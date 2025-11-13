#!/bin/bash
# Setup script for AWS infrastructure

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/terraform"

echo "🚀 Setting up AWS infrastructure for Zapier Triggers API"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    echo "   Visit: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform is not installed. Please install it first."
    echo "   Visit: https://www.terraform.io/downloads"
    exit 1
fi

# Check AWS credentials
echo "🔐 Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured."
    echo "   Run: aws configure"
    exit 1
fi

echo "✅ AWS credentials configured"
echo ""

# Navigate to terraform directory
cd "$TERRAFORM_DIR"

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    echo "⚠️  terraform.tfvars not found. Creating from example..."
    if [ -f "terraform.tfvars.example" ]; then
        cp terraform.tfvars.example terraform.tfvars
        echo "📝 Please edit terraform/terraform.tfvars with your configuration"
        echo "   Then run this script again."
        exit 1
    else
        echo "❌ terraform.tfvars.example not found"
        exit 1
    fi
fi

# Initialize Terraform
echo "🔧 Initializing Terraform..."
terraform init

# Plan
echo ""
echo "📋 Planning infrastructure changes..."
terraform plan -out=tfplan

# Ask for confirmation
echo ""
read -p "Do you want to apply these changes? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "❌ Aborted"
    exit 1
fi

# Apply
echo ""
echo "🚀 Applying infrastructure changes..."
terraform apply tfplan

# Get outputs
echo ""
echo "📊 Infrastructure outputs:"
terraform output

echo ""
echo "✅ AWS infrastructure setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Update your .env file with the output values"
echo "   2. Run database migrations: make migrate"
echo "   3. Start the application: make run"

