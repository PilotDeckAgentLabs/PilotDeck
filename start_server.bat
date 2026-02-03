@echo off
setlocal

REM 项目管理系统 - Windows 启动脚本

set ROOT=%~dp0
cd /d "%ROOT%"

if not exist ".venv" (
  echo [INFO] 未检测到 .venv, 将在当前Python环境安装依赖
) else (
  call ".venv\Scripts\activate.bat"
)

python -m pip install -r requirements.txt

python "server\main.py"

endlocal
