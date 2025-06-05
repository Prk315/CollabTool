# PowerShell migration script for database with PostgreSQL path detection
$ErrorActionPreference = "Stop"

Write-Host "Starting database migration script..."

# Find psql executable function
function Find-Psql {
    # Common PostgreSQL installation directories for Windows
    $possiblePaths = @(
        "C:\Program Files\PostgreSQL\17\bin\psql.exe",
        "C:\Program Files\PostgreSQL\16\bin\psql.exe",
        "C:\Program Files\PostgreSQL\15\bin\psql.exe",
        "C:\Program Files\PostgreSQL\14\bin\psql.exe",
        "C:\Program Files\PostgreSQL\13\bin\psql.exe"
    )
    
    # Check if psql is in PATH
    $psqlInPath = Get-Command "psql" -ErrorAction SilentlyContinue
    if ($psqlInPath) {
        Write-Host "Found psql in PATH"
        return $psqlInPath.Path
    }
    
    # Check common installation paths
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            Write-Host "Found psql at: $path"
            return $path
        }
    }
    
    # Not found in common locations, search Program Files
    $psqlFiles = Get-ChildItem -Path "C:\Program Files" -Recurse -Filter "psql.exe" -ErrorAction SilentlyContinue
    if ($psqlFiles.Count -gt 0) {
        Write-Host "Found psql at: $($psqlFiles[0].FullName)"
        return $psqlFiles[0].FullName
    }
    
    Write-Host "Error: PostgreSQL client (psql) not found. Please install PostgreSQL or add it to your PATH."
    return $null
}

# Find psql executable
$psqlPath = Find-Psql
if (-not $psqlPath) {
    Write-Host "Error: Could not find psql executable. Please install PostgreSQL or modify this script to point to your psql.exe location."
    exit 1
}

Write-Host "Using psql from: $psqlPath"

# Database connection parameters
$DB_HOST = "localhost"
$DB_PORT = "5432"
$DB_NAME = "collabtool"
$DB_USER = "postgres"

Write-Host "Database connection: $DB_NAME@$DB_HOST`:$DB_PORT as $DB_USER"

# Get password if needed
$password = Read-Host -Prompt "Enter PostgreSQL password for user $DB_USER" -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
$DB_PASSWORD = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

# Set PGPASSWORD for passwordless connection
$env:PGPASSWORD = $DB_PASSWORD

# Test connection
Write-Host "Testing database connection..."
& $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d "postgres" -c "SELECT 1" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Connection failed. Please check your PostgreSQL credentials."
    exit 1
}

Write-Host "Connection successful!"

# Create the database if it doesn't exist
Write-Host "Ensuring database '$DB_NAME' exists..."
$dbExists = & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d "postgres" -t -c "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'"
if (-not $dbExists) {
    Write-Host "Creating database $DB_NAME..."
    & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d "postgres" -c "CREATE DATABASE $DB_NAME"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create database."
        exit 1
    }
    Write-Host "Database created."
}

# Create migrations tracking table
Write-Host "Creating migrations tracking table if it doesn't exist..."
& $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT now());"

# Get all SQL migration files
$migrationsDir = $PSScriptRoot
$sqlFiles = Get-ChildItem -Path $migrationsDir -Filter "*.sql" | Sort-Object Name
Write-Host "Found $($sqlFiles.Count) migration files"

# Apply migrations
foreach ($file in $sqlFiles) {
    $version = $file.BaseName
    Write-Host "Checking migration: $version"
    
    # Check if migration has already been applied
    $applied = & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -A -c "SELECT 1 FROM schema_migrations WHERE version='$version'"
    
    if ($applied -eq "1") {
        Write-Host "✓ Migration $version already applied"
    } 
    else {
        Write-Host "→ Applying migration: $version"
        & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $file.FullName
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "✗ Error applying migration $version"
            exit $LASTEXITCODE
        }
        
        & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "INSERT INTO schema_migrations(version) VALUES('$version')"
        Write-Host "✓ Migration $version applied successfully"
    }
}

Write-Host "✔ All migrations applied successfully."

# Clean up
Remove-Item Env:PGPASSWORD

Write-Host "Database migration completed."