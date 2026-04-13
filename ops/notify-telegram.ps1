param(
    [string]$DashboardExportPath,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
if (-not $DashboardExportPath) {
    $DashboardExportPath = Join-Path $PSScriptRoot "dashboard\dashboard-export.json"
}

Push-Location $root
try {
    $env:PYTHONPATH = Join-Path $root "src"
    $command = @(
        "-m", "multica_quant_ops.telegram_notify",
        "--dashboard-export", $DashboardExportPath
    )
    if ($DryRun) {
        $command += "--dry-run"
    }
    python @command
    if ($LASTEXITCODE -ne 0) {
        throw "telegram notification failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

Write-Host "Telegram notification step completed for $DashboardExportPath"
