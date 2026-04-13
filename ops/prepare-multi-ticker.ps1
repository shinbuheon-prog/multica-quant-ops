param(
    [Parameter(Mandatory = $true)]
    [string]$Tickers,
    [int]$Quantity = 1
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $PSScriptRoot "runtime"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outputDir = Join-Path $runtimeDir "batch-$timestamp"
$usagePath = Join-Path $runtimeDir "alpha-vantage-usage.json"

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

Push-Location $root
try {
    $env:PYTHONPATH = Join-Path $root "src"
    python -m multica_quant_ops.same_day_batch `
        --tickers $Tickers `
        --quantity $Quantity `
        --output-dir $outputDir `
        --usage-file $usagePath
    if ($LASTEXITCODE -ne 0) {
        throw "same_day_batch preparation failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

Write-Host "Multi-ticker preparation written to $outputDir"
