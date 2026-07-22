# backup_db.ps1 - PostgreSQL database backup (local pg_dump, no Docker required)
param(
    [string]$Destination = "$PSScriptRoot\backups\db",
    [string]$Timestamp   = (Get-Date -Format "yyyyMMdd_HHmmss"),
    [string]$DbHost      = "localhost",
    [string]$Port        = "5432",
    [string]$DbName      = "sgd",
    [string]$DbUser      = "sgd",
    [string]$DbPassword  = "Sgd2025#",
    [int]$KeepLast       = 7    # 0 = keep all
)

$DumpFile  = "db_backup_$Timestamp.sql"
$LocalDump = Join-Path $Destination $DumpFile
$LocalZip  = "$LocalDump.zip"
$LogFile   = "$PSScriptRoot\backups\backup.log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $entry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [$Level] $Message"
    Write-Output $entry
    if (-not (Test-Path (Split-Path $LogFile -Parent))) {
        New-Item -ItemType Directory -Path (Split-Path $LogFile -Parent) | Out-Null
    }
    Add-Content -Path $LogFile -Value $entry
}

# ── 1. Check pg_dump is available ────────────────────────────────────────────
$pgDump = Get-Command pg_dump -ErrorAction SilentlyContinue
if (-not $pgDump) {
    Write-Log "pg_dump not found. Add PostgreSQL bin folder to your PATH." "ERROR"
    Write-Log "  Typical path: C:\Program Files\PostgreSQL\<version>\bin" "ERROR"
    exit 1
}

# ── 2. Ensure local destination exists ───────────────────────────────────────
if (-not (Test-Path $Destination)) {
    New-Item -ItemType Directory -Path $Destination | Out-Null
}

Write-Log "Starting DB backup → $DumpFile"

# ── 3. Run pg_dump with PGPASSWORD env var ────────────────────────────────────
$env:PGPASSWORD = $DbPassword

try {
    & pg_dump `
        -h $DbHost `
        -p $Port `
        -U $DbUser `
        -d $DbName `
        -f $LocalDump `
        --no-password 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-Log "pg_dump exited with code $LASTEXITCODE" "ERROR"
        exit 1
    }
} finally {
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}

# ── 4. Validate dump file ─────────────────────────────────────────────────────
if (-not (Test-Path $LocalDump)) {
    Write-Log "Dump file not created." "ERROR"
    exit 1
}

$sizeKB = [math]::Round((Get-Item $LocalDump).Length / 1KB, 1)
if ($sizeKB -lt 1) {
    Write-Log "Dump file is empty (${sizeKB} KB). Check DB connection." "ERROR"
    Remove-Item $LocalDump -Force
    exit 1
}

Write-Log "Dump received (${sizeKB} KB). Compressing..."

# ── 5. Compress and remove uncompressed dump ─────────────────────────────────
Compress-Archive -Path $LocalDump -DestinationPath $LocalZip -Force
Remove-Item $LocalDump -Force

$zipKB = [math]::Round((Get-Item $LocalZip).Length / 1KB, 1)
Write-Log "DB backup created → $DumpFile.zip (${zipKB} KB)"

# ── 6. Retention ─────────────────────────────────────────────────────────────
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
