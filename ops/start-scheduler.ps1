$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$request = Join-Path $PSScriptRoot "requests\daily-paper-request.json"
$reportsDir = Join-Path $PSScriptRoot "reports"
$dashboardPath = Join-Path $PSScriptRoot "dashboard\dashboard-export.json"

New-Item -ItemType Directory -Force -Path $reportsDir | Out-Null

Push-Location $root
try {
    $env:PYTHONPATH = Join-Path $root "src"
    python -m multica_quant_ops.scheduler `
        --input $request `
        --output-dir $reportsDir `
        --time 09:30 `
        --timezone America/New_York `
        --ops-dir (Join-Path $root "ops") `
        --dashboard-output $dashboardPath `
        --telegram-notify `
        --telegram-alert-only
}
finally {
    Pop-Location
}
