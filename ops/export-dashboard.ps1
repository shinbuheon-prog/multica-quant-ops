param(
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
if (-not $OutputPath) {
    $OutputPath = Join-Path $PSScriptRoot "dashboard\dashboard-export.json"
}

$outputDir = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

Push-Location $root
try {
    $env:PYTHONPATH = Join-Path $root "src"
    python -m multica_quant_ops.dashboard_export `
        --ops-dir (Join-Path $root "ops") `
        --output $OutputPath
    if ($LASTEXITCODE -ne 0) {
        throw "dashboard export failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

Write-Host "Dashboard export prepared at $OutputPath"
