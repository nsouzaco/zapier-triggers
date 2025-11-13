#!/bin/bash
# Build Lambda Layer using Docker (recommended for cross-platform compatibility)

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}📦 Building Lambda Layer using Docker...${NC}"

# Clean up previous build
rm -rf lambda-layer dependencies-layer.zip

# Build layer in Docker container matching Lambda's environment (x86_64)
docker run --rm \
    --platform linux/amd64 \
    --entrypoint /bin/bash \
    -v "$(pwd):/var/task" \
    -w /var/task \
    public.ecr.aws/lambda/python:3.11 \
    -c "
        yum install -y zip unzip 2>/dev/null || apt-get update && apt-get install -y zip unzip 2>/dev/null || echo 'zip may already be installed' && \
        mkdir -p lambda-layer/python && \
        pip install -r requirements.txt -t lambda-layer/python --no-cache-dir && \
        find lambda-layer/python -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true && \
        find lambda-layer/python -type d -name '*.dist-info' -exec rm -rf {} + 2>/dev/null || true && \
        find lambda-layer/python -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true && \
        find lambda-layer/python -type f -name '*.pyc' -delete 2>/dev/null || true && \
        find lambda-layer/python -type f -name '*.pyo' -delete 2>/dev/null || true && \
        find lambda-layer/python -type d -name 'tests' -exec rm -rf {} + 2>/dev/null || true && \
        find lambda-layer/python -type d -name 'test' -exec rm -rf {} + 2>/dev/null || true && \
        find lambda-layer/python -type f -name '*.md' -delete 2>/dev/null || true && \
        cd lambda-layer && \
        zip -r ../dependencies-layer.zip python/ -q && \
        cd .. && \
        echo 'Layer built successfully'
    "

# Calculate size
if [ -f dependencies-layer.zip ]; then
    SIZE=$(du -h dependencies-layer.zip | cut -f1)
    UNCOMPRESSED_SIZE=$(du -sm lambda-layer/python 2>/dev/null | cut -f1 || echo "0")
    
    echo -e "${GREEN}✅ Lambda Layer created: dependencies-layer.zip (${SIZE})${NC}"
    
    if [ ${UNCOMPRESSED_SIZE} -gt 250 ]; then
        echo -e "${YELLOW}⚠️  Warning: Uncompressed layer size (${UNCOMPRESSED_SIZE}MB) exceeds 250MB limit${NC}"
    fi
else
    echo -e "${RED}❌ Failed to create layer${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Layer build complete!${NC}"

