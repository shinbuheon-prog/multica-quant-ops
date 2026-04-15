$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $PSScriptRoot "runtime"
$reportsDir = Join-Path $PSScriptRoot "reports"
$incidentsDir = Join-Path $PSScriptRoot "incidents"
$dashboardPath = Join-Path $PSScriptRoot "dashboard\dashboard-export.json"

Set-Location $root

Write-Host ""
Write-Host "[Workspace Status]"
git status --short

Write-Host ""
Write-Host "[Latest Runtime Files]"
if (Test-Path $runtimeDir) {
    (
        Get-ChildItem $runtimeDir -File -Recurse |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 8 FullName, LastWriteTime |
        Format-Table -AutoSize |
        Out-String
    ).TrimEnd() | Write-Host
}
else {
    Write-Host "No runtime directory found."
}

Write-Host ""
Write-Host "[Latest Reports]"
if (Test-Path $reportsDir) {
    (
        Get-ChildItem $reportsDir -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 3 FullName, LastWriteTime |
        Format-Table -AutoSize |
        Out-String
    ).TrimEnd() | Write-Host
}
else {
    Write-Host "No reports directory found."
}

Write-Host ""
Write-Host "[Latest Incidents]"
if (Test-Path $incidentsDir) {
    (
        Get-ChildItem $incidentsDir -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 3 FullName, LastWriteTime |
        Format-Table -AutoSize |
        Out-String
    ).TrimEnd() | Write-Host
}
else {
    Write-Host "No incidents directory found."
}

Write-Host ""
Write-Host "[Dashboard Export]"
if (Test-Path $dashboardPath) {
    (
        Get-Content -LiteralPath $dashboardPath -Encoding utf8 | Select-Object -First 40 | Out-String
    ).TrimEnd() | Write-Host
}
else {
    Write-Host "No dashboard export found at $dashboardPath"
}

Write-Host ""
Write-Host "[Environment]"
Write-Host "ALPHAVANTAGE_API_KEY: $(if ($env:ALPHAVANTAGE_API_KEY) { 'set' } else { 'not set' })"
Write-Host "TELEGRAM_BOT_TOKEN: $(if ($env:TELEGRAM_BOT_TOKEN) { 'set' } else { 'not set' })"
Write-Host "TELEGRAM_CHAT_ID: $(if ($env:TELEGRAM_CHAT_ID) { 'set' } else { 'not set' })"
Write-Host "DISCORD_WEBHOOK_URL: $(if ($env:DISCORD_WEBHOOK_URL) { 'set' } else { 'not set' })"
