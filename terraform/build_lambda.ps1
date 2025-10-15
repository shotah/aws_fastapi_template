# Build script for Lambda function (PowerShell)
# Usage: .\build_lambda.ps1 <source_path> <build_path> <zip_filename>

param(
    [string]$SourcePath,
    [string]$BuildPath,
    [string]$ZipFilename
)

Write-Host "Building Lambda function..."
Write-Host "Source path: $SourcePath"
Write-Host "Build path: $BuildPath"
Write-Host "Zip filename: $ZipFilename"

# Create build directory if it doesn't exist
if (!(Test-Path $BuildPath)) {
    New-Item -ItemType Directory -Path $BuildPath -Force
}

# Create temporary directory for building
$TempDir = New-TemporaryFile | ForEach-Object { Remove-Item $_; New-Item -ItemType Directory -Path $_ }
Write-Host "Temporary build directory: $TempDir"

try {
    # Copy source code to temp directory
    Copy-Item -Path "$SourcePath\*" -Destination $TempDir -Recurse -Force

    # Install dependencies
    if (Test-Path "..\requirements.txt") {
        Write-Host "Installing Python dependencies..."
        pip install -r ..\requirements.txt -t $TempDir
    } else {
        Write-Host "No requirements.txt found, skipping dependency installation"
    }

    # Create zip file
    Set-Location $TempDir
    Compress-Archive -Path "*" -DestinationPath "$BuildPath\$ZipFilename" -Force

    Write-Host "Lambda function built successfully: $BuildPath\$ZipFilename"
} finally {
    # Clean up
    Remove-Item -Path $TempDir -Recurse -Force
}
