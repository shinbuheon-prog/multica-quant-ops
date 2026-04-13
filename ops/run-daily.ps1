$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$request = Join-Path $PSScriptRoot "requests\daily-paper-request.json"
$reportsDir = Join-Path $PSScriptRoot "reports"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$output = Join-Path $reportsDir "daily-report-$timestamp.txt"

New-Item -ItemType Directory -Force -Path $reportsDir | Out-Null

Push-Location $root
try {
    $env:PYTHONPATH = Join-Path $root "src"
    python -m multica_quant_ops.cli --input $request --output $output
}
finally {
    Pop-Location
}

Write-Host "Daily workflow report written to $output"
