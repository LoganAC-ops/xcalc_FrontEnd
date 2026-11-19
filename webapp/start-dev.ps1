# Launches the xlcalc Studio dev environment in two side-by-side terminals.
# Usage:  .\start-dev.ps1

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

$backend = Join-Path $here "backend"
$frontend = Join-Path $here "frontend"

# Install frontend deps on first run
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Installing frontend dependencies (first run)..." -ForegroundColor Cyan
    Push-Location $frontend
    npm install
    Pop-Location
}

Write-Host "Starting backend  -> http://localhost:8000" -ForegroundColor Cyan
Write-Host "Starting frontend -> http://localhost:5173" -ForegroundColor Cyan
Write-Host "Open http://localhost:5173 in your browser." -ForegroundColor Yellow
Write-Host ""

$backendCmd  = "cd '$backend';  python -m uvicorn main:app --reload --port 8000"
$frontendCmd = "cd '$frontend'; npm run dev"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host "Both servers launched in new windows. Close them to stop." -ForegroundColor Green
