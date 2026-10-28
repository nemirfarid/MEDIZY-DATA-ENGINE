<#
.SYNOPSIS
    MEDIZY / SANTE DZ - Routine d'Entretien Hebdomadaire (PowerShell)
.DESCRIPTION
    Execute VACUUM ANALYZE et REINDEX CONCURRENTLY sur PostgreSQL/PostGIS,
    ou defragmente et optimise SQLite en environnement local (VACUUM; ANALYZE; PRAGMA optimize;),
    puis purge la memoire Redis.
#>

[CmdletBinding()]
param (
    [string]$PostgresHost = $env:POSTGRES_HOST,
    [string]$PostgresPort = $env:POSTGRES_PORT,
    [string]$PostgresDb = $env:POSTGRES_DB,
    [string]$PostgresUser = $env:POSTGRES_USER,
    [string]$PostgresPassword = $env:POSTGRES_PASSWORD,
    [string]$RedisHost = $env:REDIS_HOST,
    [string]$RedisPort = $env:REDIS_PORT,
    [string]$WebhookUrl = $env:WEBHOOK_URL
)

if (-not $PostgresHost) { $PostgresHost = "localhost" }
if (-not $PostgresPort) { $PostgresPort = "5432" }
if (-not $PostgresDb) { $PostgresDb = "medizy_db" }
if (-not $PostgresUser) { $PostgresUser = "medizy_user" }
if (-not $PostgresPassword) { $PostgresPassword = "medizy_password" }
if (-not $RedisHost) { $RedisHost = "localhost" }
if (-not $RedisPort) { $RedisPort = "6379" }

$startTime = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "    MEDIZY - Routine d'Entretien Hebdomadaire (PowerShell)" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "Base de donnees cible : ${PostgresUser}@${PostgresHost}:${PostgresPort}/${PostgresDb}"
Write-Host "Serveur Redis         : ${RedisHost}:${RedisPort}"

Write-Host "Date d'execution      : $((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))"
Write-Host "=============================================================================="

$env:PGPASSWORD = $PostgresPassword

$psqlCmd = Get-Command "psql" -ErrorAction SilentlyContinue
if ($psqlCmd) {
    Write-Host "[1/3] Execution de VACUUM ANALYZE sur PostGIS..." -ForegroundColor Yellow
    & psql -h $PostgresHost -p $PostgresPort -U $PostgresUser -d $PostgresDb -c "VACUUM (ANALYZE, VERBOSE) facilities; VACUUM (ANALYZE, VERBOSE) facility_suggestions;"
    
    Write-Host "[2/3] Execution de REINDEX INDEX CONCURRENTLY..." -ForegroundColor Yellow
    & psql -h $PostgresHost -p $PostgresPort -U $PostgresUser -d $PostgresDb -c "REINDEX INDEX CONCURRENTLY idx_facilities_geom; REINDEX INDEX CONCURRENTLY idx_facilities_name_trgm;"
    Write-Host "[OK] Statistiques PostGIS et index GiST/GIN rafraichis." -ForegroundColor Green
} else {
    Write-Host "[INFO] psql non disponible localement. Verification maintenance SQLite locale..." -ForegroundColor Yellow
    $sqlitePath = "E:\medizy_data\medizy_facilities_local.db"
    if (Test-Path $sqlitePath) {
        Write-Host "Optimisation base SQLite locale : $sqlitePath" -ForegroundColor Yellow
        & python -c "import sqlite3; conn = sqlite3.connect(r'E:\medizy_data\medizy_facilities_local.db'); conn.execute('VACUUM'); conn.execute('ANALYZE'); conn.execute('PRAGMA optimize'); conn.close(); print('[OK] SQLite optimise avec succes.')"
    }
}

# Redis purge
$redisCmd = Get-Command "redis-cli" -ErrorAction SilentlyContinue
if ($redisCmd) {
    Write-Host "[3/3] Defragmentation de la memoire Redis..." -ForegroundColor Yellow
    & redis-cli -h $RedisHost -p $RedisPort MEMORY PURGE | Out-Null
    Write-Host "[OK] Memoire Redis defragmente." -ForegroundColor Green
} else {
    Write-Host "[INFO] redis-cli non disponible sur cette machine (etape omise)." -ForegroundColor Gray
}

$elapsed = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - $startTime
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host "SUCCES : Entretien hebdomadaire termine en $elapsed secondes." -ForegroundColor Green
Write-Host "==============================================================================" -ForegroundColor Green
