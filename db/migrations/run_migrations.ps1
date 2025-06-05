# PowerShell migration script for database
$ErrorActionPreference = "Stop"
$VerbosePreference = "Continue"  # Enable verbose output

Write-Host "Starting database migration script..."

# Read connection details from .env file if it exists
$envFile = Join-Path -Path $PSScriptRoot -ChildPath "..\..\\.env"
if (Test-Path $envFile) {
    Write-Host "Found .env file, loading environment variables..."
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#][^=]*)=(.*)$') {
            $name = $matches[1]
            $value = $matches[2]
            Set-Item -Path "env:$name" -Value $value
            Write-Verbose "Set environment variable: $name"
        }
    }
}

# Function to find psql executable
function Find-Psql {
    Write-Host "Searching for psql executable..."
    
    # Check if psql is in PATH
    $psqlCmd = Get-Command "psql" -ErrorAction SilentlyContinue
    if ($psqlCmd) {
        Write-Host "Found psql in PATH: $($psqlCmd.Path)"
        return $psqlCmd.Path
    }
    
    # Common PostgreSQL installation directories
    $possiblePaths = @(
        "C:\Program Files\PostgreSQL",
        "C:\Program Files (x86)\PostgreSQL"
    )
    
    foreach ($basePath in $possiblePaths) {
        Write-Host "Checking for PostgreSQL in: $basePath"
        if (Test-Path $basePath) {
            # Look for version directories
            $versionDirs = Get-ChildItem -Path $basePath -Directory | Sort-Object -Property Name -Descending
            if ($versionDirs) {
                Write-Host "Found version directories: $($versionDirs.Name -join ', ')"
                
                foreach ($versionDir in $versionDirs) {
                    $psqlPath = Join-Path -Path $versionDir.FullName -ChildPath "bin\psql.exe"
                    Write-Host "Checking for psql at: $psqlPath"
                    if (Test-Path $psqlPath) {
                        Write-Host "Found psql at: $psqlPath"
                        return $psqlPath
                    }
                }
            } else {
                Write-Host "No version directories found"
            }
        } else {
            Write-Host "Path not found: $basePath"
        }
    }
    
    # Try additional common path for new PostgreSQL installations
    $sqlPath = "C:\Program Files\PostgreSQL\17\bin\psql.exe"
    Write-Host "Checking for psql at specific path: $sqlPath"
    if (Test-Path $sqlPath) {
        Write-Host "Found psql at: $sqlPath"
        return $sqlPath
    }
    
    # Checking in Program Files for any PostgreSQL direct installation
    $pgDir = "C:\Program Files\PostgreSQL\17"
    if (Test-Path $pgDir) {
        Get-ChildItem -Path $pgDir -Recurse -Filter "psql.exe" | ForEach-Object {
            Write-Host "Found psql at: $($_.FullName)"
            return $_.FullName
        }
    }
    
    Write-Host "psql executable not found in any common locations."
    return $null
}

# Find psql executable
$psqlPath = Find-Psql
if (-not $psqlPath) {
    Write-Host "Error: PostgreSQL command-line client (psql) not found."
    Write-Host "Please make sure PostgreSQL is installed and add its bin directory to your PATH,"
    Write-Host "or modify this script to point to your psql.exe location."
    exit 1
}

Write-Host "Using psql from: $psqlPath"

# Database connection settings
$DB_HOST = $env:DB_HOST
if (-not $DB_HOST) { $DB_HOST = "localhost" }

$DB_PORT = $env:DB_PORT
if (-not $DB_PORT) { $DB_PORT = "5432" }

$DB_NAME = $env:DB_NAME
if (-not $DB_NAME) { $DB_NAME = "collabtool" }

$DB_USER = $env:DB_USER
if (-not $DB_USER) { $DB_USER = "postgres" }

$DB_PASSWORD = $env:DB_PASSWORD
if (-not $DB_PASSWORD) { $DB_PASSWORD = "" }

