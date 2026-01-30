# -*- coding: utf-8 -*-
"""File locking utilities for cross-process safety.

NOTE: Current implementation uses atomic tmp+replace without explicit locks.
This module provides a placeholder for future filelock integration if needed.
"""

import contextlib
from typing import Generator


@contextlib.contextmanager
def file_lock(file_path: str) -> Generator[None, None, None]:
    """Context manager for file locking (placeholder).
    
    Current implementation: no-op (atomic writes via tmp+replace are sufficient).
    Future: integrate `filelock` library for multi-process write coordination.
    
    Usage:
        with file_lock(path):
            # Critical section
            pass
    """
    # Placeholder: no locking yet
    # Future: from filelock import FileLock; lock = FileLock(f"{file_path}.lock")
    yield
