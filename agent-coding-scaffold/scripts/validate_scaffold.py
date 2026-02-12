#!/usr/bin/env python3
"""
Validate required scaffold artifacts exist in a target project.
"""

from __future__ import annotations

import argparse
from typing import cast
from pathlib import Path


REQUIRED_FILES = [
    ".agent/PROJECT.md",
    ".agent/ARCHITECTURE.md",
    ".agent/PLAN.yaml",
    ".agent/STATE.yaml",
    ".agent/MEMORY_INDEX.md",
    ".agent/DECISIONS.md",
    ".agent/HANDOFF.md",
    "status.yaml",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate scaffold files")
    _ = parser.add_argument("--target", required=True, help="Target project root")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target = cast(str, args.target)
    root = Path(target).resolve()

    missing: list[str] = []
    for rel in REQUIRED_FILES:
        path = root / rel
        if not path.exists():
            missing.append(rel)

    if missing:
        print("Scaffold validation failed. Missing files:")
        for rel in missing:
            print(f"- {rel}")
        raise SystemExit(1)

    print("Scaffold validation passed.")


if __name__ == "__main__":
    main()
