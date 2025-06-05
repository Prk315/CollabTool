# PowerShell script for database migrations
$ErrorActionPreference = "Stop"

# Database connection settings
$DB_HOST = "localhost"
$DB_PORT = "5432"
$DB_NAME = "collabtool"
$DB_USER = "postgres"

Write-Host "► Running migrations on $DB_NAME@$DB_HOST`:$DB_PORT as $DB_USER"

# Create migrations tracking table
Write-Host "Creating migrations tracking table if it doesn't exist..."
$createTableCmd = @"
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY, 
    applied_at TIMESTAMP DEFAULT now()
);
"@

& psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c $createTableCmd

# Get all SQL files and sort them
$currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sqlFiles = Get-ChildItem -Path $currentDir -Filter "*.sql" | Sort-Object Name

foreach ($file in $sqlFiles) {
    $version = $file.BaseName
    Write-Host "Checking migration: $version"
    
    # Check if migration has already been applied
    $checkQuery = "SELECT 1 FROM schema_migrations WHERE version='$version'"
    $checkResult = & psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -A -c $checkQuery
    
    if ($checkResult -eq "1") {
        Write-Host "✓ Migration $version already applied"
    } 
    else {
        Write-Host "→ Applying migration: $version"
        & psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -v ON_ERROR_STOP=1 -f $file.FullName
        
        $insertQuery = "INSERT INTO schema_migrations(version) VALUES('$version')"
        & psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c $insertQuery
        
        Write-Host "✓ Migration $version applied successfully"
    }
}

Write-Host "✔ All migrations applied."