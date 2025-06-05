# Simple PostgreSQL database migration script
$ErrorActionPreference = "Stop"

Write-Host "Starting simple database migration script..."

# Add PostgreSQL to PATH temporarily (based on service name 'postgresql-x64-17')
$pgBinPath = "C:\Program Files\PostgreSQL\17\bin"
if (Test-Path $pgBinPath) {
    Write-Host "Adding PostgreSQL bin directory to PATH: $pgBinPath"
    $env:Path = "$pgBinPath;$env:Path"
} else {
    Write-Host "Looking for PostgreSQL installation..."
    # Try to find PostgreSQL bin directory
    $possiblePaths = @(
        "C:\Program Files\PostgreSQL\17\bin",
        "C:\Program Files\PostgreSQL\16\bin",
        "C:\Program Files\PostgreSQL\15\bin",
        "C:\Program Files\PostgreSQL\14\bin",
        "C:\Program Files\PostgreSQL\13\bin"
    )
    
    $pgFound = $false
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            Write-Host "Found PostgreSQL bin directory: $path"
            $env:Path = "$path;$env:Path"
            $pgFound = $true
            break
        }
    }
    
    if (-not $pgFound) {
        Write-Host "Error: PostgreSQL bin directory not found. Please install PostgreSQL or add it to your PATH."
        exit 1
    }
}

# Check if psql is now available
try {
    $psqlVersion = psql --version
    Write-Host "psql found: $psqlVersion"
} catch {
    Write-Host "Error: psql command not found even after adding PostgreSQL to PATH."
    Write-Host "Please make sure PostgreSQL is properly installed."
    exit 1
}

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
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "SELECT 1" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Connection failed. Please check your PostgreSQL credentials."
    exit 1
}
Write-Host "Connection successful!"

# Create database if it doesn't exist
$dbExists = (psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | Trim)
if ($dbExists -ne "1") {
    Write-Host "Creating database $DB_NAME..."
    psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME"
}

# Create migrations tracking table
Write-Host "Creating migrations tracking table..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT now())"

# Apply migrations
$migrationsDir = $PSScriptRoot
$sqlFiles = Get-ChildItem -Path $migrationsDir -Filter "*.sql" | Sort-Object Name
Write-Host "Found $($sqlFiles.Count) migration files"

foreach ($file in $sqlFiles) {
    $version = $file.BaseName
    Write-Host "Checking migration: $version"
    
    # Check if already applied
    $applied = (psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -A -c "SELECT 1 FROM schema_migrations WHERE version='$version'" | Trim)
    
    if ($applied -eq "1") {
        Write-Host "✓ Migration $version already applied"
    } else {
        Write-Host "→ Applying migration: $version from $($file.FullName)"
        psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $file.FullName
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "✗ Error applying migration $version"
            exit $LASTEXITCODE
        }
        
        psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "INSERT INTO schema_migrations (version) VALUES ('$version')"
        Write-Host "✓ Migration $version applied successfully"
    }
}

# Clean up
Remove-Item Env:PGPASSWORD
Write-Host "✔ All migrations completed successfully."