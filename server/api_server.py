#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目管理系统 REST API 服务
提供HTTP接口进行项目数据的增删改查
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import uuid
import subprocess
import hmac
from collections import deque
import shutil
import shlex

app = Flask(__name__, static_folder='../web', static_url_path='')
CORS(app)  # 允许跨域请求

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'projects.json')
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

AGENT_RUNS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'agent_runs.json')
AGENT_EVENTS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'agent_events.jsonl')

DEPLOY_LOG_FILE = os.path.join(ROOT_DIR, 'deploy_run.log')
DEPLOY_STATE_FILE = os.path.join(ROOT_DIR, 'deploy_state.json')
DEPLOY_UNIT_PREFIX = 'myprojectmanager-deploy-'


def require_admin():
    token = os.environ.get('PM_ADMIN_TOKEN', '').strip()
    if not token:
        return False, (jsonify({
            "success": False,
            "error": "Admin token not configured. Set PM_ADMIN_TOKEN in service environment."
        }), 503)

    got = request.headers.get('X-PM-Token', '').strip()
    if not got or not hmac.compare_digest(got, token):
        return False, (jsonify({
            "success": False,
            "error": "Unauthorized"
        }), 401)
    return True, None


def require_agent():
    """Optional auth for agent-facing APIs.

    If PM_AGENT_TOKEN is not set, the agent APIs are open (local-first default).
    If PM_AGENT_TOKEN is set, callers must send X-PM-Agent-Token.
    """
    token = os.environ.get('PM_AGENT_TOKEN', '').strip()
    if not token:
        return True, None

    got = request.headers.get('X-PM-Agent-Token', '').strip()
    # Allow reuse of the admin header name for convenience when self-hosting.
    if not got:
        got = request.headers.get('X-PM-Token', '').strip()
    if not got or not hmac.compare_digest(got, token):
        return False, (jsonify({
            "success": False,
            "error": "Unauthorized"
        }), 401)
    return True, None


def read_last_lines(file_path: str, max_lines: int = 200) -> List[str]:
    try:
        dq = deque(maxlen=max_lines)
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                dq.append(line.rstrip('\n'))
        return list(dq)
    except FileNotFoundError:
        return []


def read_json_file(file_path: str) -> Optional[Dict]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def write_json_file(file_path: str, data: Dict):
    tmp = f"{file_path}.tmp"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, file_path)


def load_agent_runs() -> Dict:
    if not os.path.exists(AGENT_RUNS_FILE):
        data = {
            "version": "1.0.0",
            "lastUpdated": datetime.now().isoformat(),
            "runs": [],
        }
        save_agent_runs(data)
        return data

    obj = read_json_file(AGENT_RUNS_FILE)
    norm, changed = normalize_agent_runs_store(obj)
    if changed:
        save_agent_runs(norm)
    return norm


def save_agent_runs(data: Dict):
    data['lastUpdated'] = datetime.now().isoformat()
    write_json_file(AGENT_RUNS_FILE, data)


def normalize_agent_runs_store(raw) -> (Dict, bool):
    changed = False
    now = datetime.now().isoformat()

    if not isinstance(raw, dict):
        raw = {}
        changed = True

    data = dict(raw)
    if not isinstance(data.get('version'), str) or not data.get('version'):
        data['version'] = '1.0.0'
        changed = True
    if not isinstance(data.get('lastUpdated'), str) or not data.get('lastUpdated'):
        data['lastUpdated'] = now
        changed = True

    runs = data.get('runs')
    if not isinstance(runs, list):
        runs = []
        data['runs'] = runs
        changed = True

    for i, r in enumerate(list(runs)):
        nr, ch = normalize_agent_run(r)
        if ch:
            runs[i] = nr
            changed = True

    return data, changed


def normalize_agent_run(r) -> (Dict, bool):
    changed = False
    now = datetime.now().isoformat()

    if not isinstance(r, dict):
        r = {}
        changed = True
    run = dict(r)

    rid = run.get('id')
    if not isinstance(rid, str) or not rid.strip():
        run['id'] = f"run-{str(uuid.uuid4())[:8]}"
        changed = True

    for k in ('createdAt', 'updatedAt', 'startedAt'):
        v = run.get(k)
        if not isinstance(v, str) or not v:
            run[k] = now
            changed = True

    status = run.get('status')
    if not isinstance(status, str) or not status:
        run['status'] = 'running'
        changed = True

    # Optional fields
    for k in ('projectId', 'agentId', 'title', 'summary', 'finishedAt'):
        if k not in run:
            run[k] = None
            changed = True

    links = run.get('links')
    if links is None:
        run['links'] = []
        changed = True
    elif not isinstance(links, list):
        run['links'] = [links]
        changed = True

    tags = run.get('tags')
    if tags is None:
        run['tags'] = []
        changed = True
    elif not isinstance(tags, list):
        run['tags'] = [str(tags)] if str(tags).strip() else []
        changed = True

    metrics = run.get('metrics')
    if metrics is None:
        run['metrics'] = {}
        changed = True
    elif not isinstance(metrics, dict):
        run['metrics'] = {}
        changed = True

    meta = run.get('meta')
    if meta is None:
        run['meta'] = {}
        changed = True
    elif not isinstance(meta, dict):
        run['meta'] = {}
        changed = True

    return run, changed


