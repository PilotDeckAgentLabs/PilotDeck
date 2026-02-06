#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLite connection + migrations.

Design goals:
- Single-file deployment (data/pm.db)
- Stronger concurrency than JSON (WAL + busy_timeout)
- Zero new dependencies (stdlib sqlite3)
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Callable, List


MIGRATIONS: List[Callable[[sqlite3.Connection], None]] = []


def migration(fn: Callable[[sqlite3.Connection], None]) -> Callable[[sqlite3.Connection], None]:
    MIGRATIONS.append(fn)
    return fn


def connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # timeout is in seconds (float). This controls how long sqlite3 waits on database locks.
    conn = sqlite3.connect(db_path, timeout=5.0)
    conn.row_factory = sqlite3.Row

    # Pragmas: applied per-connection.
    # WAL enables concurrent readers/writers, and is the recommended mode for this workload.
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA synchronous=NORMAL;')
    conn.execute('PRAGMA foreign_keys=ON;')
    conn.execute('PRAGMA busy_timeout=5000;')
    return conn


def get_user_version(conn: sqlite3.Connection) -> int:
    row = conn.execute('PRAGMA user_version;').fetchone()
    if not row:
        return 0
    try:
        return int(row[0])
    except Exception:
        return 0


def set_user_version(conn: sqlite3.Connection, v: int) -> None:
    conn.execute(f'PRAGMA user_version={int(v)};')


def migrate(conn: sqlite3.Connection) -> None:
    """Apply schema migrations up to latest."""
    current = get_user_version(conn)
    target = len(MIGRATIONS)
    if current > target:
        raise RuntimeError(f"DB user_version ({current}) is newer than code migrations ({target})")

    if current == target:
        return

    # Apply migrations sequentially; each migration bumps user_version by 1.
    with conn:
        for idx in range(current, target):
            MIGRATIONS[idx](conn)
            set_user_version(conn, idx + 1)


