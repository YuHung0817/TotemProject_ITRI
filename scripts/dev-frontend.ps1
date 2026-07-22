$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $projectRoot "frontend")
try {
    $env:INIT_CWD = (Get-Location).Path
    npm run dev
} finally {
    Pop-Location
}
