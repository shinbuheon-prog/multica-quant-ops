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
    if (-not $env:DISCORD_WEBHOOK_URL) {
        $env:DISCORD_WEBHOOK_URL = [System.Environment]::GetEnvironmentVariable(
            "DISCORD_WEBHOOK_URL",
            "User"
        )
    }
    $command = @(
        "-m", "multica_quant_ops.discord_notify",
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
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}

Write-Host "Discord notification step completed for $DashboardExportPath"