@migration
def _v1_init(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS projects (
          id TEXT PRIMARY KEY,
          sort_order INTEGER NOT NULL DEFAULT 0,
          name TEXT NOT NULL,
          status TEXT NOT NULL,
          priority TEXT NOT NULL,
          category TEXT,
          progress INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          payload_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_projects_sort_order ON projects(sort_order);
        CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
        CREATE INDEX IF NOT EXISTS idx_projects_priority ON projects(priority);
        CREATE INDEX IF NOT EXISTS idx_projects_category ON projects(category);
        CREATE INDEX IF NOT EXISTS idx_projects_updated_at ON projects(updated_at);

        CREATE TABLE IF NOT EXISTS agent_runs (
          id TEXT PRIMARY KEY,
          project_id TEXT,
          agent_id TEXT,
          status TEXT,
          created_at TEXT,
          updated_at TEXT,
          started_at TEXT,
          finished_at TEXT,
          payload_json TEXT NOT NULL,
          FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_runs_created_at ON agent_runs(created_at);
        CREATE INDEX IF NOT EXISTS idx_runs_project_id ON agent_runs(project_id);
        CREATE INDEX IF NOT EXISTS idx_runs_agent_id ON agent_runs(agent_id);
        CREATE INDEX IF NOT EXISTS idx_runs_status ON agent_runs(status);

        CREATE TABLE IF NOT EXISTS agent_events (
          id TEXT PRIMARY KEY,
          ts TEXT,
          type TEXT,
          level TEXT,
          project_id TEXT,
          run_id TEXT,
          agent_id TEXT,
          title TEXT,
          message TEXT,
          payload_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_events_ts ON agent_events(ts);
        CREATE INDEX IF NOT EXISTS idx_events_project_id ON agent_events(project_id);
        CREATE INDEX IF NOT EXISTS idx_events_run_id ON agent_events(run_id);
        CREATE INDEX IF NOT EXISTS idx_events_agent_id ON agent_events(agent_id);
        CREATE INDEX IF NOT EXISTS idx_events_type ON agent_events(type);
        """
    )


@migration
def _v2_add_project_budget_fields(conn: sqlite3.Connection) -> None:
    conn.execute('ALTER TABLE projects ADD COLUMN budget REAL NOT NULL DEFAULT 0')
    conn.execute('ALTER TABLE projects ADD COLUMN actual_cost REAL NOT NULL DEFAULT 0')

    rows = conn.execute('SELECT id, payload_json FROM projects').fetchall()
    for row in rows:
        try:
            payload = json.loads(row['payload_json'])
        except Exception:
            payload = {}

        budget = 0.0
        raw_budget = payload.get('budget') if isinstance(payload, dict) else None
        if isinstance(raw_budget, dict):
            planned = raw_budget.get('planned')
            if planned is None:
                planned = raw_budget.get('total')
            if planned is None:
                planned = raw_budget.get('amount')
            try:
                budget = float(planned) if planned is not None else 0.0
            except Exception:
                budget = 0.0
        elif isinstance(raw_budget, (int, float)):
            budget = float(raw_budget)
        elif raw_budget is not None:
            try:
                budget = float(raw_budget)
            except Exception:
                budget = 0.0
        if budget < 0:
            budget = 0.0

        actual_cost = 0.0
        raw_actual = None
        if isinstance(payload, dict):
            raw_actual = payload.get('actualCost')
            if raw_actual is None:
                raw_actual = payload.get('actual_cost')
            if raw_actual is None:
                cost_obj = payload.get('cost')
                if isinstance(cost_obj, dict):
                    raw_actual = cost_obj.get('total')
                elif isinstance(cost_obj, (int, float)):
                    raw_actual = cost_obj
        if isinstance(raw_actual, (int, float)):
            actual_cost = float(raw_actual)
        elif raw_actual is not None:
            try:
                actual_cost = float(raw_actual)
            except Exception:
                actual_cost = 0.0
        if actual_cost < 0:
            actual_cost = 0.0

        conn.execute(
            'UPDATE projects SET budget=?, actual_cost=? WHERE id=?',
            (budget, actual_cost, row['id'])
        )


@migration
def _v3_add_agentops_and_usage(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS agent_profiles (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          role TEXT,
          enabled INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          payload_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_agent_profiles_updated_at ON agent_profiles(updated_at);
        CREATE INDEX IF NOT EXISTS idx_agent_profiles_name ON agent_profiles(name);

        CREATE TABLE IF NOT EXISTS agent_capabilities (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          enabled INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          payload_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_agent_capabilities_updated_at ON agent_capabilities(updated_at);
        CREATE INDEX IF NOT EXISTS idx_agent_capabilities_name ON agent_capabilities(name);

        CREATE TABLE IF NOT EXISTS token_usage_records (
          id TEXT PRIMARY KEY,
          ts TEXT NOT NULL,
          project_id TEXT,
          run_id TEXT,
          agent_id TEXT,
          workspace TEXT,
          session_id TEXT,
          source TEXT,
          model TEXT,
          prompt_tokens INTEGER NOT NULL DEFAULT 0,
          completion_tokens INTEGER NOT NULL DEFAULT 0,
          total_tokens INTEGER NOT NULL DEFAULT 0,
          cost REAL NOT NULL DEFAULT 0,
          payload_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_usage_ts ON token_usage_records(ts);
        CREATE INDEX IF NOT EXISTS idx_usage_project ON token_usage_records(project_id);
        CREATE INDEX IF NOT EXISTS idx_usage_agent ON token_usage_records(agent_id);
        CREATE INDEX IF NOT EXISTS idx_usage_workspace ON token_usage_records(workspace);
        CREATE INDEX IF NOT EXISTS idx_usage_source ON token_usage_records(source);
        CREATE INDEX IF NOT EXISTS idx_usage_session ON token_usage_records(session_id);
        """
    )
