$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python) -or -not (Test-Path "$projectRoot\frontend\node_modules")) {
    throw "Project is not initialized. Run .\scripts\bootstrap.ps1 first."
}

$backend = Start-Job -Name "totem-backend" -ScriptBlock {
    param($root, $pythonPath)
    $env:NO_COLOR = "1"
    $env:FORCE_COLOR = "0"
    Set-Location (Join-Path $root "backend")
    & $pythonPath -m uvicorn app.main:app --reload --port 8000 --no-use-colors 2>&1 |
        ForEach-Object { $_.ToString() }
    if ($LASTEXITCODE -ne 0) {
        throw "Backend exited with code $LASTEXITCODE."
    }
} -ArgumentList $projectRoot, $python

$frontend = Start-Job -Name "totem-frontend" -ScriptBlock {
    param($root)
    $env:NO_COLOR = "1"
    $env:FORCE_COLOR = "0"
    Set-Location (Join-Path $root "frontend")
    $env:INIT_CWD = (Get-Location).Path
    npm run dev -- --host 0.0.0.0 2>&1 |
        ForEach-Object { $_.ToString() }
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend exited with code $LASTEXITCODE."
    }
} -ArgumentList $projectRoot

Write-Host "Totem development environment started." -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173"
$lanIp = [System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) |
    Where-Object {
        $_.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork -and
        -not [System.Net.IPAddress]::IsLoopback($_) -and
        -not $_.IPAddressToString.StartsWith("169.254.")
    } |
    ForEach-Object { $_.IPAddressToString } |
    Select-Object -First 1
if ($lanIp) {
    Write-Host "Phone (same Wi-Fi): http://${lanIp}:5173" -ForegroundColor Cyan
} else {
    Write-Host "Phone: use http://<this-PC-IPv4-address>:5173" -ForegroundColor Yellow
}
Write-Host "API docs: http://localhost:8000/docs"
Write-Host "Press Ctrl+C to stop both services."

try {
    while ($backend.State -in @("Running", "NotStarted") -and $frontend.State -in @("Running", "NotStarted")) {
        Receive-Job $backend, $frontend -ErrorAction Continue
        Wait-Job -Job $backend, $frontend -Any -Timeout 1 | Out-Null
    }
    Receive-Job $backend, $frontend -ErrorAction Continue
    if ($backend.State -eq "Failed" -or $frontend.State -eq "Failed") {
        throw "The frontend or backend stopped unexpectedly."
    }
} finally {
    Stop-Job $backend, $frontend -ErrorAction SilentlyContinue
    Remove-Job $backend, $frontend -Force -ErrorAction SilentlyContinue
}
