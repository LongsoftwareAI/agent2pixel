"""Independently verify declared provenance against raw pinned source and vendor."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(app, upstream):
    vendor=Path(app)/'vendor/habblaud';upstream=Path(upstream)
    manifest=json.loads((vendor/'UPSTREAM.json').read_text())
    head=subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()
    errors=[];modified=[];declared=set()
    if head != manifest['commit']: errors.append('upstream HEAD does not match pin')
    ledger=(vendor/'PATCHES.md').read_text()
    for entry in manifest['files']:
        path=entry['path'];declared.add(path)
        if Path(path).is_absolute() or '..' in Path(path).parts:
            errors.append(f'unsafe manifest path: {path}');continue
        if digest(upstream/path)!=entry['upstream_sha256']:errors.append(f'upstream hash: {path}')
        current=digest(vendor/path)
        if current!=entry.get('vendored_sha256'):errors.append(f'vendor hash: {path}')
        if current!=entry['upstream_sha256']:
            modified.append(path)
            if path not in ledger:errors.append(f'undeclared patch: {path}')
    undeclared=sorted(str(p.relative_to(vendor)) for p in vendor.rglob('*') if p.is_file() and str(p.relative_to(vendor)) not in declared|{'UPSTREAM.json','PATCHES.md'})
    errors.extend(f'undeclared file: {path}' for path in undeclared)
    if digest(vendor/'LICENSE')!=digest(upstream/'LICENSE'):errors.append('MIT notice altered')
    return dict(upstream=head,files_checked=len(declared),modified_files=modified,errors=errors,passed=not errors)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--app',required=True);p.add_argument('--upstream',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    result=audit(a.app,a.upstream);Path(a.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
