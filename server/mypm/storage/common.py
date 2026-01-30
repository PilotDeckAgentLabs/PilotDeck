# -*- coding: utf-8 -*-
import json
import os
from collections import deque
from typing import Dict, List, Optional


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
