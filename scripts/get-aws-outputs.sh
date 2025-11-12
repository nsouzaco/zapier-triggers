#!/bin/bash
# Get AWS infrastructure outputs

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/terraform"

cd "$TERRAFORM_DIR"

if [ ! -d ".terraform" ]; then
    echo "❌ Terraform not initialized. Run: ./scripts/setup-aws.sh"
    exit 1
fi

echo "📊 AWS Infrastructure Outputs:"
echo ""
terraform output -json | jq -r 'to_entries[] | "\(.key): \(.value.value)"'

