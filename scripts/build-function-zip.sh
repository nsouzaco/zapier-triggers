#!/bin/bash
# Build Lambda function zip package

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}📦 Building Lambda function zip package...${NC}"

# Create temporary directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf ${TEMP_DIR}" EXIT

echo -e "${YELLOW}Copying application code...${NC}"
# Copy application code
cp -r app ${TEMP_DIR}/
cp lambda_handler_zip.py ${TEMP_DIR}/
cp lambda_worker_zip.py ${TEMP_DIR}/

# Remove unnecessary files
find ${TEMP_DIR} -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find ${TEMP_DIR} -type f -name "*.pyc" -delete 2>/dev/null || true
find ${TEMP_DIR} -type f -name "*.pyo" -delete 2>/dev/null || true
find ${TEMP_DIR} -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Remove test files if any
find ${TEMP_DIR} -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find ${TEMP_DIR} -type d -name "test" -exec rm -rf {} + 2>/dev/null || true

echo -e "${YELLOW}Creating function zip...${NC}"
# Create zip file
cd ${TEMP_DIR}
zip -r function.zip . -q
mv function.zip ${OLDPWD}/
cd - > /dev/null

# Calculate size
SIZE=$(du -h function.zip | cut -f1)
echo -e "${GREEN}✅ Function zip created: function.zip (${SIZE})${NC}"

# Check if size is within limits (50MB)
if [ -f function.zip ]; then
    ZIP_SIZE_MB=$(du -sm function.zip | cut -f1)
    if [ ${ZIP_SIZE_MB} -gt 50 ]; then
        echo -e "${YELLOW}⚠️  Warning: Function zip size (${ZIP_SIZE_MB}MB) exceeds 50MB limit${NC}"
        echo -e "${YELLOW}   Consider moving more dependencies to the layer${NC}"
    fi
fi

echo -e "${GREEN}✅ Function zip build complete!${NC}"

