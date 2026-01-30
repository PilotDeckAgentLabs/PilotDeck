# -*- coding: utf-8 -*-
"""Atomic file write utilities."""

import os
import json
from typing import Dict, Any


def write_json_atomic(file_path: str, data: Dict[str, Any], **json_kwargs):
    """Write JSON data to file atomically using tmp+replace pattern.
    
    Args:
        file_path: Target file path
        data: Dict to serialize as JSON
        **json_kwargs: Additional arguments for json.dump (e.g., indent=2)
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Write to temporary file first
    tmp = f"{file_path}.tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        # Default: ensure_ascii=False for Unicode, indent=2 for readability
        kwargs = {'ensure_ascii': False, 'indent': 2}
        kwargs.update(json_kwargs)
        json.dump(data, f, **kwargs)
    
    # Atomic replace (rename is atomic on POSIX and Windows)
    os.replace(tmp, file_path)
