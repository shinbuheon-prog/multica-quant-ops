param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$venvActivate = Join-Path $root ".venv\Scripts\Activate.ps1"

Set-Location $root

if (Test-Path $venvActivate) {
    . $venvActivate
}
else {
    Write-Warning ".venv not found. Run 'python -m venv .venv' first if needed."
}

$env:PYTHONPATH = Join-Path $root "src"

Write-Host ""
Write-Host "[Session Bootstrap]"
Write-Host "Project root: $root"
Write-Host "PYTHONPATH: $env:PYTHONPATH"
Write-Host "Virtualenv: $(if (Test-Path $venvActivate) { '.venv activated' } else { 'not found' })"
Write-Host "ALPHAVANTAGE_API_KEY: $(if ($env:ALPHAVANTAGE_API_KEY) { 'set' } else { 'not set' })"
Write-Host "TELEGRAM_BOT_TOKEN: $(if ($env:TELEGRAM_BOT_TOKEN) { 'set' } else { 'not set' })"
Write-Host "TELEGRAM_CHAT_ID: $(if ($env:TELEGRAM_CHAT_ID) { 'set' } else { 'not set' })"
Write-Host "DISCORD_WEBHOOK_URL: $(if ($env:DISCORD_WEBHOOK_URL) { 'set' } else { 'not set' })"
Write-Host ""

if (-not $SkipTests) {
    python -m pytest tests\test_telegram_notify.py tests\test_scheduler.py -q
    if ($LASTEXITCODE -ne 0) {
        throw "Bootstrap verification failed with exit code $LASTEXITCODE"
    }
}

Write-Host "Next step:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\ops\show-status.ps1"
