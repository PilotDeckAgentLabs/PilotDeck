#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLite-backed storage layer.

We intentionally keep payload_json as the canonical record for forward-compat.
We also store a handful of indexed columns for fast filtering/sorting.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..domain.models import (
    normalize_project,
    normalize_agent_run,
    normalize_agent_event,
    normalize_agent_profile,
    normalize_agent_capability,
    normalize_token_usage_record,
    Project,
    AgentRun,
    AgentEvent,
    AgentProfile,
    AgentCapability,
    TokenUsageRecord,
)
from .sqlite_db import connect, migrate


def _now() -> str:
    return datetime.now().isoformat()


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False)


def _json_loads(s: str) -> Any:
    return json.loads(s)


def _meta_get(conn, key: str) -> Optional[str]:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return str(row["value"]) if row else None


def _meta_set(conn, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


class ProjectsStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self) -> None:
        conn = connect(self.db_path)
        try:
            migrate(conn)
        finally:
            conn.close()

    def _insert_project(self, conn, project: Project, *, sort_order: int) -> None:
        payload = dict(project)
        name = str(payload.get("name") or "")
        status = str(payload.get("status") or "planning")
        priority = str(payload.get("priority") or "medium")
        category = payload.get("category")
        category = str(category) if category is not None else None
        try:
            progress = int(payload.get("progress") or 0)
        except Exception:
            progress = 0

        created_at = str(payload.get("createdAt") or _now())
        updated_at = str(payload.get("updatedAt") or created_at)

        try:
            budget = float(payload.get("budget") or 0)
        except Exception:
            budget = 0.0
        if budget < 0:
            budget = 0.0

        try:
            actual_cost = float(payload.get("actualCost") or 0)
        except Exception:
            actual_cost = 0.0
        if actual_cost < 0:
            actual_cost = 0.0

        conn.execute(
            (
                "INSERT INTO projects(id, sort_order, name, status, priority, category, progress, created_at, updated_at, budget, actual_cost, payload_json) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            ),
            (
                str(payload.get("id")),
                int(sort_order),
                name,
                status,
                priority,
                category,
                int(progress),
                created_at,
                updated_at,
                float(budget),
                float(actual_cost),
                _json_dumps(payload),
            ),
        )

    def _row_to_project(self, row) -> Project:
        try:
            payload = _json_loads(row["payload_json"])
        except Exception:
            payload = {}
        if isinstance(payload, dict):
            # Ensure consistency with indexed columns.
            payload["id"] = row["id"]
            payload["name"] = row["name"]
            payload["status"] = row["status"]
            payload["priority"] = row["priority"]
            payload["category"] = row["category"]
            payload["progress"] = row["progress"]
            payload["createdAt"] = row["created_at"]
            payload["updatedAt"] = row["updated_at"]
            payload["budget"] = row["budget"]
            payload["actualCost"] = row["actual_cost"]
            return payload
        # Fallback: should never happen.
        return {
            "id": row["id"],
            "name": row["name"],
            "status": row["status"],
            "priority": row["priority"],
            "category": row["category"],
            "progress": row["progress"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "budget": row["budget"],
            "actualCost": row["actual_cost"],
        }

    def last_updated(self) -> Optional[str]:
        conn = connect(self.db_path)
        try:
            return _meta_get(conn, "projects.lastUpdated")
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
                where.append("status=?")
                args.append(status)
            if priority:
                where.append("priority=?")
                args.append(priority)
            if category:
                where.append("category=?")
                args.append(category)

            sql = "SELECT * FROM projects"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY sort_order ASC, created_at ASC"

            rows = conn.execute(sql, tuple(args)).fetchall()
            projects = [self._row_to_project(r) for r in rows]
            meta = {
                "total": len(projects),
                "lastUpdated": _meta_get(conn, "projects.lastUpdated"),
            }
            return projects, meta
        finally:
            conn.close()

    def get(self, project_id: str) -> Optional[Project]:
        conn = connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM projects WHERE id=?", (project_id,)
            ).fetchone()
            return self._row_to_project(row) if row else None
        finally:
            conn.close()

    def create(self, project_data: Dict[str, Any]) -> Project:
        np, _ = normalize_project(project_data)
        # Business rule: require a non-empty name.
        if not str(np.get("name") or "").strip():
            raise ValueError("Project name cannot be empty")

        conn = connect(self.db_path)
        try:
            with conn:
                row = conn.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) AS m FROM projects"
                ).fetchone()
                max_sort = int(row["m"] if row and row["m"] is not None else -1)
                self._insert_project(conn, np, sort_order=max_sort + 1)
                _meta_set(conn, "projects.lastUpdated", _now())
            return np
        finally:
            conn.close()

    def update(self, project_id: str, updates: Dict[str, Any]) -> Project:
        # Full PUT semantics in this codebase are basically a patch excluding protected fields.
        return self.patch(project_id, updates, if_updated_at=None)

    def patch(
        self, project_id: str, patch: Dict[str, Any], *, if_updated_at: Optional[str]
    ) -> Project:
        conn = connect(self.db_path)
        try:
            with conn:
                row = conn.execute(
                    "SELECT * FROM projects WHERE id=?", (project_id,)
                ).fetchone()
                if not row:
                    raise KeyError("not found")

                current = self._row_to_project(row)
                if if_updated_at and str(current.get("updatedAt") or "") != str(
                    if_updated_at
                ):
                    raise RuntimeError(
                        f"updatedAt mismatch: expected={if_updated_at}, actual={current.get('updatedAt')}"
                    )

                protected = {"id", "createdAt"}
                for k, v in (patch or {}).items():
                    if k in protected or k == "ifUpdatedAt":
                        continue
                    current[k] = v

                # Normalize to keep backward-compatible defaults.
                current["id"] = project_id
                current["updatedAt"] = _now()
                np, _ = normalize_project(current)

                conn.execute(
                    (
                        "UPDATE projects SET name=?, status=?, priority=?, category=?, progress=?, updated_at=?, budget=?, actual_cost=?, payload_json=? "
                        "WHERE id=?"
                    ),
                    (
                        str(np.get("name") or ""),
                        str(np.get("status") or "planning"),
                        str(np.get("priority") or "medium"),
                        str(np.get("category"))
                        if np.get("category") is not None
                        else None,
                        int(np.get("progress") or 0),
                        str(np.get("updatedAt") or _now()),
                        float(np.get("budget") or 0),
                        float(np.get("actualCost") or 0),
                        _json_dumps(np),
                        project_id,
                    ),
                )
                _meta_set(conn, "projects.lastUpdated", _now())
                return np
        finally:
            conn.close()

    def delete(self, project_id: str) -> None:
        conn = connect(self.db_path)
        try:
            with conn:
                cur = conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
                if cur.rowcount == 0:
                    raise KeyError("not found")
                _meta_set(conn, "projects.lastUpdated", _now())
        finally:
            conn.close()

    def reorder(self, ids: List[str]) -> List[Project]:
        conn = connect(self.db_path)
        try:
            with conn:
                # Map existing ids to current sort.
                rows = conn.execute(
                    "SELECT id FROM projects ORDER BY sort_order ASC, created_at ASC"
                ).fetchall()
                existing = [str(r["id"]) for r in rows]
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
                    conn.execute(
                        "UPDATE projects SET sort_order=? WHERE id=?", (idx, pid)
                    )

                _meta_set(conn, "projects.lastUpdated", _now())

            # Return reordered list.
            return self.list()[0]
        finally:
            conn.close()

    def batch_update(
        self, ops: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], bool]:
        conn = connect(self.db_path)
        try:
            results: List[Dict[str, Any]] = []
            changed = False
            with conn:
                for op in ops or []:
                    op_id = op.get("opId") if isinstance(op, dict) else None
                    try:
                        if not isinstance(op, dict):
                            raise ValueError("op must be an object")
                        pid = op.get("id")
                        patch = op.get("patch")
                        if_updated_at = op.get("ifUpdatedAt")
                        if not pid or not isinstance(pid, str):
                            raise ValueError("id is required")
                        if not isinstance(patch, dict):
                            raise ValueError("patch must be an object")

                        conn.execute("SAVEPOINT sp")
                        try:
                            row = conn.execute(
                                "SELECT * FROM projects WHERE id=?", (pid,)
                            ).fetchone()
                            if not row:
                                results.append(
                                    {
                                        "opId": op_id,
                                        "id": pid,
                                        "success": False,
                                        "error": f"Project not found: {pid}",
                                        "status": 404,
                                    }
                                )
                                conn.execute("RELEASE sp")
                                continue

                            cur = self._row_to_project(row)
                            if if_updated_at and str(cur.get("updatedAt") or "") != str(
                                if_updated_at
                            ):
                                results.append(
                                    {
                                        "opId": op_id,
                                        "id": pid,
                                        "success": False,
                                        "error": "Conflict: updatedAt mismatch",
                                        "status": 409,
                                        "data": {
                                            "expectedUpdatedAt": if_updated_at,
                                            "actualUpdatedAt": cur.get("updatedAt"),
                                        },
                                    }
                                )
                                conn.execute("RELEASE sp")
                                continue

                            protected = {"id", "createdAt"}
                            for k, v in patch.items():
                                if k in protected:
                                    continue
                                cur[k] = v
                            cur["updatedAt"] = _now()
                            np, _ = normalize_project(cur)
                            conn.execute(
                                (
                                    "UPDATE projects SET name=?, status=?, priority=?, category=?, progress=?, updated_at=?, budget=?, actual_cost=?, payload_json=? "
                                    "WHERE id=?"
                                ),
                                (
                                    str(np.get("name") or ""),
                                    str(np.get("status") or "planning"),
                                    str(np.get("priority") or "medium"),
                                    str(np.get("category"))
                                    if np.get("category") is not None
                                    else None,
                                    int(np.get("progress") or 0),
                                    str(np.get("updatedAt") or _now()),
                                    float(np.get("budget") or 0),
                                    float(np.get("actualCost") or 0),
                                    _json_dumps(np),
                                    pid,
                                ),
                            )
                            results.append(
                                {
                                    "opId": op_id,
                                    "id": pid,
                                    "success": True,
                                    "data": np,
                                    "status": 200,
                                }
                            )
                            changed = True
                            conn.execute("RELEASE sp")
                        except Exception:
                            conn.execute("ROLLBACK TO sp")
                            conn.execute("RELEASE sp")
                            raise
                    except Exception as e:
                        results.append(
                            {
                                "opId": op_id,
                                "success": False,
                                "error": str(e),
                                "status": 400,
                            }
                        )

                if changed:
                    _meta_set(conn, "projects.lastUpdated", _now())
            return results, changed
        finally:
            conn.close()

    def get_statistics(self) -> Dict[str, Any]:
        # Keep semantics identical to ProjectService.get_statistics().
        projects, _meta = self.list()
        stats: Dict[str, Any] = {
            "total": len(projects),
            "byStatus": {},
            "byPriority": {},
            "byCategory": {},
            "financial": {
                "totalBudget": 0,
                "totalCost": 0,
                "totalRevenue": 0,
                "netProfit": 0,
            },
        }

        for p in projects:
            if not isinstance(p, dict):
                continue
            st = p.get("status") or "unknown"
            stats["byStatus"][st] = stats["byStatus"].get(st, 0) + 1
            pr = p.get("priority") or "unknown"
            stats["byPriority"][pr] = stats["byPriority"].get(pr, 0) + 1
            cat = p.get("category") or "未分类"
            stats["byCategory"][cat] = stats["byCategory"].get(cat, 0) + 1

            try:
                budget = p.get("budget")
                if isinstance(budget, dict) and "planned" in budget:
                    stats["financial"]["totalBudget"] += float(
                        budget.get("planned") or 0
                    )
                elif isinstance(budget, (int, float)):
                    stats["financial"]["totalBudget"] += float(budget)
            except Exception:
                pass

            try:
                cost = p.get("cost")
                if isinstance(cost, dict) and "total" in cost:
                    stats["financial"]["totalCost"] += float(cost.get("total") or 0)
                elif isinstance(cost, (int, float)):
                    stats["financial"]["totalCost"] += float(cost)
            except Exception:
                pass

            try:
                revenue = p.get("revenue")
                if isinstance(revenue, dict) and "total" in revenue:
                    stats["financial"]["totalRevenue"] += float(
                        revenue.get("total") or 0
                    )
                elif isinstance(revenue, (int, float)):
                    stats["financial"]["totalRevenue"] += float(revenue)
            except Exception:
                pass

        stats["financial"]["netProfit"] = (
            stats["financial"]["totalRevenue"] - stats["financial"]["totalCost"]
        )
        return stats


class AgentRunsStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self) -> None:
        conn = connect(self.db_path)
        try:
            migrate(conn)
        finally:
            conn.close()

    def _insert_run(self, conn, run: AgentRun) -> None:
        payload = dict(run)

        project_id = payload.get("projectId")
        if project_id:
            row = conn.execute(
                "SELECT 1 AS ok FROM projects WHERE id=?", (str(project_id),)
            ).fetchone()
            if not row:
                project_id = None

        conn.execute(
            (
                "INSERT INTO agent_runs(id, project_id, agent_id, status, created_at, updated_at, started_at, finished_at, payload_json) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)"
            ),
            (
                str(payload.get("id")),
                project_id,
                payload.get("agentId"),
                payload.get("status"),
                payload.get("createdAt"),
                payload.get("updatedAt"),
                payload.get("startedAt"),
                payload.get("finishedAt"),
                _json_dumps(payload),
            ),
        )

    def _row_to_run(self, row) -> AgentRun:
        payload = _json_loads(row["payload_json"])
        if isinstance(payload, dict):
            payload["id"] = row["id"]
            payload["projectId"] = row["project_id"]
            payload["agentId"] = row["agent_id"]
            payload["status"] = row["status"]
            payload["createdAt"] = row["created_at"]
            payload["updatedAt"] = row["updated_at"]
            payload["startedAt"] = row["started_at"]
            payload["finishedAt"] = row["finished_at"]
            return payload
        return {"id": row["id"]}

    def create(self, run_data: Dict[str, Any]) -> AgentRun:
        nr, _ = normalize_agent_run(run_data)
        conn = connect(self.db_path)
        try:
            with conn:
                existing = conn.execute(
                    "SELECT * FROM agent_runs WHERE id=?", (str(nr.get("id")),)
                ).fetchone()
                if existing:
                    return self._row_to_run(existing)
                self._insert_run(conn, nr)
                _meta_set(conn, "agent_runs.lastUpdated", _now())
                return nr
        finally:
            conn.close()

    def get(self, run_id: str) -> Optional[AgentRun]:
        conn = connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM agent_runs WHERE id=?", (run_id,)
            ).fetchone()
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
                where.append("project_id=?")
                args.append(project_id)
            if agent_id:
                where.append("agent_id=?")
                args.append(agent_id)
            if status:
                where.append("status=?")
                args.append(status)

            sql_base = "FROM agent_runs"
            if where:
                sql_base += " WHERE " + " AND ".join(where)

            total_row = conn.execute(
                "SELECT COUNT(1) AS n " + sql_base, tuple(args)
            ).fetchone()
            total = int(total_row["n"] if total_row else 0)

            rows = conn.execute(
                "SELECT * " + sql_base + " ORDER BY created_at DESC LIMIT ? OFFSET ?",
                tuple(args + [int(limit), int(offset)]),
            ).fetchall()
            return [self._row_to_run(r) for r in rows], total
        finally:
            conn.close()

    def patch(self, run_id: str, patch: Dict[str, Any]) -> AgentRun:
        conn = connect(self.db_path)
        try:
            with conn:
                row = conn.execute(
                    "SELECT * FROM agent_runs WHERE id=?", (run_id,)
                ).fetchone()
                if not row:
                    raise KeyError("not found")
                cur = self._row_to_run(row)

                protected = {"id", "createdAt"}
                for k, v in (patch or {}).items():
                    if k in protected:
                        continue
                    if k == "links" and not isinstance(v, list):
                        continue
                    if k == "metrics" and not isinstance(v, dict):
                        continue
                    if k == "tags" and not isinstance(v, list):
                        continue
                    if k == "meta" and not isinstance(v, dict):
                        continue
                    cur[k] = v

                cur["id"] = run_id
                cur["updatedAt"] = _now()
                nr, _ = normalize_agent_run(cur)

                conn.execute(
                    (
                        "UPDATE agent_runs SET project_id=?, agent_id=?, status=?, created_at=?, updated_at=?, started_at=?, finished_at=?, payload_json=? "
                        "WHERE id=?"
                    ),
                    (
                        nr.get("projectId"),
                        nr.get("agentId"),
                        nr.get("status"),
                        nr.get("createdAt"),
                        nr.get("updatedAt"),
                        nr.get("startedAt"),
                        nr.get("finishedAt"),
                        _json_dumps(nr),
                        run_id,
                    ),
                )
                _meta_set(conn, "agent_runs.lastUpdated", _now())
                return nr
        finally:
            conn.close()


class AgentEventsStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self) -> None:
        conn = connect(self.db_path)
        try:
            migrate(conn)
        finally:
            conn.close()

    def _insert_event(self, conn, evt: AgentEvent) -> None:
        payload = dict(evt)
        conn.execute(
            (
                "INSERT OR IGNORE INTO agent_events(id, ts, type, level, project_id, run_id, agent_id, title, message, payload_json) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            ),
            (
                payload.get("id"),
                payload.get("ts"),
                payload.get("type"),
                payload.get("level"),
                payload.get("projectId"),
                payload.get("runId"),
                payload.get("agentId"),
                payload.get("title"),
                payload.get("message"),
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

    def exists(self, event_id: str) -> Optional[Dict[str, Any]]:
        if not event_id:
            return None
        conn = connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT payload_json FROM agent_events WHERE id=?", (event_id,)
            ).fetchone()
            if not row:
                return None
            obj = _json_loads(row["payload_json"])
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
    ) -> List[Dict[str, Any]]:
        # since_dt is a datetime or None (parsed in API layer).
        since = since_dt.isoformat() if since_dt else None

        conn = connect(self.db_path)
        try:
            where = []
            args: List[Any] = []
            if project_id:
                where.append("project_id=?")
                args.append(project_id)
            if run_id:
                where.append("run_id=?")
                args.append(run_id)
            if agent_id:
                where.append("agent_id=?")
                args.append(agent_id)
            if typ:
                where.append("type=?")
                args.append(typ)
            if since:
                where.append("ts>=?")
                args.append(since)

            sql = "SELECT payload_json FROM agent_events"
            if where:
                sql += " WHERE " + " AND ".join(where)
            # Mimic legacy behavior: return the most recent N events, in ascending time order.
            sql += " ORDER BY ts DESC"
            sql += " LIMIT ?"
            args.append(int(limit))

            rows = conn.execute(sql, tuple(args)).fetchall()
            out: List[Dict[str, Any]] = []
            for r in rows:
                try:
                    obj = _json_loads(r["payload_json"])
                except Exception:
                    continue
                if not isinstance(obj, dict):
                    continue
                out.append(self.normalize_for_read(obj))
            out.reverse()
            return out
        finally:
            conn.close()


class AgentProfilesStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self) -> None:
        conn = connect(self.db_path)
        try:
            migrate(conn)
        finally:
            conn.close()

    def _row_to_profile(self, row) -> AgentProfile:
        payload = _json_loads(row["payload_json"])
        if isinstance(payload, dict):
            payload["id"] = row["id"]
            payload["name"] = row["name"]
            payload["role"] = row["role"]
            payload["enabled"] = bool(row["enabled"])
            payload["createdAt"] = row["created_at"]
            payload["updatedAt"] = row["updated_at"]
            return payload
        return {
            "id": row["id"],
            "name": row["name"],
            "role": row["role"],
            "enabled": bool(row["enabled"]),
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def list(self, *, enabled: Optional[bool] = None) -> List[AgentProfile]:
        conn = connect(self.db_path)
        try:
            sql = "SELECT * FROM agent_profiles"
            args: List[Any] = []
            if enabled is not None:
                sql += " WHERE enabled=?"
                args.append(1 if enabled else 0)
            sql += " ORDER BY updated_at DESC"
            rows = conn.execute(sql, tuple(args)).fetchall()
            return [self._row_to_profile(r) for r in rows]
        finally:
            conn.close()

    def get(self, profile_id: str) -> Optional[AgentProfile]:
        conn = connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM agent_profiles WHERE id=?", (profile_id,)
            ).fetchone()
            return self._row_to_profile(row) if row else None
        finally:
            conn.close()

    def create(self, payload: Dict[str, Any]) -> AgentProfile:
        prof, _ = normalize_agent_profile(payload)
        conn = connect(self.db_path)
        try:
            with conn:
                row = conn.execute(
                    "SELECT * FROM agent_profiles WHERE id=?", (prof["id"],)
                ).fetchone()
                if row:
                    return self._row_to_profile(row)
                conn.execute(
                    (
                        "INSERT INTO agent_profiles(id, name, role, enabled, created_at, updated_at, payload_json) "
                        "VALUES(?, ?, ?, ?, ?, ?, ?)"
                    ),
                    (
                        prof["id"],
                        str(prof.get("name") or ""),
                        str(prof.get("role") or ""),
                        1 if bool(prof.get("enabled", True)) else 0,
                        str(prof.get("createdAt") or _now()),
                        str(prof.get("updatedAt") or _now()),
                        _json_dumps(prof),
                    ),
                )
                _meta_set(conn, "agent_profiles.lastUpdated", _now())
                return prof
        finally:
            conn.close()

    def patch(self, profile_id: str, patch: Dict[str, Any]) -> AgentProfile:
        conn = connect(self.db_path)
        try:
            with conn:
                row = conn.execute(
                    "SELECT * FROM agent_profiles WHERE id=?", (profile_id,)
                ).fetchone()
                if not row:
                    raise KeyError("not found")
                cur = self._row_to_profile(row)
                for k, v in (patch or {}).items():
                    if k in {"id", "createdAt"}:
                        continue
                    cur[k] = v
                cur["id"] = profile_id
                cur["updatedAt"] = _now()
                np, _ = normalize_agent_profile(cur)
                conn.execute(
                    (
                        "UPDATE agent_profiles SET name=?, role=?, enabled=?, updated_at=?, payload_json=? WHERE id=?"
                    ),
                    (
                        str(np.get("name") or ""),
                        str(np.get("role") or ""),
                        1 if bool(np.get("enabled", True)) else 0,
                        str(np.get("updatedAt") or _now()),
                        _json_dumps(np),
                        profile_id,
                    ),
                )
                _meta_set(conn, "agent_profiles.lastUpdated", _now())
                return np
        finally:
            conn.close()

    def delete(self, profile_id: str) -> None:
        conn = connect(self.db_path)
        try:
            with conn:
                cur = conn.execute(
                    "DELETE FROM agent_profiles WHERE id=?", (profile_id,)
                )
                if cur.rowcount == 0:
                    raise KeyError("not found")
                _meta_set(conn, "agent_profiles.lastUpdated", _now())
        finally:
            conn.close()


class AgentCapabilitiesStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self) -> None:
        conn = connect(self.db_path)
        try:
            migrate(conn)
        finally:
            conn.close()

    def _row_to_capability(self, row) -> AgentCapability:
        payload = _json_loads(row["payload_json"])
        if isinstance(payload, dict):
            payload["id"] = row["id"]
            payload["name"] = row["name"]
            payload["enabled"] = bool(row["enabled"])
            payload["createdAt"] = row["created_at"]
            payload["updatedAt"] = row["updated_at"]
            return payload
        return {
            "id": row["id"],
            "name": row["name"],
            "enabled": bool(row["enabled"]),
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def list(self, *, enabled: Optional[bool] = None) -> List[AgentCapability]:
        conn = connect(self.db_path)
        try:
            sql = "SELECT * FROM agent_capabilities"
            args: List[Any] = []
            if enabled is not None:
                sql += " WHERE enabled=?"
                args.append(1 if enabled else 0)
            sql += " ORDER BY updated_at DESC"
            rows = conn.execute(sql, tuple(args)).fetchall()
            return [self._row_to_capability(r) for r in rows]
        finally:
            conn.close()

    def get(self, capability_id: str) -> Optional[AgentCapability]:
        conn = connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM agent_capabilities WHERE id=?", (capability_id,)
            ).fetchone()
            return self._row_to_capability(row) if row else None
        finally:
            conn.close()

    def create(self, payload: Dict[str, Any]) -> AgentCapability:
        cap, _ = normalize_agent_capability(payload)
        conn = connect(self.db_path)
        try:
            with conn:
                row = conn.execute(
                    "SELECT * FROM agent_capabilities WHERE id=?", (cap["id"],)
                ).fetchone()
                if row:
                    return self._row_to_capability(row)
                conn.execute(
                    (
                        "INSERT INTO agent_capabilities(id, name, enabled, created_at, updated_at, payload_json) "
                        "VALUES(?, ?, ?, ?, ?, ?)"
                    ),
                    (
                        cap["id"],
                        str(cap.get("name") or ""),
                        1 if bool(cap.get("enabled", True)) else 0,
                        str(cap.get("createdAt") or _now()),
                        str(cap.get("updatedAt") or _now()),
                        _json_dumps(cap),
                    ),
                )
                _meta_set(conn, "agent_capabilities.lastUpdated", _now())
                return cap
        finally:
            conn.close()

    def patch(self, capability_id: str, patch: Dict[str, Any]) -> AgentCapability:
        conn = connect(self.db_path)
        try:
            with conn:
                row = conn.execute(
                    "SELECT * FROM agent_capabilities WHERE id=?", (capability_id,)
                ).fetchone()
                if not row:
                    raise KeyError("not found")
                cur = self._row_to_capability(row)
                for k, v in (patch or {}).items():
                    if k in {"id", "createdAt"}:
                        continue
                    cur[k] = v
                cur["id"] = capability_id
                cur["updatedAt"] = _now()
                nc, _ = normalize_agent_capability(cur)
                conn.execute(
                    "UPDATE agent_capabilities SET name=?, enabled=?, updated_at=?, payload_json=? WHERE id=?",
                    (
                        str(nc.get("name") or ""),
                        1 if bool(nc.get("enabled", True)) else 0,
                        str(nc.get("updatedAt") or _now()),
                        _json_dumps(nc),
                        capability_id,
                    ),
                )
                _meta_set(conn, "agent_capabilities.lastUpdated", _now())
                return nc
        finally:
            conn.close()

    def delete(self, capability_id: str) -> None:
        conn = connect(self.db_path)
        try:
            with conn:
                cur = conn.execute(
                    "DELETE FROM agent_capabilities WHERE id=?", (capability_id,)
                )
                if cur.rowcount == 0:
                    raise KeyError("not found")
                _meta_set(conn, "agent_capabilities.lastUpdated", _now())
        finally:
            conn.close()


class TokenUsageStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self) -> None:
        conn = connect(self.db_path)
        try:
            migrate(conn)
        finally:
            conn.close()

    def _row_to_usage(self, row) -> TokenUsageRecord:
        payload = _json_loads(row["payload_json"])
        if isinstance(payload, dict):
            payload["id"] = row["id"]
            payload["ts"] = row["ts"]
            payload["projectId"] = row["project_id"]
            payload["runId"] = row["run_id"]
            payload["agentId"] = row["agent_id"]
            payload["workspace"] = row["workspace"]
            payload["sessionId"] = row["session_id"]
            payload["source"] = row["source"]
            payload["model"] = row["model"]
            payload["promptTokens"] = int(row["prompt_tokens"] or 0)
            payload["completionTokens"] = int(row["completion_tokens"] or 0)
            payload["totalTokens"] = int(row["total_tokens"] or 0)
            payload["cost"] = float(row["cost"] or 0)
            return payload
        return {
            "id": row["id"],
            "ts": row["ts"],
            "projectId": row["project_id"],
            "runId": row["run_id"],
            "agentId": row["agent_id"],
            "workspace": row["workspace"],
            "sessionId": row["session_id"],
            "source": row["source"],
            "model": row["model"],
            "promptTokens": int(row["prompt_tokens"] or 0),
            "completionTokens": int(row["completion_tokens"] or 0),
            "totalTokens": int(row["total_tokens"] or 0),
            "cost": float(row["cost"] or 0),
            "data": {},
        }

    def ingest(self, payload: Dict[str, Any]) -> Tuple[TokenUsageRecord, bool]:
        rec, _ = normalize_token_usage_record(payload)
        conn = connect(self.db_path)
        try:
            with conn:
                existing = conn.execute(
                    "SELECT * FROM token_usage_records WHERE id=?", (rec["id"],)
                ).fetchone()
                if existing:
                    return self._row_to_usage(existing), False
                conn.execute(
                    (
                        "INSERT INTO token_usage_records("
                        "id, ts, project_id, run_id, agent_id, workspace, session_id, source, model, "
                        "prompt_tokens, completion_tokens, total_tokens, cost, payload_json"
                        ") VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                    ),
                    (
                        rec["id"],
                        rec.get("ts"),
                        rec.get("projectId"),
                        rec.get("runId"),
                        rec.get("agentId"),
                        rec.get("workspace"),
                        rec.get("sessionId"),
                        rec.get("source"),
                        rec.get("model"),
                        int(rec.get("promptTokens") or 0),
                        int(rec.get("completionTokens") or 0),
                        int(rec.get("totalTokens") or 0),
                        float(rec.get("cost") or 0),
                        _json_dumps(rec),
                    ),
                )
                _meta_set(conn, "token_usage.lastUpdated", _now())
                return rec, True
        finally:
            conn.close()

    def list(
        self,
        *,
        project_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        workspace: Optional[str] = None,
        source: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: int = 200,
    ) -> List[TokenUsageRecord]:
        conn = connect(self.db_path)
        try:
            where = []
            args: List[Any] = []
            if project_id:
                where.append("project_id=?")
                args.append(project_id)
            if agent_id:
                where.append("agent_id=?")
                args.append(agent_id)
            if workspace:
                where.append("workspace=?")
                args.append(workspace)
            if source:
                where.append("source=?")
                args.append(source)
            if since:
                where.append("ts>=?")
                args.append(since)
            if until:
                where.append("ts<=?")
                args.append(until)

            sql = "SELECT * FROM token_usage_records"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY ts DESC LIMIT ?"
            args.append(max(1, min(5000, int(limit))))

            rows = conn.execute(sql, tuple(args)).fetchall()
            return [self._row_to_usage(r) for r in rows]
        finally:
            conn.close()

    def aggregate(self, **filters) -> Dict[str, Any]:
        items = self.list(**filters, limit=5000)

        def _blank() -> Dict[str, Any]:
            return {
                "records": 0,
                "promptTokens": 0,
                "completionTokens": 0,
                "totalTokens": 0,
                "cost": 0.0,
            }

        out = {
            "totals": _blank(),
            "byDay": {},
            "byProject": {},
            "byAgent": {},
            "byWorkspace": {},
            "byModel": {},
        }

        def _acc(bucket: Dict[str, Any], rec: TokenUsageRecord) -> None:
            bucket["records"] += 1
            bucket["promptTokens"] += int(rec.get("promptTokens") or 0)
            bucket["completionTokens"] += int(rec.get("completionTokens") or 0)
            bucket["totalTokens"] += int(rec.get("totalTokens") or 0)
            bucket["cost"] += float(rec.get("cost") or 0)

        for rec in items:
            _acc(out["totals"], rec)
            day = str(rec.get("ts") or "")[:10] or "unknown"
            pid = str(rec.get("projectId") or "unassigned")
            aid = str(rec.get("agentId") or "unassigned")
            wsp = str(rec.get("workspace") or "unknown")
            mdl = str(rec.get("model") or "unknown")

            for group_name, key in (
                ("byDay", day),
                ("byProject", pid),
                ("byAgent", aid),
                ("byWorkspace", wsp),
                ("byModel", mdl),
            ):
                if key not in out[group_name]:
                    out[group_name][key] = _blank()
                _acc(out[group_name][key], rec)

        def _to_list(
            d: Dict[str, Dict[str, Any]], key_name: str
        ) -> List[Dict[str, Any]]:
            rows = []
            for k, v in d.items():
                row = {key_name: k}
                row.update(v)
                rows.append(row)
            rows.sort(key=lambda x: x.get("totalTokens", 0), reverse=True)
            return rows

        return {
            "totals": out["totals"],
            "byDay": sorted(_to_list(out["byDay"], "day"), key=lambda x: x["day"]),
            "byProject": _to_list(out["byProject"], "projectId"),
            "byAgent": _to_list(out["byAgent"], "agentId"),
            "byWorkspace": _to_list(out["byWorkspace"], "workspace"),
            "byModel": _to_list(out["byModel"], "model"),
        }
