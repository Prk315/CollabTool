# Ultra-simple PostgreSQL migration script
# Uses direct path to psql to avoid any PATH issues

# PostgreSQL directory path - modify this if needed
$pgDir = "C:\Program Files\PostgreSQL\17\bin"
$psqlPath = "$pgDir\psql.exe"

# Check if psql exists at this location
if (-not (Test-Path $psqlPath)) {
    Write-Host "PostgreSQL not found at $psqlPath"
    Write-Host "Please edit this script and update the path to your PostgreSQL installation."
    exit 1
}

Write-Host "Using psql at: $psqlPath"

# Database connection parameters
$DB_HOST = "localhost"
$DB_PORT = "5432"
$DB_NAME = "collabtool"
$DB_USER = "postgres"

# Prompt for password
$password = Read-Host "Enter PostgreSQL password for user $DB_USER"
$env:PGPASSWORD = $password

# Test connection
Write-Host "Testing database connection..."
& $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "SELECT 1" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Connection failed. Please check your PostgreSQL credentials."
    exit 1
}
Write-Host "Connection successful!"

# Create database if it doesn't exist
$dbExists = & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 
if (-not $dbExists) {
    Write-Host "Creating database $DB_NAME..."
    & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME"
}

# Create migrations tracking table
Write-Host "Creating migrations tracking table..."
& $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT now());"

# Get all SQL migration files
$migrationsDir = $PSScriptRoot
$sqlFiles = Get-ChildItem -Path $migrationsDir -Filter "*.sql" | Sort-Object Name
Write-Host "Found $($sqlFiles.Count) migration files"

# Apply each migration
foreach ($file in $sqlFiles) {
    $version = $file.BaseName
    Write-Host "Checking migration: $version"
    
    # Check if already applied
    $applied = & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -A -c "SELECT 1 FROM schema_migrations WHERE version='$version'"
    
    if ($applied -eq "1") {
        Write-Host "Migration $version already applied"
    } else {
        Write-Host "Applying migration: $version"
        & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $file.FullName
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Error applying migration $version"
            exit $LASTEXITCODE
        }
        
        & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "INSERT INTO schema_migrations (version) VALUES ('$version');"
        Write-Host "Migration $version applied successfully"
    }
}

# Clean up
Remove-Item Env:PGPASSWORD
Write-Host "All migrations completed successfully."