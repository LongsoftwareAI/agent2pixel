"""Versioned SQLite persistence. JSON resources are schema-version migration friendly."""

import json
import sqlite3
import uuid
import threading
from functools import wraps
from datetime import datetime, timezone
from pathlib import Path


def uid():
    return str(uuid.uuid4())


def now():
    return datetime.now(timezone.utc).isoformat()


def synchronized(method):
    @wraps(method)
    def protected(self, *args, **kwargs):
        with self.lock:
            return method(self, *args, **kwargs)

    return protected


class Store:
    def __init__(self, root):
        self.lock = threading.RLock()
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(
            self.root / "agentverse.sqlite3", check_same_thread=False
        )
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY);
        INSERT OR IGNORE INTO schema_migrations VALUES(1);
        CREATE TABLE IF NOT EXISTS resources(kind TEXT, id TEXT PRIMARY KEY, workspace_id TEXT REFERENCES resources(id), body TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS resources_workspace ON resources(kind, workspace_id);
        CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, workspace_id TEXT NOT NULL REFERENCES resources(id), run_id TEXT REFERENCES resources(id), agent_id TEXT REFERENCES resources(id), body TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS events_workspace ON events(workspace_id, seq);
        CREATE INDEX IF NOT EXISTS events_run ON events(run_id,seq);
        """)
        self.db.commit()
        # Additive migration: preserve all IDs/history; online backup remains reviewable.
        if not self.db.execute(
            "SELECT 1 FROM schema_migrations WHERE version=2"
        ).fetchone():
            backup = sqlite3.connect(self.root / "pre-schema-v2.sqlite3")
            self.db.backup(backup)
            backup.close()
            self.db.execute("INSERT INTO schema_migrations VALUES(2)")
            self.db.commit()
        # A process restart must never leave a run claiming to be executing.
        for run in self.list("run"):
            if run["state"] in ("queued", "running"):
                run.update(
                    state="failed",
                    error="Runtime restarted; retry this run",
                    ended_at=now(),
                )
                for task in run["tasks"]:
                    if task["state"] in ("running", "queued"):
                        task.update(state="failed", error="Runtime restarted")
                        agent = self.get("agent", task["agent_id"])
                        if agent:
                            agent["status"] = "error"
                            self.put("agent", agent)
                        self.event(
                            run["workspace_id"],
                            "task.failed",
                            {"task_id": task["id"], "error": "Runtime restarted"},
                            run["id"],
                            task["agent_id"],
                        )
                self.put("run", run)
                self.event(
                    run["workspace_id"],
                    "workflow.failed",
                    {"error": "Runtime restarted"},
                    run["id"],
                )

    @synchronized
    def resource_kind(self, id):
        row = self.db.execute("SELECT kind FROM resources WHERE id=?", (id,)).fetchone()
        return row[0] if row else None

    @synchronized
    def put(self, kind, value):
        existing = self.resource_kind(value["id"])
        if existing and existing != kind:
            raise ValueError("Resource identity collision")
        self.db.execute(
            "INSERT INTO resources VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET kind=excluded.kind, workspace_id=excluded.workspace_id, body=excluded.body",
            (kind, value["id"], value.get("workspace_id"), json.dumps(value)),
        )
        self.db.commit()
        return value

    @synchronized
    def get(self, kind, id):
        row = self.db.execute(
            "SELECT body FROM resources WHERE kind=? AND id=?", (kind, id)
        ).fetchone()
        return json.loads(row[0]) if row else None

    @synchronized
    def list(self, kind, workspace=None):
        rows = self.db.execute(
            "SELECT body FROM resources WHERE kind=?"
            + (" AND workspace_id=?" if workspace else ""),
            (kind, workspace) if workspace else (kind,),
        ).fetchall()
        return [json.loads(row[0]) for row in rows]

    @synchronized
    def event(self, workspace, event_type, payload=None, run=None, agent=None):
        value = dict(
            id=uid(),
            schema_version=1,
            workspace_id=workspace,
            run_id=run,
            agent_id=agent,
            event_type=event_type,
            payload=payload or {},
            created_at=now(),
        )
        cursor = self.db.execute(
            "INSERT INTO events(workspace_id,run_id,agent_id,body) VALUES(?,?,?,?)",
            (workspace, run, agent, json.dumps(value)),
        )
        value["seq"] = cursor.lastrowid
        self.db.execute(
            "UPDATE events SET body=? WHERE seq=?", (json.dumps(value), value["seq"])
        )
        self.db.commit()  # persist before websocket reads
        return value

    @synchronized
    def events(self, workspace=None, run=None, after=0):
        rows = self.db.execute(
            "SELECT body FROM events WHERE seq>?"
            + (" AND workspace_id=?" if workspace else "")
            + (" AND run_id=?" if run else "")
            + " ORDER BY seq",
            [after] + ([workspace] if workspace else []) + ([run] if run else []),
        ).fetchall()
        return [json.loads(row[0]) for row in rows]
