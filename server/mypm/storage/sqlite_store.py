#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLite-backed storage layer.

We intentionally keep payload_json as the canonical record for forward-compat.
We also store a handful of indexed columns for fast filtering/sorting.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..domain.models import normalize_project, normalize_agent_run, normalize_agent_event, Project, AgentRun, AgentEvent
from .sqlite_db import connect, migrate


def _now() -> str:
    return datetime.now().isoformat()


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'), sort_keys=False)


def _json_loads(s: str) -> Any:
    return json.loads(s)


def _meta_get(conn, key: str) -> Optional[str]:
    row = conn.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
    return str(row['value']) if row else None


def _meta_set(conn, key: str, value: str) -> None:
    conn.execute(
        'INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
        (key, value),
    )


class ProjectsStore:
    def __init__(self, db_path: str, *, legacy_projects_json: Optional[str] = None):
        self.db_path = db_path
        self.legacy_projects_json = legacy_projects_json
        self._ensure_db()

    def _ensure_db(self) -> None:
        conn = connect(self.db_path)
        try:
            migrate(conn)
            self._maybe_import_legacy(conn)
        finally:
            conn.close()

    def _maybe_import_legacy(self, conn) -> None:
        # Import only if DB is empty.
        row = conn.execute('SELECT COUNT(1) AS n FROM projects').fetchone()
        if row and int(row['n'] or 0) > 0:
            return

        path = self.legacy_projects_json
        if not path or not os.path.exists(path):
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
        except Exception:
            return

        projects = raw.get('projects') if isinstance(raw, dict) else None
        if not isinstance(projects, list) or not projects:
            return

        with conn:
            for idx, p in enumerate(projects):
                np, _ = normalize_project(p)
                self._insert_project(conn, np, sort_order=idx)
            _meta_set(conn, 'projects.lastUpdated', str(raw.get('lastUpdated') or _now()))

    def _insert_project(self, conn, project: Project, *, sort_order: int) -> None:
        payload = dict(project)
        name = str(payload.get('name') or '')
        status = str(payload.get('status') or 'planning')
        priority = str(payload.get('priority') or 'medium')
        category = payload.get('category')
        category = str(category) if category is not None else None
        try:
            progress = int(payload.get('progress') or 0)
        except Exception:
            progress = 0

        created_at = str(payload.get('createdAt') or _now())
        updated_at = str(payload.get('updatedAt') or created_at)

        conn.execute(
            (
                'INSERT INTO projects(id, sort_order, name, status, priority, category, progress, created_at, updated_at, payload_json) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
            ),
            (
                str(payload.get('id')),
                int(sort_order),
                name,
                status,
                priority,
                category,
                int(progress),
                created_at,
                updated_at,
                _json_dumps(payload),
            ),
        )

    def _row_to_project(self, row) -> Project:
        payload = _json_loads(row['payload_json'])
        if isinstance(payload, dict):
            # Ensure consistency with indexed columns.
            payload['id'] = row['id']
            payload['name'] = row['name']
            payload['status'] = row['status']
            payload['priority'] = row['priority']
            payload['category'] = row['category']
            payload['progress'] = row['progress']
            payload['createdAt'] = row['created_at']
            payload['updatedAt'] = row['updated_at']
            return payload
        # Fallback: should never happen.
        return {
            'id': row['id'],
            'name': row['name'],
            'status': row['status'],
            'priority': row['priority'],
            'category': row['category'],
            'progress': row['progress'],
            'createdAt': row['created_at'],
            'updatedAt': row['updated_at'],
        }

    def last_updated(self) -> Optional[str]:
        conn = connect(self.db_path)
        try:
            return _meta_get(conn, 'projects.lastUpdated')
        finally:
            conn.close()

    def list(
        self,
        *,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Tuple[List[Project], Dict]:
        conn = connect(self.db_path)
        try:
            where = []
            args: List[Any] = []
            if status:
                where.append('status=?')
                args.append(status)
            if priority:
                where.append('priority=?')
                args.append(priority)
            if category:
                where.append('category=?')
                args.append(category)

            sql = 'SELECT * FROM projects'
            if where:
                sql += ' WHERE ' + ' AND '.join(where)
            sql += ' ORDER BY sort_order ASC, created_at ASC'

            rows = conn.execute(sql, tuple(args)).fetchall()
            projects = [self._row_to_project(r) for r in rows]
            meta = {
                'total': len(projects),
                'lastUpdated': _meta_get(conn, 'projects.lastUpdated'),
            }
            return projects, meta
        finally:
            conn.close()

    def get(self, project_id: str) -> Optional[Project]:
        conn = connect(self.db_path)
        try:
            row = conn.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone()
            return self._row_to_project(row) if row else None
        finally:
            conn.close()

    def create(self, project_data: Dict[str, Any]) -> Project:
        np, _ = normalize_project(project_data)
        # Business rule: require a non-empty name.
        if not str(np.get('name') or '').strip():
            raise ValueError('Project name cannot be empty')

        conn = connect(self.db_path)
        try:
            with conn:
                row = conn.execute('SELECT COALESCE(MAX(sort_order), -1) AS m FROM projects').fetchone()
                max_sort = int(row['m'] if row and row['m'] is not None else -1)
                self._insert_project(conn, np, sort_order=max_sort + 1)
                _meta_set(conn, 'projects.lastUpdated', _now())
            return np
        finally:
            conn.close()

    def update(self, project_id: str, updates: Dict[str, Any]) -> Project:
        # Full PUT semantics in this codebase are basically a patch excluding protected fields.
        return self.patch(project_id, updates, if_updated_at=None)

    def patch(self, project_id: str, patch: Dict[str, Any], *, if_updated_at: Optional[str]) -> Project:
        conn = connect(self.db_path)
        try:
            with conn:
                row = conn.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone()
                if not row:
                    raise KeyError('not found')

                current = self._row_to_project(row)
                if if_updated_at and str(current.get('updatedAt') or '') != str(if_updated_at):
                    raise RuntimeError(f"updatedAt mismatch: expected={if_updated_at}, actual={current.get('updatedAt')}")

                protected = {'id', 'createdAt'}
                for k, v in (patch or {}).items():
                    if k in protected or k == 'ifUpdatedAt':
                        continue
                    current[k] = v

                # Normalize to keep backward-compatible defaults.
                current['id'] = project_id
                current['updatedAt'] = _now()
                np, _ = normalize_project(current)

                conn.execute(
                    (
                        'UPDATE projects SET name=?, status=?, priority=?, category=?, progress=?, updated_at=?, payload_json=? '
                        'WHERE id=?'
                    ),
                    (
                        str(np.get('name') or ''),
                        str(np.get('status') or 'planning'),
                        str(np.get('priority') or 'medium'),
                        str(np.get('category')) if np.get('category') is not None else None,
                        int(np.get('progress') or 0),
                        str(np.get('updatedAt') or _now()),
                        _json_dumps(np),
                        project_id,
                    ),
                )
                _meta_set(conn, 'projects.lastUpdated', _now())
                return np
        finally:
            conn.close()

    def delete(self, project_id: str) -> None:
        conn = connect(self.db_path)
        try:
            with conn:
                cur = conn.execute('DELETE FROM projects WHERE id=?', (project_id,))
                if cur.rowcount == 0:
                    raise KeyError('not found')
                _meta_set(conn, 'projects.lastUpdated', _now())
        finally:
            conn.close()

    def reorder(self, ids: List[str]) -> List[Project]:
        conn = connect(self.db_path)
        try:
            with conn:
                # Map existing ids to current sort.
                rows = conn.execute('SELECT id FROM projects ORDER BY sort_order ASC, created_at ASC').fetchall()
                existing = [str(r['id']) for r in rows]
                by_set = set(existing)

                new_order: List[str] = []
                seen = set()
                for pid in ids or []:
                    if pid in by_set and pid not in seen:
                        new_order.append(pid)
                        seen.add(pid)
                for pid in existing:
                    if pid not in seen:
                        new_order.append(pid)
                        seen.add(pid)

                for idx, pid in enumerate(new_order):
                    conn.execute('UPDATE projects SET sort_order=? WHERE id=?', (idx, pid))

                _meta_set(conn, 'projects.lastUpdated', _now())

            # Return reordered list.
            return self.list()[0]
        finally:
            conn.close()

    def batch_update(self, ops: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
        conn = connect(self.db_path)
        try:
            results: List[Dict[str, Any]] = []
            changed = False
            with conn:
                for op in ops or []:
                    op_id = op.get('opId') if isinstance(op, dict) else None
                    try:
                        if not isinstance(op, dict):
                            raise ValueError('op must be an object')
                        pid = op.get('id')
                        patch = op.get('patch')
                        if_updated_at = op.get('ifUpdatedAt')
                        if not pid or not isinstance(pid, str):
                            raise ValueError('id is required')
                        if not isinstance(patch, dict):
                            raise ValueError('patch must be an object')

                        conn.execute('SAVEPOINT sp')
                        try:
                            row = conn.execute('SELECT * FROM projects WHERE id=?', (pid,)).fetchone()
                            if not row:
                                results.append({
                                    'opId': op_id,
                                    'id': pid,
                                    'success': False,
                                    'error': f"Project not found: {pid}",
                                    'status': 404,
                                })
                                conn.execute('RELEASE sp')
                                continue

                            cur = self._row_to_project(row)
                            if if_updated_at and str(cur.get('updatedAt') or '') != str(if_updated_at):
                                results.append({
                                    'opId': op_id,
                                    'id': pid,
                                    'success': False,
                                    'error': 'Conflict: updatedAt mismatch',
                                    'status': 409,
                                    'data': {
                                        'expectedUpdatedAt': if_updated_at,
                                        'actualUpdatedAt': cur.get('updatedAt'),
                                    }
                                })
                                conn.execute('RELEASE sp')
                                continue

                            protected = {'id', 'createdAt'}
                            for k, v in patch.items():
                                if k in protected:
                                    continue
                                cur[k] = v
                            cur['updatedAt'] = _now()
                            np, _ = normalize_project(cur)
                            conn.execute(
                                (
                                    'UPDATE projects SET name=?, status=?, priority=?, category=?, progress=?, updated_at=?, payload_json=? '
                                    'WHERE id=?'
                                ),
                                (
                                    str(np.get('name') or ''),
                                    str(np.get('status') or 'planning'),
                                    str(np.get('priority') or 'medium'),
                                    str(np.get('category')) if np.get('category') is not None else None,
                                    int(np.get('progress') or 0),
                                    str(np.get('updatedAt') or _now()),
                                    _json_dumps(np),
                                    pid,
                                ),
                            )
                            results.append({
                                'opId': op_id,
                                'id': pid,
                                'success': True,
                                'data': np,
                                'status': 200,
                            })
                            changed = True
                            conn.execute('RELEASE sp')
                        except Exception:
                            conn.execute('ROLLBACK TO sp')
                            conn.execute('RELEASE sp')
                            raise
                    except Exception as e:
                        results.append({
                            'opId': op_id,
                            'success': False,
                            'error': str(e),
                            'status': 400,
                        })

                if changed:
                    _meta_set(conn, 'projects.lastUpdated', _now())
            return results, changed
        finally:
            conn.close()

    def get_statistics(self) -> Dict[str, Any]:
        # Keep semantics identical to ProjectService.get_statistics().
        projects, _meta = self.list()
        stats: Dict[str, Any] = {
            'total': len(projects),
            'byStatus': {},
            'byPriority': {},
            'byCategory': {},
            'financial': {
                'totalBudget': 0,
                'totalCost': 0,
                'totalRevenue': 0,
                'netProfit': 0,
            },
        }

        for p in projects:
            st = p.get('status', 'unknown')
            stats['byStatus'][st] = stats['byStatus'].get(st, 0) + 1
            pr = p.get('priority', 'unknown')
            stats['byPriority'][pr] = stats['byPriority'].get(pr, 0) + 1
            cat = p.get('category', '未分类')
            stats['byCategory'][cat] = stats['byCategory'].get(cat, 0) + 1

            budget = p.get('budget')
            if isinstance(budget, dict) and 'planned' in budget:
                try:
                    stats['financial']['totalBudget'] += float(budget.get('planned') or 0)
                except Exception:
                    pass
            cost = p.get('cost')
            if isinstance(cost, dict) and 'total' in cost:
                try:
                    stats['financial']['totalCost'] += float(cost.get('total') or 0)
                except Exception:
                    pass
            revenue = p.get('revenue')
            if isinstance(revenue, dict) and 'total' in revenue:
                try:
                    stats['financial']['totalRevenue'] += float(revenue.get('total') or 0)
                except Exception:
                    pass

        stats['financial']['netProfit'] = stats['financial']['totalRevenue'] - stats['financial']['totalCost']
        return stats


class AgentRunsStore:
    def __init__(self, db_path: str, *, legacy_runs_json: Optional[str] = None):
        self.db_path = db_path
        self.legacy_runs_json = legacy_runs_json
        self._ensure_db()

    def _ensure_db(self) -> None:
        conn = connect(self.db_path)
        try:
            migrate(conn)
            self._maybe_import_legacy(conn)
        finally:
            conn.close()

    def _maybe_import_legacy(self, conn) -> None:
        row = conn.execute('SELECT COUNT(1) AS n FROM agent_runs').fetchone()
        if row and int(row['n'] or 0) > 0:
            return

        path = self.legacy_runs_json
        if not path or not os.path.exists(path):
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
        except Exception:
            return

        runs = raw.get('runs') if isinstance(raw, dict) else None
        if not isinstance(runs, list) or not runs:
            return

        with conn:
            for r in runs:
                nr, _ = normalize_agent_run(r)
                self._insert_run(conn, nr)
            _meta_set(conn, 'agent_runs.lastUpdated', str(raw.get('lastUpdated') or _now()))

    def _insert_run(self, conn, run: AgentRun) -> None:
        payload = dict(run)

        project_id = payload.get('projectId')
        if project_id:
            row = conn.execute('SELECT 1 AS ok FROM projects WHERE id=?', (str(project_id),)).fetchone()
            if not row:
                project_id = None

        conn.execute(
            (
                'INSERT INTO agent_runs(id, project_id, agent_id, status, created_at, updated_at, started_at, finished_at, payload_json) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)'
            ),
            (
                str(payload.get('id')),
                project_id,
                payload.get('agentId'),
                payload.get('status'),
                payload.get('createdAt'),
                payload.get('updatedAt'),
                payload.get('startedAt'),
                payload.get('finishedAt'),
                _json_dumps(payload),
            ),
        )

    def _row_to_run(self, row) -> AgentRun:
        payload = _json_loads(row['payload_json'])
        if isinstance(payload, dict):
            payload['id'] = row['id']
            payload['projectId'] = row['project_id']
            payload['agentId'] = row['agent_id']
            payload['status'] = row['status']
            payload['createdAt'] = row['created_at']
            payload['updatedAt'] = row['updated_at']
            payload['startedAt'] = row['started_at']
            payload['finishedAt'] = row['finished_at']
            return payload
        return {'id': row['id']}

    def create(self, run_data: Dict[str, Any]) -> AgentRun:
        nr, _ = normalize_agent_run(run_data)
        conn = connect(self.db_path)
        try:
            with conn:
                existing = conn.execute('SELECT * FROM agent_runs WHERE id=?', (str(nr.get('id')),)).fetchone()
                if existing:
                    return self._row_to_run(existing)
                self._insert_run(conn, nr)
                _meta_set(conn, 'agent_runs.lastUpdated', _now())
                return nr
        finally:
            conn.close()

    def get(self, run_id: str) -> Optional[AgentRun]:
        conn = connect(self.db_path)
        try:
            row = conn.execute('SELECT * FROM agent_runs WHERE id=?', (run_id,)).fetchone()
            return self._row_to_run(row) if row else None
        finally:
            conn.close()

    def list(
        self,
        *,
        project_id: Optional[str],
        agent_id: Optional[str],
        status: Optional[str],
        limit: int,
        offset: int,
    ) -> Tuple[List[AgentRun], int]:
        conn = connect(self.db_path)
        try:
            where = []
            args: List[Any] = []
            if project_id:
                where.append('project_id=?')
                args.append(project_id)
            if agent_id:
                where.append('agent_id=?')
                args.append(agent_id)
            if status:
                where.append('status=?')
                args.append(status)

            sql_base = 'FROM agent_runs'
            if where:
                sql_base += ' WHERE ' + ' AND '.join(where)

            total_row = conn.execute('SELECT COUNT(1) AS n ' + sql_base, tuple(args)).fetchone()
            total = int(total_row['n'] if total_row else 0)

            rows = conn.execute(
                'SELECT * ' + sql_base + ' ORDER BY created_at DESC LIMIT ? OFFSET ?',
                tuple(args + [int(limit), int(offset)]),
            ).fetchall()
            return [self._row_to_run(r) for r in rows], total
        finally:
            conn.close()

    def patch(self, run_id: str, patch: Dict[str, Any]) -> AgentRun:
        conn = connect(self.db_path)
        try:
            with conn:
                row = conn.execute('SELECT * FROM agent_runs WHERE id=?', (run_id,)).fetchone()
                if not row:
                    raise KeyError('not found')
                cur = self._row_to_run(row)

                protected = {'id', 'createdAt'}
                for k, v in (patch or {}).items():
                    if k in protected:
                        continue
                    if k == 'links' and not isinstance(v, list):
                        continue
                    if k == 'metrics' and not isinstance(v, dict):
                        continue
                    if k == 'tags' and not isinstance(v, list):
                        continue
                    if k == 'meta' and not isinstance(v, dict):
                        continue
                    cur[k] = v

                cur['id'] = run_id
                cur['updatedAt'] = _now()
                nr, _ = normalize_agent_run(cur)

                conn.execute(
                    (
                        'UPDATE agent_runs SET project_id=?, agent_id=?, status=?, created_at=?, updated_at=?, started_at=?, finished_at=?, payload_json=? '
                        'WHERE id=?'
                    ),
                    (
                        nr.get('projectId'),
                        nr.get('agentId'),
                        nr.get('status'),
                        nr.get('createdAt'),
                        nr.get('updatedAt'),
                        nr.get('startedAt'),
                        nr.get('finishedAt'),
                        _json_dumps(nr),
                        run_id,
                    ),
                )
                _meta_set(conn, 'agent_runs.lastUpdated', _now())
                return nr
        finally:
            conn.close()


class AgentEventsStore:
    def __init__(self, db_path: str, *, legacy_events_jsonl: Optional[str] = None):
        self.db_path = db_path
        self.legacy_events_jsonl = legacy_events_jsonl
        self._ensure_db()

    def _ensure_db(self) -> None:
        conn = connect(self.db_path)
        try:
            migrate(conn)
            self._maybe_import_legacy(conn)
        finally:
            conn.close()

    def _maybe_import_legacy(self, conn) -> None:
        row = conn.execute('SELECT COUNT(1) AS n FROM agent_events').fetchone()
        if row and int(row['n'] or 0) > 0:
            return

        path = self.legacy_events_jsonl
        if not path or not os.path.exists(path):
            return

        # Best-effort import: ignore invalid lines.
        with conn:
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    for line in f:
                        s = (line or '').strip()
                        if not s:
                            continue
                        try:
                            obj = json.loads(s)
                        except Exception:
                            continue
                        if not isinstance(obj, dict):
                            continue
                        evt = normalize_agent_event(obj)
                        self._insert_event(conn, evt)
            except FileNotFoundError:
                return

    def _insert_event(self, conn, evt: AgentEvent) -> None:
        payload = dict(evt)
        conn.execute(
            (
                'INSERT OR IGNORE INTO agent_events(id, ts, type, level, project_id, run_id, agent_id, title, message, payload_json) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
            ),
            (
                payload.get('id'),
                payload.get('ts'),
                payload.get('type'),
                payload.get('level'),
                payload.get('projectId'),
                payload.get('runId'),
                payload.get('agentId'),
                payload.get('title'),
                payload.get('message'),
                _json_dumps(payload),
            ),
        )

    def append(self, event: Dict[str, Any]) -> None:
        evt = normalize_agent_event(event)
        conn = connect(self.db_path)
        try:
            with conn:
                self._insert_event(conn, evt)
        finally:
            conn.close()

    def exists(self, event_id: str, max_lines: int = 5000) -> Optional[Dict[str, Any]]:  # noqa: ARG002
        if not event_id:
            return None
        conn = connect(self.db_path)
        try:
            row = conn.execute('SELECT payload_json FROM agent_events WHERE id=?', (event_id,)).fetchone()
            if not row:
                return None
            obj = _json_loads(row['payload_json'])
            return obj if isinstance(obj, dict) else None
        finally:
            conn.close()

    def normalize_for_read(self, obj) -> Dict[str, Any]:
        return normalize_agent_event(obj)

    def list(
        self,
        *,
        project_id: Optional[str],
        run_id: Optional[str],
        agent_id: Optional[str],
        typ: Optional[str],
        since_dt,
        limit: int,
        tail_lines: int,
    ) -> List[Dict[str, Any]]:  # noqa: ARG002
        # since_dt is a datetime or None (parsed in API layer).
        since = since_dt.isoformat() if since_dt else None

        conn = connect(self.db_path)
        try:
            where = []
            args: List[Any] = []
            if project_id:
                where.append('project_id=?')
                args.append(project_id)
            if run_id:
                where.append('run_id=?')
                args.append(run_id)
            if agent_id:
                where.append('agent_id=?')
                args.append(agent_id)
            if typ:
                where.append('type=?')
                args.append(typ)
            if since:
                where.append('ts>=?')
                args.append(since)

            sql = 'SELECT payload_json FROM agent_events'
            if where:
                sql += ' WHERE ' + ' AND '.join(where)
            # Mimic legacy behavior: return the most recent N events, in ascending time order.
            sql += ' ORDER BY ts DESC'
            sql += ' LIMIT ?'
            args.append(int(limit))

            rows = conn.execute(sql, tuple(args)).fetchall()
            out: List[Dict[str, Any]] = []
            for r in rows:
                try:
                    obj = _json_loads(r['payload_json'])
                except Exception:
                    continue
                if not isinstance(obj, dict):
                    continue
                out.append(self.normalize_for_read(obj))
            out.reverse()
            return out
        finally:
            conn.close()
