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
    """加载项目数据"""
    if not os.path.exists(DATA_FILE):
        return {
            "version": "1.0.0",
            "lastUpdated": datetime.now().isoformat(),
            "projects": []
        }
    
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data: Dict):
    """保存项目数据"""
    data["lastUpdated"] = datetime.now().isoformat()
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
        p = subprocess.run(
            cmd,
            cwd=ROOT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
            check=False,
        )
        if p.returncode != 0:
            return jsonify({
                "success": False,
                "error": f"push failed (exit {p.returncode})",
                "output": p.stdout
            }), 500

        return jsonify({
            "success": True,
            "output": p.stdout
        })

    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "error": "push timed out",
        }), 504


@app.route('/api/admin/merge-data-sync', methods=['POST'])
def admin_merge_data_sync_to_main():
    ok, err = require_admin()
    if not ok:
        return err

    if os.name != 'posix':
        return jsonify({
            "success": False,
            "error": "This endpoint requires Linux (bash + git)."
        }), 400

    script = os.path.join(ROOT_DIR, 'merge_data_sync_to_main.sh')
    if not os.path.exists(script):
        return jsonify({
            "success": False,
            "error": "merge_data_sync_to_main.sh not found"
        }), 500

    try:
        p = subprocess.run(
            ['bash', script],
            cwd=ROOT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
            check=False,
        )

        if p.returncode == 0:
            return jsonify({
                "success": True,
                "output": p.stdout
            })

        # 2: dirty worktree, 3: conflict, 4: missing data branch
        if p.returncode in (2, 3, 4):
            return jsonify({
                "success": False,
                "error": f"merge refused (exit {p.returncode})",
                "output": p.stdout
            }), 409

        return jsonify({
            "success": False,
            "error": f"merge failed (exit {p.returncode})",
            "output": p.stdout
        }), 500

    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "error": "merge timed out",
        }), 504


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
