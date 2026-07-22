# backup.ps1 - Project backup script with retention
param(
    [string]$Destination = "$PSScriptRoot\backups",
    [switch]$Compress,
    [string]$Timestamp   = (Get-Date -Format "yyyyMMdd_HHmmss"),
    [int]$KeepLast       = 7   # Keep only the last N backups (0 = keep all)
)

$Source     = $PSScriptRoot
$BackupName = "backup_$Timestamp"
$BackupPath = Join-Path $Destination $BackupName
$LogFile    = Join-Path $Destination "backup.log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $entry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [$Level] $Message"
    Write-Output $entry
    Add-Content -Path $LogFile -Value $entry
}

# ── 1. Ensure destination exists ─────────────────────────────────────────────
if (-not (Test-Path $Destination)) {
    New-Item -ItemType Directory -Path $Destination | Out-Null
}

# ── 2. Copy project files ─────────────────────────────────────────────────────
Write-Log "Starting backup → $BackupName"

try {
    # Gather items to copy, excluding sensitive/redundant folders
    $excludeList = @("backups", ".venv", "__pycache__", ".git", "*.pyc")
    $items = Get-ChildItem -Path $Source -Exclude $excludeList

    New-Item -ItemType Directory -Path $BackupPath | Out-Null
    foreach ($item in $items) {
        Copy-Item -Path $item.FullName -Destination $BackupPath -Recurse -Force
    }

    # ── 3. Compress if requested ──────────────────────────────────────────────
    if ($Compress) {
        $zipPath = "${BackupPath}.zip"
        Compress-Archive -Path "$BackupPath\*" -DestinationPath $zipPath -Force
        Remove-Item -Recurse -Force $BackupPath
        Write-Log "Compressed backup created → ${BackupName}.zip"
        $BackupPath = $zipPath
    } else {
        Write-Log "Folder backup created → $BackupName"
    }

} catch {
    Write-Log "Backup FAILED: $_" "ERROR"
    exit 1
}

# ── 4. Retention: remove old backups beyond KeepLast ─────────────────────────
if ($KeepLast -gt 0) {
    $pattern = if ($Compress) { "backup_*.zip" } else { "backup_*" }
    $allBackups = Get-ChildItem -Path $Destination -Filter $pattern |
                  Sort-Object Name -Descending

    $toDelete = $allBackups | Select-Object -Skip $KeepLast
    foreach ($old in $toDelete) {
        Remove-Item -Recurse -Force $old.FullName
        Write-Log "Deleted old backup → $($old.Name)" "CLEANUP"
    }
}

Write-Log "Backup completed successfully."
