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
    if (-not $env:TELEGRAM_BOT_TOKEN) {
        $env:TELEGRAM_BOT_TOKEN = [System.Environment]::GetEnvironmentVariable(
            "TELEGRAM_BOT_TOKEN",
            "User"
        )
    }
    if (-not $env:TELEGRAM_CHAT_ID) {
        $env:TELEGRAM_CHAT_ID = [System.Environment]::GetEnvironmentVariable(
            "TELEGRAM_CHAT_ID",
            "User"
        )
    }
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
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}

Write-Host "Telegram notification step completed for $DashboardExportPath"
