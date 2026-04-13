$ErrorActionPreference = "Stop"

$usagePath = Join-Path $PSScriptRoot "runtime\alpha-vantage-usage.json"

if (-not (Test-Path $usagePath)) {
    Write-Host "No Alpha Vantage usage tracker file found at $usagePath"
    exit 0
}

Get-Content -Raw -Encoding utf8 $usagePath
