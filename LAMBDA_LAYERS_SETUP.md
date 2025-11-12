# Lambda Layers Deployment Setup - Ready to Deploy

## ✅ What's Been Created

1. **Lambda Handler** (`lambda_handler_zip.py`)
   - Uses Mangum to wrap FastAPI app
   - Compatible with zip deployment

2. **Build Scripts**:
   - `scripts/build-lambda-layer-docker.sh` - Builds layer in Docker (recommended)
   - `scripts/build-lambda-layer.sh` - Builds layer locally (fallback)
   - `scripts/build-function-zip.sh` - Builds function zip package
   - `scripts/deploy-zip.sh` - Full deployment script

3. **SAM Template** (`template.zip.yaml`)
   - Configured for zip deployment with layers
   - Includes DependenciesLayer resource
   - API function uses zip + layer

## 🚀 Quick Deploy

```bash
# Option 1: Full automated deployment
./scripts/deploy-zip.sh

# Option 2: Manual steps
# 1. Build layer (Docker recommended)
./scripts/build-lambda-layer-docker.sh

# 2. Build function zip
./scripts/build-function-zip.sh

# 3. Deploy with SAM
sam build --template template.zip.yaml
sam deploy --stack-name zapier-triggers-api-dev --capabilities CAPABILITY_IAM
```

## 📝 Notes

- **Layer Build**: The Docker-based build (`build-lambda-layer-docker.sh`) is recommended because it matches Lambda's exact environment and avoids cross-platform compilation issues.

- **Function Zip**: Already working! The function zip is 27KB and ready.

- **Dependencies**: The layer will contain all dependencies from `requirements.txt`. If the layer exceeds 250MB uncompressed, you may need to split into multiple layers or optimize dependencies.

## 🔧 Next Steps

1. Build the layer (may take a few minutes):
   ```bash
   ./scripts/build-lambda-layer-docker.sh
   ```

2. Deploy:
   ```bash
   ./scripts/deploy-zip.sh
   ```

3. Test the API endpoint from the CloudFormation outputs.

## ⚠️ Troubleshooting

- **Layer build fails**: Make sure Docker is running and you have internet access
- **Deployment fails**: Check that Terraform outputs are available and AWS credentials are configured
- **Function too large**: If function.zip > 50MB, move more code to the layer or optimize imports