Write-Host "Database connection parameters:"
Write-Host "Host: $DB_HOST"
Write-Host "Port: $DB_PORT"
Write-Host "Database: $DB_NAME"
Write-Host "User: $DB_USER"

# Create the PGPASSWORD environment variable for passwordless connection
if ($DB_PASSWORD) {
    $env:PGPASSWORD = $DB_PASSWORD
    Write-Host "PGPASSWORD environment variable set"
} else {
    Write-Host "No password provided, proceeding without setting PGPASSWORD"
}

Write-Host "► Running migrations on $DB_NAME@$DB_HOST`:$DB_PORT as $DB_USER"

# Function to execute psql commands
function Invoke-Psql {
    param (
        [string]$Query,
        [string]$File = $null
    )
    
    $baseArgs = @(
        "-h", $DB_HOST,
        "-p", $DB_PORT,
        "-U", $DB_USER,
        "-d", $DB_NAME
    )
    
    if ($File) {
        Write-Host "Executing SQL file: $File"
        $fullCommand = "$psqlPath " + ($baseArgs -join " ") + " -v ON_ERROR_STOP=1 -f `"$File`""
        Write-Host "Command: $fullCommand"
        & $psqlPath @baseArgs -v ON_ERROR_STOP=1 -f $File
    }
    else {
        Write-Host "Executing SQL query: $Query"
        $fullCommand = "$psqlPath " + ($baseArgs -join " ") + " -c `"$Query`""
        Write-Host "Command: $fullCommand"
        & $psqlPath @baseArgs -c $Query
    }
    
    $exitCode = $LASTEXITCODE
    Write-Host "Command exit code: $exitCode"
    return $exitCode
}

function Get-PsqlOutput {
    param (
        [string]$Query
    )
    
    Write-Host "Executing query to get output: $Query"
    $fullCommand = "$psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -A -c `"$Query`""
    Write-Host "Command: $fullCommand"
    $output = & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -A -c $Query
    Write-Host "Output: $output"
    return $output
}

# Try a simple connection test first
Write-Host "Testing database connection..."
try {
    & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d "postgres" -c "SELECT 1" -t
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Connection test failed with exit code $LASTEXITCODE"
        Write-Host "Check your PostgreSQL server and credentials"
        exit 1
    }
    Write-Host "Connection test successful!"
} catch {
    Write-Host "Connection test failed: $_"
    exit 1
}

# Create migrations tracking table
Write-Host "Creating migrations tracking table if it doesn't exist..."
Invoke-Psql -Query "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT now());"

# Get all SQL files and sort them
$migrationsDir = Join-Path -Path $PSScriptRoot -ChildPath "."
Write-Host "Looking for SQL migration files in: $migrationsDir"
$sqlFiles = Get-ChildItem -Path $migrationsDir -Filter "*.sql" | Sort-Object Name
Write-Host "Found SQL files: $($sqlFiles.Name -join ', ')"
Write-Host "SQL files found: $($sqlFiles.Count)"

foreach ($file in $sqlFiles) {
    $version = $file.BaseName
    Write-Host "Checking migration: $version"
    
    # Check if migration has already been applied
    $checkResult = Get-PsqlOutput -Query "SELECT 1 FROM schema_migrations WHERE version='$version'"
    
    if ($checkResult -eq "1") {
        Write-Host "✓ Migration $version already applied"
    } else {
        Write-Host "→ Applying migration: $version"
        $exitCode = Invoke-Psql -File $file.FullName
        if ($exitCode -ne 0) {
            Write-Host "✗ Error applying migration $version" -ForegroundColor Red
            exit $exitCode
        }
        $insertCmd = "INSERT INTO schema_migrations(version) VALUES('$version')"
        Invoke-Psql -Query $insertCmd
        Write-Host "✓ Migration $version applied successfully"
    }
}

Write-Host "✔ All migrations applied."

# Clear the PGPASSWORD environment variable for security
if ($env:PGPASSWORD) {
    Remove-Item env:PGPASSWORD
    Write-Host "PGPASSWORD environment variable cleared"
}

Write-Host "Database migration script completed."