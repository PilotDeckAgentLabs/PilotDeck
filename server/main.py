#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目管理系统 REST API 服务 - 入口点

Usage:
    python server/main.py
    
Environment variables:
    PM_PORT: Server port (default: 8689)
    PM_DEBUG: Debug mode (default: 0)
    PM_ADMIN_TOKEN: Admin API token
    PM_AGENT_TOKEN: Agent API token
"""

import sys
import os

# Add server directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mypm import create_app, Config  # noqa: E402


def main():
    """Application entry point."""
    config = Config()
    app = create_app(config)
    
    print("=" * 60)
    print("项目管理系统 API 服务")
    print("=" * 60)
    print(f"数据库: {config.DB_FILE}")
    print(f"API地址: http://localhost:{config.PORT}/api")
    print(f"Web界面: http://localhost:{config.PORT}")
    print(f"调试模式: {'开启' if config.DEBUG else '关闭'}")
    print("=" * 60)
    
    app.run(
        host='0.0.0.0',
        port=config.PORT,
        debug=config.DEBUG
    )


if __name__ == '__main__':
    main()
