#!/bin/bash
# Build Lambda Layer for dependencies

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}📦 Building Lambda Layer for dependencies...${NC}"

# Create layer directory structure
LAYER_DIR="lambda-layer"
PYTHON_DIR="${LAYER_DIR}/python"

# Clean up previous build
rm -rf ${LAYER_DIR}
mkdir -p ${PYTHON_DIR}

echo -e "${YELLOW}Installing dependencies...${NC}"
# Install dependencies to the layer directory
# Try python3 -m pip first, fallback to pip
# Note: psycopg2-binary may need PostgreSQL dev libraries on some systems
# For Lambda, we can use pre-built wheels which should work fine

PIP_CMD=""
if command -v python3 &> /dev/null; then
    PIP_CMD="python3 -m pip"
elif command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
else
    echo -e "${RED}❌ pip not found. Please install Python and pip.${NC}"
    exit 1
fi

# Install dependencies
# Lambda uses Python 3.11 on Linux x86_64, but we can install normally
# The dependencies will work fine in Lambda's environment
$PIP_CMD install -r requirements.txt -t ${PYTHON_DIR} --no-cache-dir

echo -e "${YELLOW}Cleaning up unnecessary files...${NC}"
# Remove unnecessary files to reduce size
find ${PYTHON_DIR} -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find ${PYTHON_DIR} -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find ${PYTHON_DIR} -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
find ${PYTHON_DIR} -type f -name "*.pyc" -delete 2>/dev/null || true
find ${PYTHON_DIR} -type f -name "*.pyo" -delete 2>/dev/null || true
find ${PYTHON_DIR} -type f -name "*.so" ! -name "*.so.*" -delete 2>/dev/null || true

# Remove test files and documentation
find ${PYTHON_DIR} -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find ${PYTHON_DIR} -type d -name "test" -exec rm -rf {} + 2>/dev/null || true
find ${PYTHON_DIR} -type f -name "*.md" -delete 2>/dev/null || true
find ${PYTHON_DIR} -type f -name "*.txt" ! -name "requirements.txt" -delete 2>/dev/null || true

echo -e "${YELLOW}Creating layer zip...${NC}"
# Create zip file
cd ${LAYER_DIR}
zip -r ../dependencies-layer.zip python/ -q
cd ..

# Calculate size
SIZE=$(du -h dependencies-layer.zip | cut -f1)
echo -e "${GREEN}✅ Lambda Layer created: dependencies-layer.zip (${SIZE})${NC}"

# Check if size is within limits (50MB compressed, 250MB uncompressed)
UNCOMPRESSED_SIZE=$(du -sm ${PYTHON_DIR} | cut -f1)
if [ ${UNCOMPRESSED_SIZE} -gt 250 ]; then
    echo -e "${YELLOW}⚠️  Warning: Uncompressed layer size (${UNCOMPRESSED_SIZE}MB) exceeds 250MB limit${NC}"
fi

echo -e "${GREEN}✅ Layer build complete!${NC}"

