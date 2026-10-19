#!/usr/bin/env python3
"""Verified directory backup/restore. Stop the application before using either command."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile

MANIFEST = '.agentverse-backup.json'
MAX_BYTES = 512 * 1024 * 1024


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(root):
    result = {}
    total = 0
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('Symlinks are not allowed in backup data')
        if path.is_file() and path.relative_to(root).as_posix() != MANIFEST:
            total += path.stat().st_size
            if total > MAX_BYTES:
                raise ValueError('Backup exceeds512MiB')
            result[path.relative_to(root).as_posix()] = digest(path)
    return result


def backup_fingerprint(root):
    """Ignore reader-maintained SQLite shared memory and empty WAL sidecars.

    Opening a stopped WAL database read-only may create these files. Nonempty
    WAL/journal contents and all durable files still participate in the guard.
    Symlinks and total-size validation remain enforced by files().
    """
    return {
        relative: value for relative, value in files(root).items()
        if not relative.endswith('-shm')
        and not (relative.endswith('-wal') and (root / relative).stat().st_size == 0)
    }


def validate_db(path):
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Database integrity check failed')
        if db.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Database foreign key check failed')


def quiescent(db):
    for (body,) in db.execute("SELECT body FROM resources WHERE kind='run'"):
        if json.loads(body)['state'] in ('queued', 'running', 'waiting_approval', 'waiting_review'):
            raise ValueError('Finish/cancel active runs and stop application before backup')


def empty_destination(path):
    if path.is_symlink() or path.exists():
        raise ValueError('Destination must not exist; existing data is never overwritten')
    path.parent.mkdir(parents=True, exist_ok=True)


def backup(data, destination):
    data, destination = data.resolve(), destination.absolute()
    if not (data / 'agentverse.sqlite3').is_file():
        raise ValueError('Source application database missing')
    if destination.resolve().is_relative_to(data):
        raise ValueError('Backup must be outside source data directory')
    empty_destination(destination)
    with tempfile.TemporaryDirectory(prefix='.agentverse-backup-', dir=destination.parent) as scratch:
        stage = Path(scratch) / 'data'
        stage.mkdir()
        before = backup_fingerprint(data)
        live = sqlite3.connect((data / 'agentverse.sqlite3').as_uri() + '?mode=ro', uri=True)
        try:
            quiescent(live)
            version = live.execute('PRAGMA data_version').fetchone()[0]
            for relative in before:
                source = data / relative
                if source.name.endswith(('-wal', '-shm', '-journal')):
                    continue
                target = stage / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if source.suffix in ('.sqlite3', '.db'):
                    with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as src:
                        with closing(sqlite3.connect(target)) as dst:
                            src.backup(dst)
                    validate_db(target)
                else:
                    shutil.copyfile(source, target)
            if version != live.execute('PRAGMA data_version').fetchone()[0] or before != backup_fingerprint(data):
                raise ValueError('Source changed during backup; stop application and retry')
        finally:
            live.close()
        manifest = dict(version=1, original_root=str(data), files=files(stage))
        (stage / MANIFEST).write_text(json.dumps(manifest, indent=2) + '\n')
        stage.rename(destination)
    return dict(files=len(manifest['files']), destination=str(destination), verified=True)


def restore(source, destination):
    source, destination = source.resolve(), destination.absolute()
    if (source / MANIFEST).is_symlink():
        raise ValueError('Backup manifest symlink denied')
    manifest = json.loads((source / MANIFEST).read_text())
    if manifest.get('version') != 1 or not isinstance(manifest.get('files'), dict):
        raise ValueError('Unsupported backup manifest')
    if manifest['files'] != files(source):
        raise ValueError('Backup hash/contents mismatch')
    for relative in manifest['files']:
        if Path(relative).is_absolute() or '..' in Path(relative).parts:
            raise ValueError('Unsafe backup path')
    empty_destination(destination)
    with tempfile.TemporaryDirectory(prefix='.agentverse-restore-', dir=destination.parent) as scratch:
        stage = Path(scratch) / 'data'
        stage.mkdir()
        for relative in manifest['files']:
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, target)
        database = stage / 'agentverse.sqlite3'
        validate_db(database)
        with closing(sqlite3.connect(database)) as db:
            quiescent(db)
            for id, body in db.execute("SELECT id,body FROM resources WHERE kind='workspace'").fetchall():
                value = json.loads(body)
                old_path = Path(value['root_path'])
                old_root = Path(manifest['original_root'])
                if not old_path.is_relative_to(old_root):
                    raise ValueError('Workspace root is outside backed-up data')
                value['root_path'] = str(destination.resolve() / old_path.relative_to(old_root))
                db.execute('UPDATE resources SET body=? WHERE id=?', (json.dumps(value), id))
            db.commit()
        validate_db(database)
        stage.rename(destination)
    return dict(files=len(manifest['files']), destination=str(destination), verified=True,
                relocated_workspace_roots=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['backup', 'restore'])
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = (backup if args.operation == 'backup' else restore)(args.source, args.destination)
    except (ValueError, OSError, sqlite3.Error, KeyError) as error:
        parser.exit(1, str(error) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
