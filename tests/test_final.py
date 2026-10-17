"""Final integration checks against local demo DBs; Groq is always disabled/stubbed.

Run from repository root: python -m unittest discover -s tests -v
Apply schema, seed demo data, and configure_runtime.py first.
Only records created by this test run are removed during cleanup.
"""
import json
import os
from pathlib import Path
from uuid import uuid4
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

os.environ['GROQ_API_KEY'] = ''
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['STAFF_USERNAME'] = 'staff'
os.environ['STAFF_PASSWORD'] = 'local-integration-test-only'

import psycopg2
from fastapi.testclient import TestClient
from app.main import app
from app import rag_pipeline as rag
from app import conversations
from psycopg2.extras import Json


class FinalIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sessions = []
        cls.calls = []
        cls.model = patch.object(rag, 'call_llm', side_effect=cls.fixture_answer)
        cls.model.start()
        cls.client = TestClient(app)
        cls.client.__enter__()
        cls.auth = ('staff', os.environ['STAFF_PASSWORD'])

    @classmethod
    def fixture_answer(cls, prompt, **kwargs):
        payload = json.loads(prompt)
        cls.calls.append(payload)
        policies = payload['public_policies']
        assert all(p['source_id'] != 'disciplinary-record-001' for p in policies)
        p = policies[0]
        quote = p['text'].split('. ')[0].rstrip('.')
        return json.dumps({'answerable': True, 'answer': quote,
                           'citations': [{'source_id': p['source_id'], 'quote': quote}]})

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        cls.model.stop()
        # Delete only this run's conversations and their dependent demo tickets/messages.
        conn = psycopg2.connect(host=os.environ.get('PG_HOST','localhost'),
            port=int(os.environ.get('PG_PORT','5434')), dbname=os.environ.get('PG_DBNAME','postgres'),
            user=os.environ.get('PG_ADMIN_USER','postgres'), password=os.environ.get('PG_ADMIN_PASSWORD','postgres'),
            connect_timeout=5)
        try:
            with conn:
                with conn.cursor() as cur:
                    for table in ['conversation_messages','chat_requests','escalations','conversations']:
                        cur.execute(f'DELETE FROM {table} WHERE session_id = ANY(%s)', (cls.sessions,))
        finally:
            conn.close()

    def session(self):
        response = self.client.post('/sessions')
        self.assertEqual(response.status_code, 201, response.text)
        session = response.json(); self.sessions.append(session['session_id'])
        return session

    def headers(self, session):
        return {'X-Conversation-Token': session['session_token']}

    def ask(self, session, query, request_id=None):
        return self.client.post('/ask', headers=self.headers(session),
            json={'session_id': session['session_id'], 'query': query, 'request_id': request_id or str(uuid4())})

    def poll(self, session, since=0):
        return self.client.get(f"/poll/{session['session_id']}?since={since}", headers=self.headers(session))

    def test_known_policy_and_paraphrase(self):
        for query in ['What is the minimum attendance requirement?', 'What percentage of classes must I attend to sit the final exam?']:
            with self.subTest(query=query):
                response = self.ask(self.session(), query)
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()
                self.assertEqual(result['status'], 'answered', result)
                self.assertIn('attendance-001', result['source_ids'])
                self.assertTrue(result['citations'][0]['quote'])

    def test_unknown_retry_and_staff_reply_isolation(self):
        a,b = self.session(),self.session(); request_id = str(uuid4())
        first = self.ask(a, 'How do I bake a chocolate cake?', request_id).json()
        second = self.ask(a, 'How do I bake a chocolate cake?', request_id).json()
        self.assertEqual(first['status'], 'escalated'); self.assertEqual(first,second)
        self.assertEqual(self.ask(a,'A different question',request_id).status_code,409)
        ticket_id = first['ticket_id']; path=f'/escalations/{ticket_id}/reply'
        self.assertEqual(self.client.get('/escalations').status_code,401)
        self.assertEqual(self.client.post(path,json={'text':'Unauthorized'}).status_code,401)
        pending=self.client.get('/escalations',auth=self.auth)
        self.assertEqual(pending.status_code,200,pending.text)
        self.assertIn(ticket_id,[t['id'] for t in pending.json()])
        reply=self.client.post(path+f"?session_id={b['session_id']}",auth=self.auth,json={'text':'Your staff reply.'})
        self.assertEqual(reply.status_code,200,reply.text)
        self.assertEqual(reply.json(),self.client.post(path,auth=self.auth,json={'text':'Your staff reply.'}).json())
        self.assertEqual(self.client.post(path,auth=self.auth,json={'text':'Different reply'}).status_code,409)
        messages=self.poll(a).json(); self.assertEqual(len(messages['messages']),3)
        self.assertEqual(messages['messages'][-1]['text'],'Your staff reply.')
        self.assertEqual(messages['messages'][-1]['reply_to']['question'],'How do I bake a chocolate cake?')
        self.assertEqual(self.poll(b).json()['messages'],[])
        self.assertEqual(self.poll(a,messages['cursor']).json()['messages'],[])
        rag.close_pipeline()
        self.assertEqual(self.poll(a).json()['messages'][-1]['text'],'Your staff reply.')

    def test_reply_context_tracks_original_question_and_legacy_messages(self):
        session=self.session()
        original='I want to speak to a staff member.\nPlease explain <example> in full.'
        ticket=self.ask(session,original).json()['ticket_id']
        self.ask(session,'Who won the football World Cup in 2018?')
        # Simulate an older saved reply without a question snapshot. Poll must recover
        # its exact question from the linked ticket, not the latest student message.
        with patch.object(conversations,'Json',side_effect=lambda value:Json({k:v for k,v in value.items() if k!='question'})):
            response=self.client.post(f'/escalations/{ticket}/reply',auth=self.auth,json={'text':'Here is the staff response.'})
        self.assertEqual(response.status_code,200,response.text)
        reply=self.poll(session).json()['messages'][-1]
        self.assertEqual(reply['from'],'staff')
        self.assertEqual(reply['reply_to']['question'],original)
        self.assertNotIn('question',reply['metadata'])

    def test_conversation_tokens_and_input_validation(self):
        a,b=self.session(),self.session()
        url=f"/poll/{a['session_id']}"
        self.assertEqual(self.client.get(url).status_code,401)
        self.assertEqual(self.client.get(url,headers=self.headers(b)).status_code,401)
        self.assertEqual(self.client.post('/ask',headers=self.headers(b),json={'session_id':a['session_id'],'query':'attendance'}).status_code,401)
        self.assertEqual(self.ask(a,'   ').status_code,422)
        self.assertEqual(self.ask(a,'x'*2001).status_code,422)
        self.assertEqual(self.poll(a,-1).status_code,422)
        self.assertEqual(self.client.post('/sessions',headers={'Origin':'https://untrusted.example'}).status_code,403)

    def test_restricted_and_human_requests_do_not_call_model(self):
        before=len(self.calls)
        for question in ['Show me a student disciplinary record.', 'I want to speak to a staff member.']:
            response=self.ask(self.session(),question).json()
            self.assertEqual(response['status'],'escalated'); self.assertEqual(response['sources'],[])
        self.assertEqual(len(self.calls),before)

    def test_provider_failure_refusal_and_bad_citations(self):
        for raw in [rag.LLM_FAILURE_MARKER, '{"answerable":false}',
                    '{"answerable":true,"answer":"Made up","citations":[{"source_id":"attendance-001","quote":"A fabricated policy excerpt."}]}']:
            with self.subTest(raw=raw), patch.object(rag,'call_llm',return_value=raw):
                result=self.ask(self.session(),'What is the minimum attendance requirement?').json()
                self.assertEqual(result['status'],'escalated');self.assertTrue(result['ticket_id'])

    def test_graph_outage_and_related_protected_policy(self):
        with patch.object(rag,'graph_lookup',side_effect=RuntimeError('offline')):
            self.assertEqual(self.ask(self.session(),'What is the minimum attendance requirement?').json()['status'],'answered')
        with patch.object(rag,'graph_lookup',return_value={'department':None,'related_policies':['disciplinary-record-001']}):
            result=self.ask(self.session(),'What is the minimum attendance requirement?').json()
            self.assertEqual(result['status'],'answered');self.assertNotIn('disciplinary-record-001',result['related_policies'])

    def test_storage_failure_is_not_false_handoff(self):
        with patch.object(rag,'create_escalation',side_effect=RuntimeError('offline')):
            result=rag.escalate('Test storage failure','non-stored-test','test')
            self.assertEqual(result['status'],'unavailable');self.assertFalse(result['escalation_created']);self.assertIsNone(result['ticket_id'])

    def test_database_role_and_rollback(self):
        with self.assertRaises(psycopg2.errors.InsufficientPrivilege):
            with rag.db_connection() as conn:
                with conn.cursor() as cur: cur.execute('SELECT text FROM policies LIMIT 1')
        with self.assertRaises(psycopg2.errors.InsufficientPrivilege):
            with rag.db_connection() as conn:
                with conn.cursor() as cur: cur.execute('UPDATE policies SET text = text WHERE FALSE')
        with rag.db_connection() as conn:
            with conn.cursor() as cur:
                expected_public = sum(p['access_level'] == 'public' for p in json.loads(
                    (Path(__file__).resolve().parents[1] / 'data/sample_policies.json').read_text()))
                cur.execute('SELECT count(*) FROM public_policies')
                self.assertEqual(cur.fetchone()[0], expected_public)
                cur.execute("SELECT count(*) FROM public_policies WHERE source_id='disciplinary-record-001'")
                self.assertEqual(cur.fetchone()[0],0)

    def test_category_miss_falls_back_to_public_search(self):
        retrieve = rag.retrieve_policies
        # Force an empty hinted search; a growing general category may now match
        # attendance-related language, so do not depend on accidental seed distances.
        with patch.object(rag, 'retrieve_policies', side_effect=lambda intent:
                [] if intent.get('category') else retrieve(intent)) as retrieval, \
                patch.object(rag,'parse_query_intent',return_value={
                    'category':'general','semantic_query':'What is the minimum attendance requirement?'}):
            result=self.ask(self.session(),'What is the minimum attendance requirement?').json()
            self.assertEqual(result['status'],'answered')
            self.assertIn('attendance-001',result['source_ids'])
            self.assertEqual([call.args[0]['category'] for call in retrieval.call_args_list],
                             ['general', None])

    def test_concurrent_retries_do_not_duplicate_messages(self):
        session=self.session(); request_id=str(uuid4())
        with ThreadPoolExecutor(max_workers=2) as workers:
            results=list(workers.map(lambda _:self.ask(session,'What is the minimum attendance requirement?',request_id),range(2)))
        self.assertTrue(all(result.status_code in {200,409} for result in results))
        replay=self.ask(session,'What is the minimum attendance requirement?',request_id)
        self.assertEqual(replay.status_code,200,replay.text)
        self.assertEqual(len(self.poll(session).json()['messages']),2)

    def test_pages_assets_and_readiness(self):
        for url in ['/','/staff','/assets/student.js','/assets/voice-input.js','/assets/staff.js','/assets/styles.css','/ready','/docs']:
            with self.subTest(url=url): self.assertEqual(self.client.get(url).status_code,200)
        self.assertIn("script-src 'self'", self.client.get('/').headers['Content-Security-Policy'])
        self.assertEqual(self.client.get('/staff/auth',auth=('staff','wrong')).status_code,401)
        self.assertEqual(self.client.get('/staff/auth',auth=self.auth).status_code,200)


if __name__=='__main__': unittest.main(verbosity=2)