def append_agent_event(event: Dict):
    os.makedirs(os.path.dirname(AGENT_EVENTS_FILE), exist_ok=True)
    with open(AGENT_EVENTS_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')


def parse_iso(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def clamp_int(v: int, lo: int, hi: int) -> int:
    try:
        iv = int(v)
    except Exception:
        iv = lo
    if iv < lo:
        return lo
    if iv > hi:
        return hi
    return iv


def deploy_state_read() -> Dict:
    return read_json_file(DEPLOY_STATE_FILE) or {}


def deploy_state_write(patch: Dict):
    cur = deploy_state_read()
    cur.update(patch)
    cur['updatedAt'] = datetime.now().isoformat()
    write_json_file(DEPLOY_STATE_FILE, cur)


def systemctl_show(unit: str, props: List[str]) -> Dict[str, str]:
    if not unit:
        return {}
    if not shutil.which('systemctl'):
        return {}
    args = ['systemctl', 'show', unit]
    for p in props:
        args.extend(['-p', p])
    try:
        p = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=3,
            check=False,
        )
        out = p.stdout or ''
        data = {}
        for line in out.splitlines():
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            data[k.strip()] = v.strip()
        return data
    except Exception:
        return {}


def parse_deploy_finish_from_log(job_id: str) -> Optional[int]:
    if not job_id:
        return None
    lines = read_last_lines(DEPLOY_LOG_FILE, max_lines=800)

    # Preferred marker: [INFO] Deploy finished jobId=... (exit=0)
    needle = f"Deploy finished jobId={job_id}"
    for line in reversed(lines):
        if needle not in line:
            continue
        i = line.find('(exit=')
        if i < 0:
            return None
        j = line.find(')', i)
        if j < 0:
            j = len(line)
        raw = line[i + len('(exit='):j]
        try:
            return int(str(raw).strip())
        except Exception:
            return None

    # Back-compat: find JobId block, then parse the last "Deploy finished (exit=...)" after it.
    start_idx = -1
    for idx in range(len(lines) - 1, -1, -1):
        if lines[idx].strip() == f"[INFO] JobId: {job_id}":
            start_idx = idx
            break
    if start_idx < 0:
        return None

    for line in reversed(lines[start_idx:]):
        if 'Deploy finished (exit=' not in line:
            continue
        i = line.find('(exit=')
        if i < 0:
            continue
        j = line.find(')', i)
        if j < 0:
            j = len(line)
        raw = line[i + len('(exit='):j]
        try:
            return int(str(raw).strip())
        except Exception:
            return None
    return None

def load_data() -> Dict:
    """加载项目数据。

    Backward compatibility:
    - If fields are missing or wrong-typed, fill defaults.
    - If any normalization happens, write back to disk.
    """
    if not os.path.exists(DATA_FILE):
        data = {
            "version": "1.0.0",
            "lastUpdated": datetime.now().isoformat(),
            "projects": []
        }
        # Persist the initial structure so future tooling can rely on it.
        save_data(data)
        return data

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    data, changed = normalize_projects_store(raw)
    if changed:
        save_data(data)
    return data

def save_data(data: Dict):
    """保存项目数据"""
    data["lastUpdated"] = datetime.now().isoformat()
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_projects_store(raw) -> (Dict, bool):
    """Normalize projects.json content, returning (data, changed)."""
    changed = False
    now = datetime.now().isoformat()

    if not isinstance(raw, dict):
        raw = {}
        changed = True

    data = dict(raw)
    if not isinstance(data.get('version'), str) or not data.get('version'):
        data['version'] = '1.0.0'
        changed = True
    if not isinstance(data.get('lastUpdated'), str) or not data.get('lastUpdated'):
        data['lastUpdated'] = now
        changed = True

    projects = data.get('projects')
    if not isinstance(projects, list):
        projects = []
        data['projects'] = projects
        changed = True

    for i, p in enumerate(list(projects)):
        np, ch = normalize_project(p)
        if ch:
            projects[i] = np
            changed = True

    return data, changed


def normalize_project(p) -> (Dict, bool):
    """Normalize a single project record, returning (project, changed)."""
    changed = False
    now = datetime.now().isoformat()

    if not isinstance(p, dict):
        p = {}
        changed = True
    project = dict(p)

    # Identity
    pid = project.get('id')
    if not isinstance(pid, str) or not pid.strip():
        project['id'] = f"proj-{str(uuid.uuid4())[:8]}"
        changed = True

    # Name
    name = project.get('name')
    if name is None:
        project['name'] = ''
        changed = True

    # Timestamps
    created_at = project.get('createdAt')
    updated_at = project.get('updatedAt')
    if not isinstance(created_at, str) or not created_at:
        # Prefer existing updatedAt if present, otherwise now
        project['createdAt'] = updated_at if isinstance(updated_at, str) and updated_at else now
        changed = True
    if not isinstance(updated_at, str) or not updated_at:
        project['updatedAt'] = now
        changed = True

    # Core fields
    status = project.get('status')
    if not isinstance(status, str) or not status:
        project['status'] = 'planning'
        changed = True
    priority = project.get('priority')
    if not isinstance(priority, str) or not priority:
        project['priority'] = 'medium'
        changed = True

    progress = project.get('progress')
    try:
        prog = int(progress) if progress is not None else 0
    except Exception:
        prog = 0
    if prog < 0:
        prog = 0
    if prog > 100:
        prog = 100
    if project.get('progress') != prog:
        project['progress'] = prog
        changed = True

    desc = project.get('description')
    if desc is None:
        project['description'] = ''
        changed = True
    notes = project.get('notes')
    if notes is None:
        project['notes'] = ''
        changed = True

    # Tags
    tags = project.get('tags')
    if tags is None:
        project['tags'] = []
        changed = True
    elif not isinstance(tags, list):
        project['tags'] = [str(tags)] if str(tags).strip() else []
        changed = True
    else:
        # Normalize to list[str] without empties
        nt = []
        for t in tags:
            s = str(t).strip()
            if s:
                nt.append(s)
        if nt != tags:
            project['tags'] = nt
            changed = True

    # Cost / Revenue
    for key in ('cost', 'revenue'):
        v = project.get(key)
        if v is None:
            project[key] = {'total': 0}
            changed = True
        elif isinstance(v, (int, float)):
            project[key] = {'total': float(v)}
            changed = True
        elif isinstance(v, dict):
            total = v.get('total')
            try:
                tv = float(total) if total is not None else 0.0
            except Exception:
                tv = 0.0
            if tv < 0:
                tv = 0.0
            # Keep other keys, but ensure total is numeric
            if v.get('total') != tv:
                nv = dict(v)
                nv['total'] = tv
                project[key] = nv
                changed = True
        else:
            project[key] = {'total': 0}
            changed = True

    return project, changed

# === API 路由 ===

@app.route('/')
def index():
    """返回前端页面"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """获取所有项目（支持筛选）"""
    data = load_data()
    projects = data["projects"]
    
    # 查询参数筛选
    status = request.args.get('status')
    priority = request.args.get('priority')
    category = request.args.get('category')
    
    if status:
        projects = [p for p in projects if p.get('status') == status]
    if priority:
        projects = [p for p in projects if p.get('priority') == priority]
    if category:
        projects = [p for p in projects if p.get('category') == category]
    
    return jsonify({
        "success": True,
        "data": projects,
        "total": len(projects),
        "lastUpdated": data.get("lastUpdated")
    })

@app.route('/api/projects/<project_id>', methods=['GET'])
def get_project(project_id: str):
    """获取单个项目详情"""
    data = load_data()
    
    for project in data["projects"]:
        if project["id"] == project_id:
            return jsonify({
                "success": True,
                "data": project
            })
    
    return jsonify({
        "success": False,
        "error": f"项目未找到: {project_id}"
    }), 404

@app.route('/api/projects', methods=['POST'])
def create_project():
    """创建新项目"""
    try:
        project_data = request.json
        
        # 验证必需字段
        if not project_data.get('name'):
            return jsonify({
                "success": False,
                "error": "项目名称不能为空"
            }), 400
        
        # 生成项目ID
        if "id" not in project_data:
            project_data["id"] = f"proj-{str(uuid.uuid4())[:8]}"
        
        # 设置时间戳
        now = datetime.now().isoformat()
        project_data["createdAt"] = now
        project_data["updatedAt"] = now
        
        # 设置默认值
        project_data.setdefault("status", "planning")
        project_data.setdefault("priority", "medium")
        project_data.setdefault("progress", 0)
        project_data.setdefault("description", "")
        project_data.setdefault("notes", "")
        project_data.setdefault("cost", {"total": 0})
        project_data.setdefault("revenue", {"total": 0})
        
        # 保存数据
        data = load_data()
        data["projects"].append(project_data)
        save_data(data)
        
        return jsonify({
            "success": True,
            "data": project_data,
            "message": "项目创建成功"
        }), 201
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/projects/<project_id>', methods=['PUT'])
def update_project(project_id: str):
    """更新项目"""
    try:
        updates = request.json
        data = load_data()
        
        # 查找项目
        project = None
        for p in data["projects"]:
            if p["id"] == project_id:
                project = p
                break
        
        if not project:
            return jsonify({
                "success": False,
                "error": f"项目未找到: {project_id}"
            }), 404
        
        # 更新字段（排除不应被修改的字段）
        protected_fields = ["id", "createdAt"]
        for key, value in updates.items():
            if key not in protected_fields:
                project[key] = value
        
        project["updatedAt"] = datetime.now().isoformat()
        save_data(data)
        
        return jsonify({
            "success": True,
            "data": project,
            "message": "项目更新成功"
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/projects/reorder', methods=['POST'])
def reorder_projects():
    """按照给定顺序重排项目列表（用于拖拽排序持久化）"""
    try:
        body = request.json or {}
        ids = body.get('ids')
        if not isinstance(ids, list):
            return jsonify({
                "success": False,
                "error": "ids 必须是数组"
            }), 400

        data = load_data()
        projects = data.get("projects", [])

        by_id = {}
        for p in projects:
            pid = p.get('id')
            if pid:
                by_id[pid] = p

        new_projects = []
        seen = set()
        for pid in ids:
            if pid in by_id and pid not in seen:
                new_projects.append(by_id[pid])
                seen.add(pid)

        # Append any projects not included in ids, preserving current order.
        for p in projects:
            pid = p.get('id')
            if pid and pid not in seen:
                new_projects.append(p)
                seen.add(pid)

        data["projects"] = new_projects
        save_data(data)

        return jsonify({
            "success": True,
            "data": new_projects,
            "total": len(new_projects),
            "lastUpdated": data.get("lastUpdated")
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id: str):
    """删除项目"""
    try:
        data = load_data()
        projects = data["projects"]
        
        # 查找并删除项目
        for i, project in enumerate(projects):
            if project["id"] == project_id:
                del projects[i]
                save_data(data)
                return jsonify({
                    "success": True,
                    "message": f"项目已删除: {project_id}"
                })
        
        return jsonify({
            "success": False,
            "error": f"项目未找到: {project_id}"
        }), 404
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """获取统计信息"""
    try:
        data = load_data()
        projects = data["projects"]
        
        stats = {
            "total": len(projects),
            "byStatus": {},
            "byPriority": {},
            "byCategory": {},
            "financial": {
                "totalBudget": 0,
                "totalCost": 0,
                "totalRevenue": 0,
                "netProfit": 0
            }
        }
        
        for p in projects:
            # 状态统计
            status = p.get("status", "unknown")
            stats["byStatus"][status] = stats["byStatus"].get(status, 0) + 1
            
            # 优先级统计
            priority = p.get("priority", "unknown")
            stats["byPriority"][priority] = stats["byPriority"].get(priority, 0) + 1
            
            # 分类统计
            category = p.get("category", "未分类")
            stats["byCategory"][category] = stats["byCategory"].get(category, 0) + 1
            
            # 财务统计
            if "budget" in p and "planned" in p["budget"]:
                stats["financial"]["totalBudget"] += p["budget"]["planned"]
            if "cost" in p and "total" in p["cost"]:
                stats["financial"]["totalCost"] += p["cost"]["total"]
            if "revenue" in p and "total" in p["revenue"]:
                stats["financial"]["totalRevenue"] += p["revenue"]["total"]
        
        stats["financial"]["netProfit"] = (
            stats["financial"]["totalRevenue"] - stats["financial"]["totalCost"]
        )
        
        return jsonify({
            "success": True,
            "data": stats
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        "success": True,
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/meta', methods=['GET'])
def api_meta():
    """Lightweight, agent-friendly metadata about the service."""
    data = load_data()
    return jsonify({
        "success": True,
        "data": {
            "service": "MyProjectManager",
            "apiBase": "/api",
            "dataLastUpdated": data.get("lastUpdated"),
            "projectCount": len(data.get("projects", []) or []),
            "enums": {
                "status": ["planning", "in-progress", "paused", "completed", "cancelled"],
                "priority": ["low", "medium", "high", "urgent"],
            },
            "auth": {
                "agentTokenRequired": bool(os.environ.get('PM_AGENT_TOKEN', '').strip()),
                "adminTokenRequired": bool(os.environ.get('PM_ADMIN_TOKEN', '').strip()),
                "agentHeader": "X-PM-Agent-Token",
                "adminHeader": "X-PM-Token",
            },
            "capabilities": {
                "projects": True,
                "stats": True,
                "agentRuns": True,
                "agentEvents": True,
                "agentActions": True,
                "projectsBatch": True,
                "projectsPatch": True,
            }
        }
    })


@app.route('/api/projects/<project_id>', methods=['PATCH'])
def patch_project(project_id: str):
    """Partial update for agents (same semantics as PUT, but explicitly PATCH)."""
    try:
        updates = request.get_json(silent=True) or {}
        data = load_data()

        project = None
        for p in data.get("projects", []):
            if p.get("id") == project_id:
                project = p
                break

        if not project:
            return jsonify({
                "success": False,
                "error": f"项目未找到: {project_id}"
            }), 404

        # Optional optimistic concurrency.
        want = (updates or {}).get('ifUpdatedAt')
        if want and str(project.get('updatedAt') or '') != str(want):
            return jsonify({
                "success": False,
                "error": "Conflict: updatedAt mismatch",
                "data": {
                    "expectedUpdatedAt": want,
                    "actualUpdatedAt": project.get('updatedAt'),
                }
            }), 409
        if isinstance(updates, dict) and 'ifUpdatedAt' in updates:
            updates = {k: v for k, v in updates.items() if k != 'ifUpdatedAt'}

        protected_fields = ["id", "createdAt"]
        for key, value in (updates or {}).items():
            if key not in protected_fields:
                project[key] = value

        project["updatedAt"] = datetime.now().isoformat()
        save_data(data)

        return jsonify({
            "success": True,
            "data": project,
            "message": "项目更新成功"
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/projects/batch', methods=['POST'])
def batch_update_projects():
    """Batch operations for agents.

    Body:
      {"ops": [{"id": "proj-...", "patch": {...}, "ifUpdatedAt": "...", "opId": "..."}, ...]}
    """
    try:
        body = request.get_json(silent=True) or {}
        ops = body.get('ops')
        if not isinstance(ops, list):
            return jsonify({
                "success": False,
                "error": "ops must be an array",
            }), 400

        data = load_data()
        projects = data.get('projects', []) or []
        by_id = {p.get('id'): p for p in projects if p.get('id')}

        results = []
        changed = False
        now = datetime.now().isoformat()

        for op in ops:
            op_id = None
            try:
                if not isinstance(op, dict):
                    raise ValueError('op must be an object')
                op_id = op.get('opId')
                pid = op.get('id')
                patch = op.get('patch')
                if_updated_at = op.get('ifUpdatedAt')

                if not pid or not isinstance(pid, str):
                    raise ValueError('id is required')
                if not isinstance(patch, dict):
                    raise ValueError('patch must be an object')

                project = by_id.get(pid)
                if not project:
                    results.append({
                        "opId": op_id,
                        "id": pid,
                        "success": False,
                        "error": f"项目未找到: {pid}",
                        "status": 404,
                    })
                    continue

                if if_updated_at and str(project.get('updatedAt') or '') != str(if_updated_at):
                    results.append({
                        "opId": op_id,
                        "id": pid,
                        "success": False,
                        "error": "Conflict: updatedAt mismatch",
                        "status": 409,
                        "data": {
                            "expectedUpdatedAt": if_updated_at,
                            "actualUpdatedAt": project.get('updatedAt'),
                        }
                    })
                    continue

                protected_fields = ["id", "createdAt"]
                for k, v in patch.items():
                    if k not in protected_fields:
                        project[k] = v
                project['updatedAt'] = now
                changed = True
                results.append({
                    "opId": op_id,
                    "id": pid,
                    "success": True,
                    "data": project,
                    "status": 200,
                })
            except Exception as e:
                results.append({
                    "opId": op_id,
                    "success": False,
                    "error": str(e),
                    "status": 400,
                })

        if changed:
            save_data(data)

        return jsonify({
            "success": True,
            "data": {
                "results": results,
                "changed": changed,
                "lastUpdated": data.get('lastUpdated'),
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def _agent_event_exists(event_id: str, max_lines: int = 5000) -> Optional[Dict]:
    if not event_id:
        return None
    lines = read_last_lines(AGENT_EVENTS_FILE, max_lines=max_lines)
    for line in reversed(lines):
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict) and obj.get('id') == event_id:
            return obj
    return None


def normalize_agent_event(obj) -> Dict:
    """Normalize an event dict for read responses.

    NOTE: This does NOT write back to disk (events log is append-only).
    """
    if not isinstance(obj, dict):
        obj = {}

    out = dict(obj)
    # Required-ish fields
    if 'id' not in out:
        out['id'] = None
    if 'ts' not in out:
        out['ts'] = None
    if 'type' not in out:
        out['type'] = 'note'
    if 'level' not in out:
        out['level'] = 'info'

    # Common linkage fields
    for k in ('projectId', 'runId', 'agentId'):
        if k not in out:
            out[k] = None

    # Display fields
    for k in ('title', 'message'):
        if k not in out:
            out[k] = None
    if 'data' not in out:
        out['data'] = None

    # Coerce types lightly (avoid raising)
    for k in ('id', 'ts', 'type', 'level', 'projectId', 'runId', 'agentId', 'title', 'message'):
        v = out.get(k)
        if v is None:
            continue
        if isinstance(v, (dict, list)):
            continue
        out[k] = str(v)

    # Keep data as-is if it's JSON-ish; otherwise stringify
    dv = out.get('data')
    if dv is not None and not isinstance(dv, (dict, list, str, int, float, bool)):
        out['data'] = str(dv)

    return out


def project_find_by_id(data: Dict, project_id: str) -> Optional[Dict]:
    for p in data.get('projects', []) or []:
        if isinstance(p, dict) and p.get('id') == project_id:
            return p
    return None


def project_get_tags(project: Dict) -> List[str]:
    tags = project.get('tags')
    if not isinstance(tags, list):
        return []
    out = []
    for t in tags:
        s = str(t).strip()
        if s and s not in out:
            out.append(s)
    return out


def project_set_tags(project: Dict, tags: List[str]):
    project['tags'] = tags


def build_action_event(action_id: str, *, project_id: str, run_id: Optional[str], agent_id: Optional[str],
                       typ: str, level: str, title: str, message: str, data: Dict) -> Dict:
    now = datetime.now().isoformat()
    return {
        'id': action_id,
        'ts': now,
        'type': typ,
        'level': level,
        'projectId': project_id,
        'runId': run_id,
        'agentId': agent_id,
        'title': title,
        'message': message,
        'data': data,
    }


@app.route('/api/agent/actions', methods=['POST'])
def agent_actions():
    """Semantic, agent-friendly actions.

    This endpoint exists so agents do not need to understand the full project schema.
    It also records a per-project execution trace via /api/agent/events.

    Body:
      {
        "agentId": "...",        // optional
        "runId": "...",          // optional
        "actions": [
          {
            "id": "act-...",     // optional but recommended for idempotency
            "projectId": "proj-...", // required unless top-level projectId is provided
            "type": "set_status" | "set_priority" | "set_progress" | "bump_progress" | "append_note" | "add_tag" | "remove_tag",
            "params": { ... },
            "ifUpdatedAt": "...", // optional optimistic concurrency
            "recordOnly": false     // optional
          }
        ]
      }
    """
    ok, err = require_agent()
    if not ok:
        return err

    try:
        body = request.get_json(silent=True) or {}
        agent_id = body.get('agentId')
        run_id = body.get('runId')
        default_project_id = body.get('projectId')
        actions = body.get('actions')
        if not isinstance(actions, list) or not actions:
            return jsonify({"success": False, "error": "actions must be a non-empty array"}), 400

        data = load_data()
        changed = False
        results = []

        for a in actions:
            try:
                if not isinstance(a, dict):
                    raise ValueError('action must be an object')

                action_id = str(a.get('id') or '').strip()
                if not action_id:
                    action_id = f"act-{str(uuid.uuid4())[:8]}"

                # Idempotency: if we already recorded this action id as an event, return it.
                existing = _agent_event_exists(action_id)
                if existing:
                    pid = existing.get('projectId') or (a.get('projectId') or default_project_id)
                    project = project_find_by_id(data, str(pid or '')) if pid else None
                    results.append({
                        "id": action_id,
                        "success": True,
                        "status": 200,
                        "projectId": pid,
                        "event": existing,
                        "project": project,
                        "message": "action exists",
                    })
                    continue

                project_id = a.get('projectId') or default_project_id
                if not project_id or not isinstance(project_id, str):
                    raise ValueError('projectId is required')

                project = project_find_by_id(data, project_id)
                if not project:
                    results.append({
                        "id": action_id,
                        "success": False,
                        "status": 404,
                        "projectId": project_id,
                        "error": f"项目未找到: {project_id}",
                    })
                    continue

                if_updated_at = a.get('ifUpdatedAt')
                if if_updated_at and str(project.get('updatedAt') or '') != str(if_updated_at):
                    results.append({
                        "id": action_id,
                        "success": False,
                        "status": 409,
                        "projectId": project_id,
                        "error": "Conflict: updatedAt mismatch",
                        "data": {
                            "expectedUpdatedAt": if_updated_at,
                            "actualUpdatedAt": project.get('updatedAt'),
                        }
                    })
                    continue

                action_type = str(a.get('type') or '').strip()
                params = a.get('params') if isinstance(a.get('params'), dict) else {}
                record_only = bool(a.get('recordOnly'))

                # Apply action
                before = {
                    "status": project.get('status'),
                    "priority": project.get('priority'),
                    "progress": project.get('progress'),
                    "tags": project_get_tags(project),
                }

                patch = {}
                event_level = 'info'
                event_message = ''

                if action_type == 'set_status':
                    status = str(params.get('status') or '').strip()
                    allowed = {"planning", "in-progress", "paused", "completed", "cancelled"}
                    if status not in allowed:
                        raise ValueError(f"invalid status: {status}")
                    if project.get('status') != status:
                        patch['status'] = status
                    event_message = f"set status -> {status}"

                elif action_type == 'set_priority':
                    pr = str(params.get('priority') or '').strip()
                    allowed = {"low", "medium", "high", "urgent"}
                    if pr not in allowed:
                        raise ValueError(f"invalid priority: {pr}")
                    if project.get('priority') != pr:
                        patch['priority'] = pr
                    event_message = f"set priority -> {pr}"

                elif action_type == 'set_progress':
                    v = params.get('progress')
                    nv = clamp_int(v, 0, 100)
                    if int(project.get('progress') or 0) != nv:
                        patch['progress'] = nv
                    event_message = f"set progress -> {nv}%"

                elif action_type == 'bump_progress':
                    delta = params.get('delta')
                    try:
                        d = int(delta)
                    except Exception:
                        raise ValueError('delta must be an integer')
                    cur = int(project.get('progress') or 0)
                    nv = clamp_int(cur + d, 0, 100)
                    if cur != nv:
                        patch['progress'] = nv
                    event_message = f"bump progress {d} -> {nv}%"

                elif action_type == 'append_note':
                    note = str(params.get('note') or '').strip()
                    if not note:
                        raise ValueError('note is required')
                    # Default behavior: record in event log only.
                    also_write = bool(params.get('alsoWriteToProjectNotes'))
                    if also_write:
                        cur_notes = str(project.get('notes') or '').rstrip()
                        prefix = datetime.now().strftime('%Y-%m-%d %H:%M')
                        who = str(agent_id or 'agent')
                        line = f"[{prefix}] ({who}) {note}"
                        patch['notes'] = (cur_notes + "\n" + line).lstrip() if cur_notes else line
                    event_message = note

                elif action_type == 'add_tag':
                    tag = str(params.get('tag') or '').strip()
                    if not tag:
                        raise ValueError('tag is required')
                    tags = project_get_tags(project)
                    if tag not in tags:
                        tags.append(tag)
                        patch['tags'] = tags
                    event_message = f"add tag: {tag}"

                elif action_type == 'remove_tag':
                    tag = str(params.get('tag') or '').strip()
                    if not tag:
                        raise ValueError('tag is required')
                    tags = project_get_tags(project)
                    if tag in tags:
                        tags = [t for t in tags if t != tag]
                        patch['tags'] = tags
                    event_message = f"remove tag: {tag}"

                else:
                    raise ValueError(f"unknown action type: {action_type}")

                after = {
                    "status": patch.get('status', project.get('status')),
                    "priority": patch.get('priority', project.get('priority')),
                    "progress": patch.get('progress', project.get('progress')),
                    "tags": patch.get('tags', project_get_tags(project)),
                }

                # Persist mutation
                if (not record_only) and patch:
                    for k, v in patch.items():
                        if k in ("id", "createdAt"):
                            continue
                        project[k] = v
                    project['updatedAt'] = datetime.now().isoformat()
                    changed = True

                # Always append event for traceability
                evt = build_action_event(
                    action_id,
                    project_id=project_id,
                    run_id=run_id,
                    agent_id=agent_id,
                    typ=f"action.{action_type}",
                    level=event_level,
                    title=action_type,
                    message=event_message,
                    data={
                        "action": {
                            "type": action_type,
                            "params": params,
                            "recordOnly": record_only,
                            "ifUpdatedAt": if_updated_at,
                        },
                        "before": before,
                        "after": after,
                        "projectUpdatedAt": project.get('updatedAt'),
                    }
                )
                append_agent_event(evt)

                results.append({
                    "id": action_id,
                    "success": True,
                    "status": 200,
                    "projectId": project_id,
                    "changed": bool((not record_only) and patch),
                    "project": project,
                    "event": evt,
                })

            except Exception as e:
                results.append({
                    "success": False,
                    "status": 400,
                    "error": str(e),
                    "action": a,
                })

        if changed:
            save_data(data)

        return jsonify({
            "success": True,
            "data": {
                "results": results,
                "changed": changed,
                "lastUpdated": data.get('lastUpdated'),
            }
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/agent/events', methods=['POST'])
def agent_create_event():
    ok, err = require_agent()
    if not ok:
        return err

    try:
        body = request.get_json(silent=True) or {}

        event_id = str(body.get('id') or '').strip()
        if event_id:
            existing = _agent_event_exists(event_id)
            if existing:
                return jsonify({"success": True, "data": existing, "message": "event exists"})
        else:
            event_id = f"evt-{str(uuid.uuid4())[:8]}"

        now = datetime.now().isoformat()
        event = {
            "id": event_id,
            "ts": now,
            "type": str(body.get('type') or 'note').strip(),
            "level": str(body.get('level') or 'info').strip(),
            "projectId": body.get('projectId'),
            "runId": body.get('runId'),
            "agentId": body.get('agentId'),
            "title": body.get('title'),
            "message": body.get('message'),
            "data": body.get('data'),
        }

        append_agent_event(event)
        return jsonify({"success": True, "data": event}), 201

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/agent/events', methods=['GET'])
def agent_list_events():
    ok, err = require_agent()
    if not ok:
        return err

    try:
        project_id = request.args.get('projectId')
        run_id = request.args.get('runId')
        agent_id = request.args.get('agentId')
        typ = request.args.get('type')
        since = request.args.get('since')
        limit = request.args.get('limit')
        tail = request.args.get('tail')

        since_dt = parse_iso(str(since or '').strip())
        lim = 200
        if limit:
            try:
                lim = max(1, min(2000, int(limit)))
            except Exception:
                lim = 200

        max_lines = 2000
        if tail:
            try:
                max_lines = max(100, min(20000, int(tail)))
            except Exception:
                max_lines = 2000

        lines = read_last_lines(AGENT_EVENTS_FILE, max_lines=max_lines)
        events: List[Dict] = []
        for line in lines:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            obj = normalize_agent_event(obj)
            if project_id and obj.get('projectId') != project_id:
                continue
            if run_id and obj.get('runId') != run_id:
                continue
            if agent_id and obj.get('agentId') != agent_id:
                continue
            if typ and obj.get('type') != typ:
                continue
            if since_dt:
                ts = parse_iso(str(obj.get('ts') or '').strip())
                if not ts or ts < since_dt:
                    continue
            events.append(obj)

        if len(events) > lim:
            events = events[-lim:]

        return jsonify({
            "success": True,
            "data": events,
            "total": len(events),
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/agent/runs', methods=['POST'])
def agent_create_run():
    ok, err = require_agent()
    if not ok:
        return err

    try:
        body = request.get_json(silent=True) or {}
        run_id = str(body.get('id') or '').strip()
        if not run_id:
            run_id = f"run-{str(uuid.uuid4())[:8]}"

        store = load_agent_runs()
        runs = store.get('runs', []) or []
        for r in runs:
            if isinstance(r, dict) and r.get('id') == run_id:
                return jsonify({"success": True, "data": r, "message": "run exists"})

        now = datetime.now().isoformat()
        run = {
            "id": run_id,
            "createdAt": now,
            "updatedAt": now,
            "startedAt": body.get('startedAt') or now,
            "finishedAt": body.get('finishedAt'),
            "status": body.get('status') or 'running',
            "projectId": body.get('projectId'),
            "agentId": body.get('agentId'),
            "title": body.get('title'),
            "summary": body.get('summary'),
            "links": body.get('links') if isinstance(body.get('links'), list) else [],
            "metrics": body.get('metrics') if isinstance(body.get('metrics'), dict) else {},
            "tags": body.get('tags') if isinstance(body.get('tags'), list) else [],
            "meta": body.get('meta') if isinstance(body.get('meta'), dict) else {},
        }

        runs.append(run)
        store['runs'] = runs
        save_agent_runs(store)
        return jsonify({"success": True, "data": run}), 201

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/agent/runs', methods=['GET'])
def agent_list_runs():
    ok, err = require_agent()
    if not ok:
        return err

    try:
        project_id = request.args.get('projectId')
        agent_id = request.args.get('agentId')
        status = request.args.get('status')
        limit = request.args.get('limit')
        offset = request.args.get('offset')

        lim = 50
        off = 0
        if limit:
            try:
                lim = max(1, min(500, int(limit)))
            except Exception:
                lim = 50
        if offset:
            try:
                off = max(0, int(offset))
            except Exception:
                off = 0

        store = load_agent_runs()
        runs = store.get('runs', []) or []
        out = []
        for r in runs:
            if not isinstance(r, dict):
                continue
            if project_id and r.get('projectId') != project_id:
                continue
            if agent_id and r.get('agentId') != agent_id:
                continue
            if status and r.get('status') != status:
                continue
            out.append(r)

        # Most recent first
        out.sort(key=lambda x: str(x.get('createdAt') or ''), reverse=True)
        page = out[off:off + lim]

        return jsonify({
            "success": True,
            "data": page,
            "total": len(out),
            "limit": lim,
            "offset": off,
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/agent/runs/<run_id>', methods=['GET'])
def agent_get_run(run_id: str):
    ok, err = require_agent()
    if not ok:
        return err

    store = load_agent_runs()
    runs = store.get('runs', []) or []
    for r in runs:
        if isinstance(r, dict) and r.get('id') == run_id:
            return jsonify({"success": True, "data": r})
    return jsonify({"success": False, "error": f"run not found: {run_id}"}), 404


@app.route('/api/agent/runs/<run_id>', methods=['PATCH'])
def agent_patch_run(run_id: str):
    ok, err = require_agent()
    if not ok:
        return err

    try:
        patch = request.get_json(silent=True) or {}
        store = load_agent_runs()
        runs = store.get('runs', []) or []

        run = None
        for r in runs:
            if isinstance(r, dict) and r.get('id') == run_id:
                run = r
                break
        if not run:
            return jsonify({"success": False, "error": f"run not found: {run_id}"}), 404

        protected = ['id', 'createdAt']
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
            run[k] = v

        run['updatedAt'] = datetime.now().isoformat()
        save_agent_runs(store)
        return jsonify({"success": True, "data": run})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# === 运维接口（危险操作：需要 PM_ADMIN_TOKEN） ===

@app.route('/api/admin/push', methods=['POST'])
def admin_push_to_github():
    ok, err = require_admin()
    if not ok:
        return err

    if os.name != 'posix':
        return jsonify({
            "success": False,
            "error": "This endpoint requires Linux (bash)."
        }), 400

    # Flask 3.x: accessing request.json may raise 415 if Content-Type is not JSON.
    # This endpoint treats body as optional; be tolerant.
    body = request.get_json(silent=True) or {}
    mode = str(body.get('mode') or 'data-only').strip()
    if mode not in ('data-only', 'all'):
        return jsonify({
            "success": False,
            "error": "mode must be 'data-only' or 'all'"
        }), 400

    script = os.path.join(ROOT_DIR, 'push_data_to_github.sh')
    if not os.path.exists(script):
        return jsonify({
            "success": False,
            "error": "push_data_to_github.sh not found"
        }), 500

    cmd = ['bash', script]
    if mode == 'all':
        cmd.append('--all')

    try:
        # Ensure git can find config and SSH keys when run from systemd
        env = os.environ.copy()
        env.setdefault('HOME', os.path.expanduser('~'))
        env.setdefault('USER', os.getenv('USER', 'root'))
        
        p = subprocess.run(
            cmd,
            cwd=ROOT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
            check=False,
            env=env,
        )
        
        output = (p.stdout or '').strip()
        
        if p.returncode != 0:
            # Extract meaningful error from output
            lines = output.split('\n')
            error_lines = [line for line in lines if '[ERROR]' in line or 'fatal:' in line or 'error:' in line]
            error_summary = error_lines[-1] if error_lines else f"push failed (exit {p.returncode})"
            
            return jsonify({
                "success": False,
                "error": error_summary,
                "output": output,
                "exitCode": p.returncode
            }), 500

        return jsonify({
            "success": True,
            "output": output
        })

    except subprocess.TimeoutExpired as e:
        output = (e.stdout or '').strip() if hasattr(e, 'stdout') else ''
        return jsonify({
            "success": False,
            "error": "push timed out (exceeded 180 seconds)",
            "output": output
        }), 504


@app.route('/api/admin/data/pull', methods=['POST'])
def admin_pull_data_repo():
    ok, err = require_admin()
    if not ok:
        return err

    if os.name != 'posix':
        return jsonify({
            "success": False,
            "error": "This endpoint requires Linux (bash)."
        }), 400

    script = os.path.join(ROOT_DIR, 'pull_data_repo.sh')
    if not os.path.exists(script):
        return jsonify({
            "success": False,
            "error": "pull_data_repo.sh not found"
        }), 500

    try:
        # Ensure git can find config and SSH keys when run from systemd
        env = os.environ.copy()
        env.setdefault('HOME', os.path.expanduser('~'))
        env.setdefault('USER', os.getenv('USER', 'root'))
        
        p = subprocess.run(
            ['bash', script],
            cwd=ROOT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
            check=False,
            env=env,
        )
        
        output = (p.stdout or '').strip()
        
        if p.returncode != 0:
            # 2: dirty worktree, 4/5/6: misconfig
            http = 409 if p.returncode == 2 else 500
            
            # Extract meaningful error from output
            lines = output.split('\n')
            error_lines = [line for line in lines if '[ERROR]' in line or 'fatal:' in line or 'error:' in line]
            error_summary = error_lines[-1] if error_lines else f"pull data repo failed (exit {p.returncode})"
            
            return jsonify({
                "success": False,
                "error": error_summary,
                "output": output,
                "exitCode": p.returncode
            }), http

        return jsonify({
            "success": True,
            "output": output
        })

    except subprocess.TimeoutExpired as e:
        output = (e.stdout or '').strip() if hasattr(e, 'stdout') else ''
        return jsonify({
            "success": False,
            "error": "pull data repo timed out (exceeded 180 seconds)",
            "output": output
        }), 504


@app.route('/api/admin/merge-data-sync', methods=['POST'])
def admin_merge_data_sync_to_main():
    ok, err = require_admin()
    if not ok:
        return err

    # Data is stored in a separate repository under ./data.
    # The legacy workflow (data-sync -> merge into main) no longer applies.
    return jsonify({
        "success": False,
        "error": "Deprecated: data repo is separated (./data). 'merge-data-sync' no longer applies.",
    }), 410



@app.route('/api/admin/deploy', methods=['POST'])
def admin_deploy_pull_restart():
    ok, err = require_admin()
    if not ok:
        return err

    if os.name != 'posix':
        return jsonify({
            "success": False,
            "error": "This endpoint requires Linux (bash + systemctl/nohup)."
        }), 400

    script = os.path.join(ROOT_DIR, 'deploy_pull_restart.sh')
    if not os.path.exists(script):
        return jsonify({
            "success": False,
            "error": "deploy_pull_restart.sh not found"
        }), 500

    try:
        job_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
        unit = f"{DEPLOY_UNIT_PREFIX}{job_id}"

        lf = open(DEPLOY_LOG_FILE, 'a', encoding='utf-8', errors='replace')
        lf.write("\n" + "=" * 60 + "\n")
        lf.write(f"[INFO] Deploy triggered at {datetime.now().isoformat()}\n")
        lf.write(f"[INFO] JobId: {job_id}\n")
        lf.flush()

        # If this Flask app runs under systemd, restarting the service will kill processes
        # in the same cgroup. To make deploy survive restart, prefer running the deploy
        # script in a transient systemd unit.
        method = 'popen'
        pid = None
        started = False
        start_error = None

        if shutil.which('systemd-run') and shutil.which('systemctl'):
            method = 'systemd-run'
            cmd_str = (
                f"cd {shlex.quote(ROOT_DIR)} && "
                f"bash {shlex.quote(script)} >> {shlex.quote(DEPLOY_LOG_FILE)} 2>&1; "
                f"rc=$?; "
                f"echo \"[INFO] Deploy finished jobId={job_id} (exit=$rc)\" >> {shlex.quote(DEPLOY_LOG_FILE)}; "
                f"exit $rc"
            )
            # Start async (no --wait). Output from systemd-run itself is not critical.
            r = subprocess.run(
                ['systemd-run', f'--unit={unit}', '--collect', '/bin/bash', '-lc', cmd_str],
                cwd=ROOT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=5,
                check=False,
            )
            if r.returncode == 0:
                started = True
                lf.write(f"[INFO] Started via systemd-run: unit={unit}\n")
                lf.flush()
            else:
                start_error = (r.stdout or '').strip()
                lf.write(f"[WARN] systemd-run failed; falling back to background Popen.\n")
                if start_error:
                    lf.write(f"[WARN] systemd-run output: {start_error}\n")
                lf.flush()
                method = 'popen'

        if not started:
            proc = subprocess.Popen(
                ['bash', script],
                cwd=ROOT_DIR,
                stdout=lf,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            pid = proc.pid
            started = True
            lf.write(f"[INFO] Started via Popen: pid={pid}\n")
            lf.flush()

        deploy_state_write({
            'jobId': job_id,
            'unit': unit if method == 'systemd-run' else None,
            'pid': pid,
            'method': method,
            'state': 'running',
            'startedAt': datetime.now().isoformat(),
            'startError': start_error,
        })

        lf.close()

        return jsonify({
            "success": True,
            "jobId": job_id,
            "unit": unit if method == 'systemd-run' else None,
            "pid": pid,
            "method": method,
            "logFile": "deploy_run.log",
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/admin/deploy/log', methods=['GET'])
def admin_deploy_log():
    ok, err = require_admin()
    if not ok:
        return err

    lines = read_last_lines(DEPLOY_LOG_FILE, max_lines=240)
    return jsonify({
        "success": True,
        "lines": lines
    })


@app.route('/api/admin/deploy/status', methods=['GET'])
def admin_deploy_status():
    ok, err = require_admin()
    if not ok:
        return err

    st = deploy_state_read()
    job_id = st.get('jobId') or ''
    unit = st.get('unit') or ''
    pid = st.get('pid')
    method = st.get('method') or ''

    state = 'unknown'
    exit_code = None
    msg = ''

    # If log already records finish marker, that's authoritative.
    done_rc = parse_deploy_finish_from_log(job_id)
    if done_rc is not None:
        exit_code = done_rc
        state = 'success' if done_rc == 0 else 'failed'
        msg = f"finished jobId={job_id}"
        deploy_state_write({'state': state, 'exitCode': exit_code})
        return jsonify({
            'success': True,
            'data': {
                'state': state,
                'method': method,
                'unit': unit or None,
                'pid': pid,
                'exitCode': exit_code,
                'message': msg,
                'startedAt': st.get('startedAt'),
                'updatedAt': datetime.now().isoformat(),
            }
        })

    if method == 'systemd-run' and unit:
        props = systemctl_show(unit, [
            'ActiveState', 'SubState', 'Result', 'ExecMainStatus', 'ExecMainCode',
            'StateChangeTimestamp', 'ExecMainExitTimestamp'
        ])
        active = props.get('ActiveState', '')
        sub = props.get('SubState', '')
        result = props.get('Result', '')
        exec_status = props.get('ExecMainStatus', '')

        try:
            if exec_status != '':
                exit_code = int(exec_status)
        except Exception:
            exit_code = None

        if active in ('activating', 'active') and sub in ('running', 'start'):
            state = 'running'
        elif exit_code is not None:
            state = 'success' if exit_code == 0 else 'failed'
        elif active == 'failed' or result in ('failed', 'exit-code', 'timeout', 'signal', 'core-dump'):
            state = 'failed'
        else:
            state = 'unknown'

        msg = f"unit={unit} active={active} sub={sub} result={result}"
        deploy_state_write({'state': state, 'exitCode': exit_code, 'unitState': props})

    elif method == 'popen' and pid:
        # Best-effort: check if the pid is still alive.
        try:
            os.kill(int(pid), 0)
            state = 'running'
        except Exception:
            # If the process disappeared, we don't know if it succeeded; rely on logs.
            state = st.get('state') or 'unknown'
        msg = f"pid={pid}"

    return jsonify({
        'success': True,
        'data': {
            'state': state,
            'method': method,
            'unit': unit or None,
            'pid': pid,
            'exitCode': exit_code,
            'message': msg,
            'startedAt': st.get('startedAt'),
            'updatedAt': datetime.now().isoformat(),
        }
    })

# === 错误处理 ===

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "资源未找到"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "服务器内部错误"
    }), 500

# === 启动服务 ===

if __name__ == '__main__':
    print("=" * 60)
    print("项目管理系统 API 服务")
    print("=" * 60)
    print(f"数据文件: {DATA_FILE}")
    port = int(os.environ.get('PM_PORT', '8689'))
    print(f"API地址: http://localhost:{port}/api")
    print(f"Web界面: http://localhost:{port}")
    print("=" * 60)
    
    # 确保数据目录存在
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    
    # 启动服务
    debug = os.environ.get('PM_DEBUG', '').strip() == '1'
    app.run(host='0.0.0.0', port=port, debug=debug)
