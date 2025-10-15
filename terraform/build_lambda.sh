#!/bin/bash

# Build script for Lambda function
# Usage: ./build_lambda.sh <source_path> <build_path> <zip_filename>

set -e

SOURCE_PATH="$1"
BUILD_PATH="$2"
ZIP_FILENAME="$3"

echo "Building Lambda function..."
echo "Source path: $SOURCE_PATH"
echo "Build path: $BUILD_PATH"
echo "Zip filename: $ZIP_FILENAME"

# Create build directory if it doesn't exist
mkdir -p "$BUILD_PATH"

# Create temporary directory for building
TEMP_DIR=$(mktemp -d)
echo "Temporary build directory: $TEMP_DIR"

# Copy source code to temp directory
cp -r "$SOURCE_PATH"/* "$TEMP_DIR/"

# Install dependencies
if [ -f "../requirements.txt" ]; then
    echo "Installing Python dependencies..."
    pip install -r ../requirements.txt -t "$TEMP_DIR"
else
    echo "No requirements.txt found, skipping dependency installation"
fi

# Create zip file
cd "$TEMP_DIR"
zip -r "$BUILD_PATH/$ZIP_FILENAME" .

# Clean up
rm -rf "$TEMP_DIR"

echo "Lambda function built successfully: $BUILD_PATH/$ZIP_FILENAME"
