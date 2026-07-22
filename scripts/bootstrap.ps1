$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

function Test-Tool([string]$Name) {
    try {
        & $Name --version *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw "winget was not found. Install App Installer from Microsoft Store first."
}

if (-not (Test-Tool "python")) {
    Write-Host "Installing Python 3.12..." -ForegroundColor Cyan
    winget install --id Python.Python.3.12 --exact --accept-package-agreements --accept-source-agreements
    Refresh-Path
}

if (-not (Test-Tool "node")) {
    Write-Host "Installing Node.js LTS..." -ForegroundColor Cyan
    winget install --id OpenJS.NodeJS.LTS --exact --accept-package-agreements --accept-source-agreements
    Refresh-Path
}

if (-not (Test-Tool "python") -or -not (Test-Tool "node")) {
    throw "Tools were installed but PATH is not refreshed. Reopen PowerShell and run this script again."
}

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Created .env. Set OPENAI_API_KEY before generating images." -ForegroundColor Yellow
}

& $PSScriptRoot\setup.ps1
Write-Host "Bootstrap complete. Run .\scripts\dev.ps1 to start development." -ForegroundColor Green

