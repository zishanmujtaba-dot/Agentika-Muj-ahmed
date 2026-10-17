"""Offline Docker setup: apply schema, upsert demo data, and grant runtime access."""
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
if os.environ.get('PG_READONLY_PASSWORD', '') in {'', 'postgres', 'change_me', 'set_by_configure_runtime'}:
    raise SystemExit('Set a private PG_READONLY_PASSWORD in .env before running setup.')
if os.environ.get('STAFF_PASSWORD', '') in {'', 'set_by_configure_runtime'}:
    raise SystemExit('Set a private STAFF_PASSWORD in .env before running setup.')
for script, arguments in [('insert_policies.py', []), ('insert_graph.py', []),
                          ('configure_runtime.py', ['--no-env-write'])]:
    subprocess.run([sys.executable, str(root / 'scripts' / script), *arguments], cwd=root, check=True)
print('Docker database setup complete. Start the app and open http://localhost:8001/.')
