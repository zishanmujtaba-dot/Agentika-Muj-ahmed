"""Small local retrieval check; no Groq or other answer-generation calls."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['GROQ_API_KEY'] = ''
os.environ['LANGSMITH_TRACING'] = 'false'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
from app import rag_pipeline as rag

checks = json.loads((ROOT / 'data' / 'retrieval_checks.json').read_text())
results = []
try:
    for check in checks:
        intent = rag.parse_query_intent(check['query'])
        rows = rag.retrieve_policies(intent)
        matches = rag.confident_policies(rows)
        if not matches and intent['category']:
            rows = rag.retrieve_policies({**intent, 'category': None})
            matches = rag.confident_policies(rows)
        actual = matches[0]['source_id'] if matches else None
        results.append({'query': check['query'], 'expected': check['expected'], 'actual': actual,
            'best_distance': round(rows[0]['distance'],4) if rows else None, 'passed': actual == check['expected']})
finally:
    rag.close_pipeline()
print(json.dumps({'threshold': rag.DISTANCE_THRESHOLD, 'passed': sum(r['passed'] for r in results),
                  'total': len(results), 'checks': results}, indent=2))
raise SystemExit(0 if all(r['passed'] for r in results) else 1)
