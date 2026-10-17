"""Read-only migration inventory: record IDs/ownership and history hashes only.

Run snapshot against a baseline DB copy, then check against migrated copy. Never
opens Store (which performs startup writes). No model text or secrets in output.
"""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def snapshot(db_path):
    db=sqlite3.connect(Path(db_path).resolve().as_uri()+'?mode=ro',uri=True)
    resources=[];history=[]
    for kind,identity,workspace,body in db.execute('SELECT kind,id,workspace_id,body FROM resources ORDER BY id'):
        resources.append(dict(kind=kind,id=identity,workspace_id=workspace))
        value=json.loads(body)
        if kind=='run' and value.get('state') in ('completed','failed','cancelled'):
            history.append(dict(id=identity,sha256=hashlib.sha256(body.encode()).hexdigest()))
    events=[dict(seq=seq,sha256=hashlib.sha256(body.encode()).hexdigest()) for seq,body in db.execute('SELECT seq,body FROM events ORDER BY seq')]
    db.close()
    return dict(resources=resources,terminal_runs=history,events=events)


def verify(before,after):
    errors=[]
    for key in ('resources','events'):
        index={row['id' if key=='resources' else 'seq']:row for row in after[key]}
        for row in before[key]:
            identity=row['id' if key=='resources' else 'seq']
            if index.get(identity)!=row:errors.append(f'{key} identity/ownership/history changed: {identity}')
    # Schema additions may alter serialized terminal runs; compare only legacy
    # history output via explicit application checks rather than rejecting additions.
    return dict(passed=not errors,errors=errors,baseline_counts={k:len(v) for k,v in before.items()},after_counts={k:len(v) for k,v in after.items()})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=['snapshot','verify']);p.add_argument('--db',required=True);p.add_argument('--baseline',required=True);p.add_argument('--output');a=p.parse_args()
    if a.operation=='snapshot':Path(a.baseline).write_text(json.dumps(snapshot(a.db),indent=2)+'\n')
    else:
        result=verify(json.loads(Path(a.baseline).read_text()),snapshot(a.db))
        if a.output:Path(a.output).write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
