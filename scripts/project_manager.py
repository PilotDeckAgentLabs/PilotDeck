#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Project management CLI.

Default backend: SQLite (data/pm.db)
Legacy backend: JSON (data/projects.json) is supported via one-time import into SQLite.
"""

import json
import os
import sys
from typing import Dict, Optional


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT_DIR, 'server'))

from mypm.storage import ProjectsStore  # noqa: E402
from mypm.domain.errors import ProjectNotFoundError  # noqa: E402

class ProjectManager:
    def __init__(self, db_file: str = "data/pm.db", legacy_json: str = "data/projects.json"):
        self.db_file = db_file
        self.store = ProjectsStore(db_file, legacy_projects_json=legacy_json)
    
    def list_projects(self, status: Optional[str] = None, priority: Optional[str] = None):
        """列出项目"""
        projects, _meta = self.store.list(status=status, priority=priority)
        
        if not projects:
            print("未找到项目")
            return
        
        print(f"\n{'ID':<12} {'名称':<30} {'状态':<12} {'优先级':<10} {'进度':<6}")
        print("-" * 80)
        for p in projects:
            print(f"{p['id']:<12} {p['name']:<30} {p['status']:<12} {p['priority']:<10} {p.get('progress', 0):>5}%")
    
    def get_project(self, project_id: str) -> Optional[Dict]:
        """获取单个项目详情"""
        return self.store.get(project_id)
    
    def add_project(self, project_data: Dict):
        """添加新项目"""
        project = self.store.create(project_data or {})
        print(f"项目已添加: {project['id']} - {project.get('name')}")
    
    def update_project(self, project_id: str, updates: Dict):
        """更新项目"""
        try:
            self.store.patch(project_id, updates or {}, if_updated_at=None)
            print(f"项目已更新: {project_id}")
            return True
        except KeyError:
            print(f"未找到项目: {project_id}")
            return False
    
    def delete_project(self, project_id: str):
        """删除项目"""
        try:
            self.store.delete(project_id)
            print(f"项目已删除: {project_id}")
            return True
        except KeyError:
            print(f"未找到项目: {project_id}")
            return False
    
    def update_progress(self, project_id: str, progress: int):
        """更新项目进度"""
        if not (0 <= progress <= 100):
            print("进度必须在0-100之间")
            return False
        return self.update_project(project_id, {"progress": progress})
    
    def update_status(self, project_id: str, status: str):
        """更新项目状态"""
        valid_statuses = ["planning", "in-progress", "paused", "completed", "cancelled"]
        if status not in valid_statuses:
            print(f"无效的状态。有效值: {', '.join(valid_statuses)}")
            return False
        return self.update_project(project_id, {"status": status})
    
    def get_statistics(self):
        """获取统计信息"""
        stats = self.store.get_statistics()
        total = stats.get('total', 0)
        by_status = stats.get('byStatus', {})
        by_priority = stats.get('byPriority', {})
        fin = stats.get('financial', {})

        print(f"\n=== 项目统计 ===")
        print(f"总项目数: {total}")
        print(f"\n按状态:")
        for st, count in by_status.items():
            print(f"  {st}: {count}")
        print(f"\n按优先级:")
        for pr, count in by_priority.items():
            print(f"  {pr}: {count}")
        print(f"\n财务概况:")
        print(f"  总预算: ¥{float(fin.get('totalBudget') or 0):,.2f}")
        print(f"  总成本: ¥{float(fin.get('totalCost') or 0):,.2f}")
        print(f"  总收入: ¥{float(fin.get('totalRevenue') or 0):,.2f}")
        print(f"  净收益: ¥{float(fin.get('netProfit') or 0):,.2f}")


def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="项目管理系统CLI")
    parser.add_argument("--db-file", default="data/pm.db", help="SQLite 数据库路径")
    parser.add_argument("--legacy-json", default="data/projects.json", help="Legacy JSON (optional import source)")
    
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # list命令
    list_parser = subparsers.add_parser("list", help="列出项目")
    list_parser.add_argument("--status", help="按状态筛选")
    list_parser.add_argument("--priority", help="按优先级筛选")
    
    # get命令
    get_parser = subparsers.add_parser("get", help="获取项目详情")
    get_parser.add_argument("id", help="项目ID")
    
    # add命令
    add_parser = subparsers.add_parser("add", help="添加项目")
    add_parser.add_argument("--name", required=True, help="项目名称")
    add_parser.add_argument("--description", default="", help="项目描述")
    add_parser.add_argument("--status", default="planning", help="项目状态")
    add_parser.add_argument("--priority", default="medium", help="优先级")
    add_parser.add_argument("--category", default="", help="项目分类")
    
    # update命令
    update_parser = subparsers.add_parser("update", help="更新项目")
    update_parser.add_argument("id", help="项目ID")
    update_parser.add_argument("--name", help="项目名称")
    update_parser.add_argument("--status", help="项目状态")
    update_parser.add_argument("--priority", help="优先级")
    update_parser.add_argument("--progress", type=int, help="进度(0-100)")
    
    # delete命令
    delete_parser = subparsers.add_parser("delete", help="删除项目")
    delete_parser.add_argument("id", help="项目ID")
    
    # stats命令
    stats_parser = subparsers.add_parser("stats", help="显示统计信息")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    pm = ProjectManager(args.db_file, legacy_json=args.legacy_json)
    
    if args.command == "list":
        pm.list_projects(status=args.status, priority=args.priority)
    
    elif args.command == "get":
        project = pm.get_project(args.id)
        if project:
            print(json.dumps(project, ensure_ascii=False, indent=2))
        else:
            print(f"未找到项目: {args.id}")
    
    elif args.command == "add":
        project_data = {
            "name": args.name,
            "description": args.description,
            "status": args.status,
            "priority": args.priority,
            "category": args.category
        }
        pm.add_project(project_data)
    
    elif args.command == "update":
        updates = {}
        if args.name:
            updates["name"] = args.name
        if args.status:
            updates["status"] = args.status
        if args.priority:
            updates["priority"] = args.priority
        if args.progress is not None:
            updates["progress"] = args.progress
        
        if updates:
            pm.update_project(args.id, updates)
        else:
            print("没有指定要更新的字段")
    
    elif args.command == "delete":
        pm.delete_project(args.id)
    
    elif args.command == "stats":
        pm.get_statistics()


if __name__ == "__main__":
    main()
