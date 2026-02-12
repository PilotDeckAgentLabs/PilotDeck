#!/usr/bin/env python3
"""
Initialize Agent Coding Scaffold in a target project.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import cast


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize agent coding scaffold")
    _ = parser.add_argument("--target", required=True, help="Target project root")
    _ = parser.add_argument("--project-id", required=True, help="Project identifier")
    _ = parser.add_argument("--project-name", required=True, help="Project display name")
    _ = parser.add_argument("--repo", required=True, help="Repository URL or slug")
    _ = parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing scaffold files",
    )
    return parser.parse_args()


def replace_tokens(text: str, project_id: str, project_name: str, repo: str) -> str:
    return (
        text.replace("proj-template", project_id)
        .replace("Template Project", project_name)
        .replace("github.com/org/repo", repo)
    )


def copy_template_file(src: Path, dst: Path, project_id: str, project_name: str, repo: str, force: bool) -> None:
    if dst.exists() and not force:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    content = src.read_text(encoding="utf-8")
    content = replace_tokens(content, project_id, project_name, repo)
    _ = dst.write_text(content, encoding="utf-8")


def init_scaffold(target_root: Path, project_id: str, project_name: str, repo: str, force: bool) -> None:
    script_dir = Path(__file__).resolve().parent
    scaffold_root = script_dir.parent / "scaffold" / "templates"

    if not scaffold_root.exists():
        raise FileNotFoundError(f"Template root not found: {scaffold_root}")

    # Copy .agent templates
    agent_src = scaffold_root / ".agent"
    agent_dst = target_root / ".agent"
    for src in agent_src.rglob("*"):
        if src.is_file():
            rel = src.relative_to(agent_src)
            copy_template_file(src, agent_dst / rel, project_id, project_name, repo, force)

    # Copy status template
    status_src = scaffold_root / "status.yaml"
    status_dst = target_root / "status.yaml"
    copy_template_file(status_src, status_dst, project_id, project_name, repo, force)

    # Copy schemas and workflows for local reference
    support_src = script_dir.parent / "scaffold"
    support_dst = target_root / ".agent-scaffold"
    if support_dst.exists() and force:
        shutil.rmtree(support_dst)
    if not support_dst.exists():
        _ = shutil.copytree(support_src, support_dst)


def main() -> None:
    args = parse_args()
    target = Path(cast(str, args.target)).resolve()
    target.mkdir(parents=True, exist_ok=True)

    init_scaffold(
        target_root=target,
        project_id=cast(str, args.project_id),
        project_name=cast(str, args.project_name),
        repo=cast(str, args.repo),
        force=cast(bool, args.force),
    )

    print("Scaffold initialized successfully.")
    print(f"Target: {target}")
    print("Read next: .agent/HANDOFF.md -> .agent/PLAN.yaml -> .agent/ARCHITECTURE.md")


if __name__ == "__main__":
    main()
