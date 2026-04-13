$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$request = Join-Path $PSScriptRoot "requests\daily-paper-request.json"
$incidentsDir = Join-Path $PSScriptRoot "incidents"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$output = Join-Path $incidentsDir "incident-summary-$timestamp.txt"

New-Item -ItemType Directory -Force -Path $incidentsDir | Out-Null

Push-Location $root
try {
    $env:PYTHONPATH = Join-Path $root "src"
    $summary = python -m multica_quant_ops.cli --input $request --incident-summary
}
finally {
    Pop-Location
}

$summary | Set-Content -Encoding utf8 $output

Write-Host "Incident summary written to $output"
