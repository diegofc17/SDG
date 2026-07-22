# backup_db.ps1 - PostgreSQL database backup via Docker
# Uses pg_dump inside the postgres container and saves the dump locally.
param(
    [string]$Destination = "$PSScriptRoot\backups\db",
    [string]$Timestamp   = (Get-Date -Format "yyyyMMdd_HHmmss"),
    [string]$Container   = "postgres_db",
    [string]$DbName      = "sgd",
    [string]$DbUser      = "sgd",
    [int]$KeepLast       = 7    # 0 = keep all
)

$DumpFile = "db_backup_$Timestamp.sql"
$LogFile  = "$PSScriptRoot\backups\backup.log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $entry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [$Level] $Message"
    Write-Output $entry
    Add-Content -Path $LogFile -Value $entry
}

# ── 1. Ensure destination exists ──────────────────────────────────────────────
if (-not (Test-Path $Destination)) {
    New-Item -ItemType Directory -Path $Destination | Out-Null
}

Write-Log "Starting DB backup → $DumpFile"

# ── 2. Check that the container is running ─────────────────────────────────────
$running = docker ps --filter "name=$Container" --format "{{.Names}}" 2>&1
if ($running -notmatch $Container) {
    Write-Log "Container '$Container' is not running. Starting Docker Compose..." "WARN"
    docker compose -f "$PSScriptRoot\docker-compose.yml" up -d db 2>&1 | Out-Null
    Start-Sleep -Seconds 5  # wait for postgres to be ready
}

# ── 3. Run pg_dump inside the container ───────────────────────────────────────
$localDump = Join-Path $Destination $DumpFile

try {
    docker exec $Container `
        pg_dump -U $DbUser -d $DbName --no-password `
        | Out-File -FilePath $localDump -Encoding utf8

    if ((Get-Item $localDump).Length -lt 100) {
        Write-Log "Dump file seems empty or too small. Backup may have failed." "ERROR"
        exit 1
    }

    # Compress the dump to save space
    $zipFile = "$localDump.gz"
    Compress-Archive -Path $localDump -DestinationPath ($localDump + ".zip") -Force
    Remove-Item $localDump -Force
    $finalFile = "$localDump.zip"

    Write-Log "DB backup created → $DumpFile.zip ($('{0:N1}' -f ((Get-Item $finalFile).Length / 1KB)) KB)"

} catch {
    Write-Log "DB backup FAILED: $_" "ERROR"
    exit 1
}

# ── 4. Retention: keep only the last N dumps ──────────────────────────────────
if ($KeepLast -gt 0) {
    $allDumps = Get-ChildItem -Path $Destination -Filter "db_backup_*.zip" |
                Sort-Object Name -Descending
    $toDelete = $allDumps | Select-Object -Skip $KeepLast
    foreach ($old in $toDelete) {
        Remove-Item -Force $old.FullName
        Write-Log "Deleted old DB backup → $($old.Name)" "CLEANUP"
    }
}

Write-Log "DB backup completed successfully."
