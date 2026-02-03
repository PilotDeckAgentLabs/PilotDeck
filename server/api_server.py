#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目管理系统 REST API 服务

DEPRECATED: This file is kept for backward compatibility only.
New code should import from mypm package:
    from mypm import create_app, Config
    
See server/main.py for the new entry point.
"""

# Backward compatibility: re-export Flask app
from mypm import create_app, Config

app = create_app(Config())


# === 启动服务 ===

if __name__ == '__main__':
    config = Config()
    print("=" * 60)
    print("项目管理系统 API 服务")
    print("=" * 60)
    print(f"数据库: {config.DB_FILE}")
    port = config.PORT
    print(f"API地址: http://localhost:{port}/api")
    print(f"Web界面: http://localhost:{port}")
    print("=" * 60)
    print("")
    print("⚠️  WARNING: api_server.py is deprecated.")
    print("   Use 'python server/main.py' instead.")
    print("=" * 60)
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=config.DEBUG
    )
