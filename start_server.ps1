Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
Set-Location $root

if (Test-Path (Join-Path $root '.venv\Scripts\Activate.ps1')) {
  . (Join-Path $root '.venv\Scripts\Activate.ps1')
} else {
  Write-Host '[INFO] 未检测到 .venv, 将在当前Python环境安装依赖'
}

python -m pip install -r requirements.txt
python (Join-Path $root 'server\api_server.py')
