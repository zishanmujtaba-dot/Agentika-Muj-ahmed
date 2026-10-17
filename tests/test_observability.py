"""Offline LangSmith SDK tests: SDK transport is mocked, no real API calls."""
import json
import os
import unittest
from unittest.mock import patch

from langsmith import Client
from app import observability as obs


class ObservabilityTests(unittest.TestCase):
    def test_default_enabled_requires_key(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(obs.tracing_enabled())
            os.environ['LANGSMITH_API_KEY'] = 'fake-test-only'
            self.assertTrue(obs.tracing_enabled())
            os.environ['LANGSMITH_TRACING'] = 'false'
            self.assertFalse(obs.tracing_enabled())

    def test_client_receives_explicit_workspace_scope(self):
        with patch.dict(os.environ, {'LANGSMITH_API_KEY': 'fake-test-only',
                'LANGSMITH_WORKSPACE_ID': 'workspace-test',
                'LANGSMITH_ORGANIZATION_ID': 'organization-test'}), \
                patch.object(obs, '_client', None), patch('langsmith.Client') as factory:
            obs._get_client()
            self.assertEqual(factory.call_args.kwargs['workspace_id'], 'workspace-test')
            self.assertEqual(factory.call_args.kwargs['headers'],
                             {'X-Organization-Id': 'organization-test'})

    def test_disabled_does_not_initialize_sdk_client(self):
        @obs.observed('disabled')
        def function(value):
            return value
        with patch.dict(os.environ, {'LANGSMITH_TRACING': 'false'}), patch.object(obs, '_get_client') as client:
            self.assertEqual(function('unchanged'), 'unchanged')
            client.assert_not_called()

    def test_real_sdk_nested_spans_redact_arguments_and_outputs(self):
        client = Client(api_key='fake-test-only', auto_batch_tracing=False)
        @obs.observed('child', summarize=lambda result: {'source_count': len(result)})
        def child(question):
            return ['PRIVATE ANSWER']
        @obs.observed('parent', summarize=lambda result: {'status': 'answered'})
        def parent(question, session_token):
            return child(question)
        with patch.dict(os.environ, {'LANGSMITH_TRACING': 'true', 'LANGSMITH_API_KEY': 'fake-test-only'}), \
             patch.object(obs, '_get_client', return_value=client), \
             patch.object(Client, 'create_run') as create, patch.object(Client, 'update_run') as update:
            self.assertEqual(parent('PRIVATE QUESTION', 'SECRET TOKEN'), ['PRIVATE ANSWER'])
            self.assertEqual(create.call_count, 2)
            starts = [call.kwargs for call in create.call_args_list]
            root = next(run for run in starts if run['name'] == 'parent')
            child_run = next(run for run in starts if run['name'] == 'child')
            self.assertEqual(child_run['parent_run_id'], root['id'])
            self.assertTrue(update.called)
            payload = str(create.call_args_list) + str(update.call_args_list)
            for private in ['PRIVATE QUESTION', 'PRIVATE ANSWER', 'SECRET TOKEN']:
                self.assertNotIn(private, payload)
            self.assertIn('source_count', payload)

    def test_business_error_is_preserved_but_message_is_not_exported(self):
        client = Client(api_key='fake-test-only', auto_batch_tracing=False)
        @obs.observed('error')
        def fail():
            raise ValueError('SECRET PROVIDER MESSAGE')
        with patch.dict(os.environ, {'LANGSMITH_TRACING': 'true', 'LANGSMITH_API_KEY': 'fake-test-only'}), \
             patch.object(obs, '_get_client', return_value=client), \
             patch.object(Client, 'create_run') as create, patch.object(Client, 'update_run') as update:
            with self.assertRaisesRegex(ValueError, 'SECRET PROVIDER MESSAGE'):
                fail()
            self.assertNotIn('SECRET PROVIDER MESSAGE', str(create.call_args_list) + str(update.call_args_list))
            self.assertIn('ValueError', str(update.call_args_list))

    def test_setup_failure_does_not_repeat_or_block_business_logic(self):
        calls = []
        @obs.observed('fail-open')
        def work():
            calls.append(1)
            return 42
        with patch.dict(os.environ, {'LANGSMITH_TRACING': 'true', 'LANGSMITH_API_KEY': 'fake-test-only'}), \
             patch.object(obs, '_get_client', side_effect=RuntimeError('telemetry failed')):
            self.assertEqual(work(), 42)
        self.assertEqual(calls, [1])

    def test_summary_failure_does_not_repeat_business_logic(self):
        calls = []
        client = Client(api_key='fake-test-only', auto_batch_tracing=False)
        def bad_summary(result):
            raise RuntimeError('bad telemetry summary')
        @obs.observed('bad summary', summarize=bad_summary)
        def work():
            calls.append(1)
            return 42
        with patch.dict(os.environ, {'LANGSMITH_TRACING': 'true', 'LANGSMITH_API_KEY': 'fake-test-only'}), \
             patch.object(obs, '_get_client', return_value=client), \
             patch.object(Client, 'create_run'), patch.object(Client, 'update_run'):
            self.assertEqual(work(), 42)
        self.assertEqual(calls, [1])
