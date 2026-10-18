import json
import sqlite3
from pathlib import Path
import pytest
from scripts.data_backup import backup, restore


def seed(root):
    root.mkdir()
    ws = root / 'workspaces' / 'w'
    ws.mkdir(parents=True)
    (ws / 'report.md').write_text('verified report\n')
    with sqlite3.connect(root / 'agentverse.sqlite3') as db:
        db.execute('CREATE TABLE resources(kind TEXT,id TEXT PRIMARY KEY,body TEXT)')
        db.execute('INSERT INTO resources VALUES(?,?,?)', ('workspace', 'w', json.dumps({'id':'w','root_path':str(ws)})))
        db.execute('INSERT INTO resources VALUES(?,?,?)', ('run', 'r', json.dumps({'id':'r','state':'completed','output':'original'})))
    return root


def test_verified_restore_preserves_ids_outputs_and_relocates(tmp_path):
    data = seed(tmp_path / 'original')
    saved, recovered = tmp_path / 'backup', tmp_path / 'recovered'
    assert backup(data,saved)['verified']
    assert restore(saved,recovered)['verified']
    with sqlite3.connect(recovered/'agentverse.sqlite3') as db:
        values={id:json.loads(body) for id,body in db.execute('SELECT id,body FROM resources')}
    assert values['r']['output']=='original'
    assert Path(values['w']['root_path'])==recovered/'workspaces'/'w'
    assert (Path(values['w']['root_path'])/'report.md').read_text()=='verified report\n'
    assert (data/'workspaces'/'w'/'report.md').is_file()


def test_refuses_tampered_backup_existing_destination_and_symlink(tmp_path):
    data=seed(tmp_path/'original'); saved=tmp_path/'backup'
    backup(data,saved)
    with pytest.raises(ValueError,match='must not exist'):restore(saved,data)
    (saved/'workspaces'/'w'/'report.md').write_text('tampered')
    with pytest.raises(ValueError,match='mismatch'):restore(saved,tmp_path/'recover')
    (data/'escape').symlink_to(tmp_path)
    with pytest.raises(ValueError,match='Symlinks'):backup(data,tmp_path/'bad')


@pytest.mark.parametrize('state',['running','waiting_approval','waiting_review'])
def test_refuses_active_run_and_nested_destination(tmp_path,state):
    data=seed(tmp_path/'original')
    with sqlite3.connect(data/'agentverse.sqlite3') as db:
        db.execute('UPDATE resources SET body=? WHERE id=?',(json.dumps({'id':'r','state':state}),'r'))
    with pytest.raises(ValueError,match='active runs'):backup(data,tmp_path/'backup')
    with pytest.raises(ValueError,match='outside'):backup(data,data/'backup')
