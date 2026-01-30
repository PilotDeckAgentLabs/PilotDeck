#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目管理数据操作脚本
提供命令行接口来管理projects.json数据
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
import uuid

class ProjectManager:
    def __init__(self, data_file: str = "data/projects.json"):
        self.data_file = data_file
        self.data = self._load_data()
    
    def _load_data(self) -> Dict:
        """加载项目数据"""
        if not os.path.exists(self.data_file):
            return {
                "version": "1.0.0",
                "lastUpdated": datetime.now().isoformat(),
                "projects": []
            }
        
        with open(self.data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_data(self):
        """保存项目数据"""
        self.data["lastUpdated"] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def list_projects(self, status: Optional[str] = None, priority: Optional[str] = None):
        """列出项目"""
        projects = self.data["projects"]
        
        if status:
            projects = [p for p in projects if p.get("status") == status]
        if priority:
            projects = [p for p in projects if p.get("priority") == priority]
        
        if not projects:
            print("未找到项目")
            return
        
        print(f"\n{'ID':<12} {'名称':<30} {'状态':<12} {'优先级':<10} {'进度':<6}")
        print("-" * 80)
        for p in projects:
            print(f"{p['id']:<12} {p['name']:<30} {p['status']:<12} {p['priority']:<10} {p.get('progress', 0):>5}%")
    
    def get_project(self, project_id: str) -> Optional[Dict]:
        """获取单个项目详情"""
        for project in self.data["projects"]:
            if project["id"] == project_id:
                return project
        return None
    
    def add_project(self, project_data: Dict):
        """添加新项目"""
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
        project_data.setdefault("tags", [])
        
        self.data["projects"].append(project_data)
        self._save_data()
        print(f"项目已添加: {project_data['id']} - {project_data['name']}")
    
    def update_project(self, project_id: str, updates: Dict):
        """更新项目"""
        project = self.get_project(project_id)
        if not project:
            print(f"未找到项目: {project_id}")
            return False
        
        # 更新字段
        for key, value in updates.items():
            project[key] = value
        
        project["updatedAt"] = datetime.now().isoformat()
        self._save_data()
        print(f"项目已更新: {project_id}")
        return True
    
    def delete_project(self, project_id: str):
        """删除项目"""
        projects = self.data["projects"]
        for i, project in enumerate(projects):
            if project["id"] == project_id:
                del projects[i]
                self._save_data()
                print(f"项目已删除: {project_id}")
                return True
        
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
        projects = self.data["projects"]
        total = len(projects)
        
        by_status = {}
        by_priority = {}
        total_budget = 0
        total_cost = 0
        total_revenue = 0
        
        for p in projects:
            # 状态统计
            status = p.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1
            
            # 优先级统计
            priority = p.get("priority", "unknown")
            by_priority[priority] = by_priority.get(priority, 0) + 1
            
            # 财务统计
            if "budget" in p and "planned" in p["budget"]:
                total_budget += p["budget"]["planned"]
            if "cost" in p and "total" in p["cost"]:
                total_cost += p["cost"]["total"]
            if "revenue" in p and "total" in p["revenue"]:
                total_revenue += p["revenue"]["total"]
        
        print(f"\n=== 项目统计 ===")
        print(f"总项目数: {total}")
        print(f"\n按状态:")
        for status, count in by_status.items():
            print(f"  {status}: {count}")
        print(f"\n按优先级:")
        for priority, count in by_priority.items():
            print(f"  {priority}: {count}")
        print(f"\n财务概况:")
        print(f"  总预算: ¥{total_budget:,.2f}")
        print(f"  总成本: ¥{total_cost:,.2f}")
        print(f"  总收入: ¥{total_revenue:,.2f}")
        print(f"  净收益: ¥{total_revenue - total_cost:,.2f}")


def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="项目管理系统CLI")
    parser.add_argument("--data-file", default="data/projects.json", help="数据文件路径")
    
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
    
    pm = ProjectManager(args.data_file)
    
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
