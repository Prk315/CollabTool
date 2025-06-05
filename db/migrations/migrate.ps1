# PowerShell migration script for database
$ErrorActionPreference = "Stop"

# Database connection settings
$DB_HOST = "localhost"
$DB_PORT = "5432"
$DB_NAME = "collabtool"
$DB_USER = $env:USERNAME

Write-Host "► Running migrations on $DB_NAME@$DB_HOST`:$DB_PORT as $DB_USER"

$connectionString = "host=$DB_HOST port=$DB_PORT user=$DB_USER dbname=$DB_NAME"

# Create migrations tracking table
$createTableCmd = "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT now());"
& psql $connectionString -c $createTableCmd

# Get all SQL files and sort them
$sqlFiles = Get-ChildItem -Path "db/migrations" -Filter "*.sql" | Sort-Object Name

foreach ($file in $sqlFiles) {
    $version = $file.BaseName
    $checkCmd = "SELECT 1 FROM schema_migrations WHERE version='$version'"
    $alreadyApplied = & psql $connectionString -tAc $checkCmd
    
    if ($alreadyApplied -eq "1") {
        Write-Host "✓ $version already applied"
    }
    else {
        Write-Host "→ applying $version"
        & psql $connectionString -v ON_ERROR_STOP=1 -f $file.FullName
        $insertCmd = "INSERT INTO schema_migrations(version) VALUES('$version')"
        & psql $connectionString -c $insertCmd
    }
}

Write-Host "✔ All migrations applied."