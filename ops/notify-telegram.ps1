param(
    [string]$DashboardExportPath,
    [switch]$DryRun,
    [switch]$AlertOnly,
    [int]$LowCallsThreshold = 5
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
        "--dashboard-export", $DashboardExportPath,
        "--low-calls-threshold", $LowCallsThreshold
    )
    if ($DryRun) {
        $command += "--dry-run"
    }
    if ($AlertOnly) {
        $command += "--alert-only"
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
