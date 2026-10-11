$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
python -m uvicorn server:app --host 127.0.0.1 --port 8787
