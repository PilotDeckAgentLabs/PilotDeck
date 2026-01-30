# -*- coding: utf-8 -*-
"""Deploy and ops-related utilities."""

import os
import shutil
import subprocess
import shlex
from typing import Dict, List, Optional
from datetime import datetime
import uuid

from ..storage.atomic import write_json_atomic


class DeployService:
    """Handles deployment state and systemctl utilities."""
    
    def __init__(self, root_dir: str, state_file: str, log_file: str, unit_prefix: str):
        self.root_dir = root_dir
        self.state_file = state_file
        self.log_file = log_file
        self.unit_prefix = unit_prefix
    
    def read_state(self) -> Dict:
        """Read deploy state from JSON file."""
        if not os.path.exists(self.state_file):
            return {}
        try:
            import json
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def write_state(self, patch: Dict):
        """Update deploy state (merge patch)."""
        cur = self.read_state()
        cur.update(patch)
        cur['updatedAt'] = datetime.now().isoformat()
        write_json_atomic(self.state_file, cur)
    
    def systemctl_show(self, unit: str, props: List[str]) -> Dict[str, str]:
        """Query systemctl show for given unit and properties.
        
        Returns:
            Dict of property=value pairs
        """
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
    
    def parse_deploy_finish_from_log(self, job_id: str) -> Optional[int]:
        """Parse exit code from deploy log for given job ID.
        
        Returns:
            Exit code if found, None otherwise
        """
        if not job_id:
            return None
        
        lines = self._read_last_lines(self.log_file, max_lines=800)
        
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
    
    def _read_last_lines(self, file_path: str, max_lines: int = 200) -> List[str]:
        """Read last N lines from file."""
        from collections import deque
        try:
            dq = deque(maxlen=max_lines)
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    dq.append(line.rstrip('\n'))
            return list(dq)
        except FileNotFoundError:
            return []
    
    def start_deploy_job(self, script_path: str) -> Dict:
        """Start deployment script as background job.
        
        Returns:
            Dict with jobId, unit/pid, method
        """
        job_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
        unit = f"{self.unit_prefix}{job_id}"
        
        # Write job header to log
        with open(self.log_file, 'a', encoding='utf-8', errors='replace') as lf:
            lf.write("\n" + "=" * 60 + "\n")
            lf.write(f"[INFO] Deploy triggered at {datetime.now().isoformat()}\n")
            lf.write(f"[INFO] JobId: {job_id}\n")
            lf.flush()
        
        method = 'popen'
        pid = None
        started = False
        start_error = None
        
        # Try systemd-run first (survives service restart)
        if shutil.which('systemd-run') and shutil.which('systemctl'):
            method = 'systemd-run'
            cmd_str = (
                f"cd {shlex.quote(self.root_dir)} && "
                f"bash {shlex.quote(script_path)} >> {shlex.quote(self.log_file)} 2>&1; "
                f"rc=$?; "
                f"echo \"[INFO] Deploy finished jobId={job_id} (exit=$rc)\" >> {shlex.quote(self.log_file)}; "
                f"exit $rc"
            )
            
            r = subprocess.run(
                ['systemd-run', f'--unit={unit}', '--collect', '/bin/bash', '-lc', cmd_str],
                cwd=self.root_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=5,
                check=False,
            )
            
            if r.returncode == 0:
                started = True
                with open(self.log_file, 'a', encoding='utf-8') as lf:
                    lf.write(f"[INFO] Started via systemd-run: unit={unit}\n")
            else:
                start_error = (r.stdout or '').strip()
                with open(self.log_file, 'a', encoding='utf-8') as lf:
                    lf.write(f"[WARN] systemd-run failed; falling back to Popen.\n")
                    if start_error:
                        lf.write(f"[WARN] systemd-run output: {start_error}\n")
                method = 'popen'
        
        # Fallback to Popen
        if not started:
            with open(self.log_file, 'a', encoding='utf-8') as lf:
                proc = subprocess.Popen(
                    ['bash', script_path],
                    cwd=self.root_dir,
                    stdout=lf,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                pid = proc.pid
                started = True
                lf.write(f"[INFO] Started via Popen: pid={pid}\n")
        
        # Save state
        self.write_state({
            'jobId': job_id,
            'unit': unit if method == 'systemd-run' else None,
            'pid': pid,
            'method': method,
            'state': 'running',
            'startedAt': datetime.now().isoformat(),
            'startError': start_error,
        })
        
        return {
            "jobId": job_id,
            "unit": unit if method == 'systemd-run' else None,
            "pid": pid,
            "method": method,
        }
    
    def get_deploy_status(self) -> Dict:
        """Get current deploy job status.
        
        Returns:
            Dict with state, exitCode, method, unit/pid, message
        """
        st = self.read_state()
        job_id = st.get('jobId') or ''
        unit = st.get('unit') or ''
        pid = st.get('pid')
        method = st.get('method') or ''
        
        state = 'unknown'
        exit_code = None
        msg = ''
        
        # Check log for finish marker (authoritative)
        done_rc = self.parse_deploy_finish_from_log(job_id)
        if done_rc is not None:
            exit_code = done_rc
            state = 'success' if done_rc == 0 else 'failed'
            msg = f"finished jobId={job_id}"
            self.write_state({'state': state, 'exitCode': exit_code})
            return {
                'state': state,
                'method': method,
                'unit': unit or None,
                'pid': pid,
                'exitCode': exit_code,
                'message': msg,
                'startedAt': st.get('startedAt'),
                'updatedAt': datetime.now().isoformat(),
            }
        
        # Check systemd unit status
        if method == 'systemd-run' and unit:
            props = self.systemctl_show(unit, [
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
            self.write_state({'state': state, 'exitCode': exit_code, 'unitState': props})
        
        # Check Popen pid status
        elif method == 'popen' and pid:
            try:
                os.kill(int(pid), 0)
                state = 'running'
            except Exception:
                state = st.get('state') or 'unknown'
            msg = f"pid={pid}"
        
        return {
            'state': state,
            'method': method,
            'unit': unit or None,
            'pid': pid,
            'exitCode': exit_code,
            'message': msg,
            'startedAt': st.get('startedAt'),
            'updatedAt': datetime.now().isoformat(),
        }
