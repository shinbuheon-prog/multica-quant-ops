$ErrorActionPreference = "Stop"

param(
    [Parameter(Mandatory = $true)]
    [string]$Ticker,
    [int]$Quantity = 1
)

$root = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $PSScriptRoot "runtime"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$requestPath = Join-Path $runtimeDir "$Ticker-request-$timestamp.json"
$briefPath = Join-Path $runtimeDir "$Ticker-brief-$timestamp.json"
$usagePath = Join-Path $runtimeDir "alpha-vantage-usage.json"

New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

Push-Location $root
try {
    $env:PYTHONPATH = Join-Path $root "src"
    python -m multica_quant_ops.same_day `
        --ticker $Ticker `
        --quantity $Quantity `
        --output-request $requestPath `
        --output-brief $briefPath `
        --usage-file $usagePath
}
finally {
    Pop-Location
}

Write-Host "Same-day request prepared at $requestPath"
Write-Host "Paper-trading prep brief prepared at $briefPath"
Write-Host "Alpha Vantage usage tracker updated at $usagePath"
