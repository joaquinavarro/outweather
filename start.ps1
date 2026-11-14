# ROOTSHIFT local launcher (Windows). Optional: `python -m rootshift` and Docker
# are the recommended ways to run it. Kept for convenience on Windows only.
# Usage:  .\start.ps1 [-Dev]
param(
    [switch]$Dev
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

if ($Dev) {
    Write-Host "ROOTSHIFT (dev) -- API http://127.0.0.1:8000 + web http://localhost:3000"
    Start-Process -FilePath "python" `
        -ArgumentList "-m", "uvicorn", "rootshift.api.app:app", "--host", "127.0.0.1", "--port", "8000", "--reload" `
        -WorkingDirectory $backend
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm.cmd run dev" -WorkingDirectory $frontend
    Write-Host "Open http://localhost:3000"
} else {
    Write-Host "ROOTSHIFT -- building the web app once, then serving everything on http://127.0.0.1:8000"
    if (-not (Test-Path (Join-Path $frontend "out"))) {
        Push-Location $frontend
        cmd /c "npm.cmd run build"
        Pop-Location
    }
    Start-Process -FilePath "python" `
        -ArgumentList "-m", "rootshift", "--host", "127.0.0.1", "--port", "8000" `
        -WorkingDirectory $backend
    Write-Host "Open http://127.0.0.1:8000 after ~10 seconds."
}
