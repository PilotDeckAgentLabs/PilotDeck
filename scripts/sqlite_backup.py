#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a consistent single-file SQLite backup.

Motivation:
- In WAL mode, copying only the main *.db file is NOT a safe backup.
- Use SQLite online backup API to write a consistent snapshot into a single file.

This script is designed to be called from ops scripts (e.g. backup_db_snapshot.sh).
"""

from __future__ import annotations

import argparse
import os
import sqlite3


def _open(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON;')
    conn.execute('PRAGMA busy_timeout=5000;')
    return conn


def backup(db_path: str, out_path: str, *, checkpoint: bool, truncate_wal: bool) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    src = _open(db_path)
    try:
        if checkpoint:
            try:
                src.execute('PRAGMA wal_checkpoint(FULL);').fetchall()
            except Exception:
                pass

        # Ensure output path doesn't keep stale file content.
        if os.path.exists(out_path):
            os.remove(out_path)

        dst = _open(out_path)
        try:
            src.backup(dst)
        finally:
            dst.close()

        if truncate_wal:
            try:
                src.execute('PRAGMA wal_checkpoint(TRUNCATE);').fetchall()
            except Exception:
                pass
    finally:
        src.close()


def main() -> None:
    p = argparse.ArgumentParser(description='Create a consistent SQLite backup file')
    p.add_argument('--db', required=True, help='Source SQLite DB path (e.g. data/pm.db)')
    p.add_argument('--out', required=True, help='Output backup path (e.g. data/pm_backup.db)')
    p.add_argument('--no-checkpoint', action='store_true', help='Skip WAL checkpoint before backup')
    p.add_argument('--no-truncate-wal', action='store_true', help='Do not attempt WAL truncation after backup')
    args = p.parse_args()

    backup(
        args.db,
        args.out,
        checkpoint=not args.no_checkpoint,
        truncate_wal=not args.no_truncate_wal,
    )


if __name__ == '__main__':
    main()
