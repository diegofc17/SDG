# setup_backup_task.ps1
# Registers daily automatic backups (files + database) using Windows Task Scheduler.
# Run this script ONCE as Administrator.
#
# Usage:
#   .\setup_backup_task.ps1                         # default: files at 02:00 AM, DB at 02:30 AM
#   .\setup_backup_task.ps1 -TimeFiles "20:00"      # file backup at 8 PM
#   .\setup_backup_task.ps1 -TimeDB    "20:30"      # DB backup at 8:30 PM
#   .\setup_backup_task.ps1 -Compress               # compress file backups to .zip
#   .\setup_backup_task.ps1 -KeepLast 14            # keep last 14 backups
#   .\setup_backup_task.ps1 -Remove                 # remove both tasks

param(
    [string]$TimeFiles = "14:22",
    [string]$TimeDB    = "14:22",
    [switch]$Compress,
    [int]$KeepLast     = 7,
    [switch]$Remove
)

$TaskFiles = "SGD_AutoBackup_Files"
$TaskDB    = "SGD_AutoBackup_DB"
$Root      = $PSScriptRoot

# ── Helper to remove a task ───────────────────────────────────────────────────
function Remove-TaskIfExists([string]$Name) {
    if (Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $Name -Confirm:$false
        Write-Host "  ✅ Task '$Name' removed." -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Task '$Name' not found." -ForegroundColor Yellow
    }
}

# ── Remove mode ───────────────────────────────────────────────────────────────
if ($Remove) {
    Write-Host "`nRemoving scheduled tasks...`n"
    Remove-TaskIfExists $TaskFiles
    Remove-TaskIfExists $TaskDB
    Write-Host ""
    exit
}

# ── Helper to register a task ─────────────────────────────────────────────────
function Register-BackupTask {
    param(
        [string]$Name,
        [string]$Script,
        [string]$ExtraArgs,
        [string]$Time
    )
    $psArgs  = "-ExecutionPolicy Bypass -NonInteractive -File `"$Script`" $ExtraArgs"
    $action  = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $psArgs
    $trigger = New-ScheduledTaskTrigger -Daily -At $Time
    $settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable:$false `
        -WakeToRun:$false

    Register-ScheduledTask `
        -TaskName $Name `
        -Action   $action `
        -Trigger  $trigger `
        -Settings $settings `
        -RunLevel Limited `
        -Force | Out-Null

    Write-Host "  ✅ '$Name' → daily at $Time" -ForegroundColor Green
}

# ── Build argument strings ────────────────────────────────────────────────────
$fileArgs = "-KeepLast $KeepLast"
if ($Compress) { $fileArgs += " -Compress" }

$dbArgs = "-KeepLast $KeepLast"

# ── Register both tasks ───────────────────────────────────────────────────────
Write-Host "`nRegistering scheduled backup tasks...`n"

try {
    Register-BackupTask -Name $TaskFiles -Script "$Root\backup.ps1"    -ExtraArgs $fileArgs -Time $TimeFiles
    Register-BackupTask -Name $TaskDB    -Script "$Root\backup_db.ps1" -ExtraArgs $dbArgs   -Time $TimeDB

    Write-Host ""
    Write-Host "  Configuration:" -ForegroundColor Cyan
    Write-Host "    Files  : every day at $TimeFiles  → backups\backup_<timestamp>\" -ForegroundColor Cyan
    Write-Host "    DB     : every day at $TimeDB  → backups\db\db_backup_<timestamp>.zip" -ForegroundColor Cyan
    Write-Host "    Retain : last $KeepLast backups per type" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  To remove: .\setup_backup_task.ps1 -Remove" -ForegroundColor DarkGray
    Write-Host ""

} catch {
    Write-Host "❌ Failed: $_" -ForegroundColor Red
    Write-Host "   Run this script as Administrator." -ForegroundColor Yellow
}
