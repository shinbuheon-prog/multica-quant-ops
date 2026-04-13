$ErrorActionPreference = "Stop"

$request = Join-Path $PSScriptRoot "requests\daily-paper-request.json"
$reportsDir = Join-Path $PSScriptRoot "reports"

New-Item -ItemType Directory -Force -Path $reportsDir | Out-Null

Push-Location $root
try {
    $env:PYTHONPATH = Join-Path $root "src"
    python -m multica_quant_ops.scheduler --input $request --output-dir $reportsDir --time 09:30 --timezone America/New_York
}
finally {
    Pop-Location
}
