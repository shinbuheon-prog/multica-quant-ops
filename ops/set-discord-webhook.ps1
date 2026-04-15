param(
    [Parameter(Mandatory = $true)]
    [string]$WebhookUrl
)

$ErrorActionPreference = "Stop"

$WebhookUrl = $WebhookUrl.Trim()
if ($WebhookUrl -like "https://discordapp.com/*") {
    $WebhookUrl = $WebhookUrl -replace "^https://discordapp\.com", "https://discord.com"
}

[System.Environment]::SetEnvironmentVariable(
    "DISCORD_WEBHOOK_URL",
    $WebhookUrl,
    "User"
)

$env:DISCORD_WEBHOOK_URL = $WebhookUrl

Write-Host "DISCORD_WEBHOOK_URL saved to Windows User environment variables."
Write-Host "Current session has also been updated."
Write-Host ""
Write-Host "Next test:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\ops\notify-discord.ps1 -DryRun"
