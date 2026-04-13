$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

Push-Location $root
try {
    $env:PYTHONPATH = Join-Path $root "src"
    python -m multica_quant_ops.api.http
}
finally {
    Pop-Location
}
