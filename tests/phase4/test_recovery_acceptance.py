"""Independent stopped-app recovery acceptance: actual CLI, relational data and artifact bytes."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

from services.api.store import Store


def test_verified_backup_restore_preserves_provenance_history_and_unicode_artifact(tmp_path):
    data = tmp_path/'original'
    store = Store(data)
    workspace_root = data/'workspaces'/'ws'
    workspace_root.mkdir(parents=True)
    workspace = {'id': 'ws', 'root_path': str(workspace_root), 'name': 'Recovery fixture'}
    store.put('workspace', workspace)
    store.put('agent', {'id': 'agent', 'workspace_id': 'ws', 'name': 'Analyst'})
    source_content = 'Nguồn được cung cấp — 12 hồ sơ; trạng thái chưa xác minh.'
    source = {'id': 'source', 'workspace_id': 'ws', 'content': source_content,
              'sha256': hashlib.sha256(source_content.encode()).hexdigest(), 'untrusted': True}
    store.put('source', source)
    store.put('memory', {'id': 'memory', 'workspace_id': 'ws', 'content': '12 supplied cases', 'source_id': 'source'})
    store.put('memory_history', {'id': 'history', 'workspace_id': 'ws', 'memory_id': 'memory', 'before': {'content': 'Earlier observation'}, 'action': 'edited'})
    artifact = workspace_root/'artifacts'/'run'/'report.md'
    artifact.parent.mkdir(parents=True)
    artifact_bytes = '# Báo cáo\n\n12 hồ sơ — nguồn được cung cấp.\n'.encode()
    artifact.write_bytes(artifact_bytes)
    run = {'id': 'run', 'workspace_id': 'ws', 'state': 'completed', 'tasks': [{'id': 'task', 'agent_id': 'agent', 'state': 'completed', 'output': artifact_bytes.decode()}],
           'artifacts': [{'id': 'artifact', 'path': 'artifacts/run/report.md', 'sha256': hashlib.sha256(artifact_bytes).hexdigest(), 'source_id': 'source'}]}
    store.put('run', run)
    store.event('ws', 'workflow.completed', {'source_id': 'source'}, 'run', 'agent')
    store.db.close()  # Stopped app is a prerequisite, not a hot-backup claim.
    with sqlite3.connect(data/'checkpoints.sqlite3') as db:
        db.execute('CREATE TABLE acceptance_checkpoint(id TEXT PRIMARY KEY, output TEXT)')
        db.execute('INSERT INTO acceptance_checkpoint VALUES(?,?)', ('run', artifact_bytes.decode()))
    backup = tmp_path/'verified-backup'
    restored = tmp_path/'restored'
    script = Path(__file__).resolve().parents[2]/'scripts'/'data_backup.py'
    for operation, source_path, destination in [('backup', data, backup), ('restore', backup, restored)]:
        proc = subprocess.run([sys.executable, str(script), operation, '--source', str(source_path), '--destination', str(destination)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        assert json.loads(proc.stdout)['verified'] is True
    with sqlite3.connect(restored/'agentverse.sqlite3') as db:
        records = {(kind, ident): json.loads(body) for kind, ident, body in db.execute('SELECT kind,id,body FROM resources')}
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []
        events = [json.loads(row[0]) for row in db.execute('SELECT body FROM events')]
    assert records['source', 'source'] == source
    assert records['run', 'run'] == run
    assert records['memory', 'memory']['source_id'] == 'source'
    assert records['memory_history', 'history']['before']['content'] == 'Earlier observation'
    assert events[0]['payload']['source_id'] == 'source' and events[0]['run_id'] == 'run'
    assert records['workspace', 'ws']['root_path'] == str(restored/'workspaces'/'ws')
    assert (restored/'workspaces'/'ws'/'artifacts'/'run'/'report.md').read_bytes() == artifact_bytes
    assert artifact.read_bytes() == artifact_bytes  # Source never changed.
    with sqlite3.connect(restored/'checkpoints.sqlite3') as db:
        assert db.execute('SELECT output FROM acceptance_checkpoint WHERE id=?', ('run',)).fetchone()[0] == artifact_bytes.decode()
    # A second restore must refuse the existing destination without changing its evidence.
    proc = subprocess.run([sys.executable, str(script), 'restore', '--source', str(backup), '--destination', str(restored)], capture_output=True, text=True)
    assert proc.returncode != 0
    assert (restored/'workspaces'/'ws'/'artifacts'/'run'/'report.md').read_bytes() == artifact_bytes
