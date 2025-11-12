# Lambda Deployment Issue Report: Runtime.InvalidEntrypoint

## Problem Summary

AWS Lambda function deployed as a container image is failing with `Runtime.InvalidEntrypoint` error during the INIT phase. The handler works perfectly when tested locally using Docker with the Lambda runtime interface emulator, but fails in the actual Lambda environment.

**Error Details:**
```
INIT_REPORT Init Duration: 5.36 ms	Phase: init	Status: error	Error Type: Runtime.InvalidEntrypoint
```

**Lambda Function:**
- Name: `zapier-triggers-api-dev-api`
- Region: `us-east-1`
- Package Type: `Image`
- Architecture: `x86_64`
- Base Image: `public.ecr.aws/lambda/python:3.11`

## What Works

1. ✅ **Local Docker Test**: Handler executes successfully when tested locally
   ```bash
   docker run --rm -p 9000:8080 <image> 
   curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{"test":"event"}'
   # Returns: {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": "{\"status\": \"ok\", \"message\": \"Handler is working\"}"}
   ```

2. ✅ **Docker Build**: Image builds successfully with handler validation
   ```
   ✓ Handler imports successfully
   Handler function: <function lambda_handler at 0x7ffff72d9c60>
   ```

3. ✅ **ECR Push**: Image pushes to ECR successfully
4. ✅ **Lambda Update**: Function code updates complete successfully
5. ✅ **Lambda Configuration**: Handler is `None` (correct for container images), PackageType is `Image`

## What Doesn't Work

❌ **Lambda Execution**: All invocations fail with `Runtime.InvalidEntrypoint` during INIT phase, before handler code executes.

## Attempted Solutions

### Option 1: Explicit ENTRYPOINT
- Added explicit `ENTRYPOINT ["/lambda-entrypoint.sh"]` to Dockerfile
- Result: ❌ Still fails

### Option 2: Minimal Handler (No Imports)
- Created ultra-minimal handler with zero imports
- Result: ❌ Still fails

### Option 3: Standard AWS Handler Naming
- Changed from `lambda_handler.handler` to `lambda_function.lambda_handler`
- Result: ❌ Still fails

### Option 4: Minimal Dockerfile (No Dependencies)
- Removed all dependencies and app code, only handler file
- Result: ❌ Still fails

### Option 5: ImageConfig in SAM Template
- Added explicit `ImageConfig.Command` in CloudFormation template
- Result: ❌ Still fails

## Current Code State

### Dockerfile.lambda.minimal
```dockerfile
# Ultra-minimal Dockerfile - Option 5
FROM public.ecr.aws/lambda/python:3.11

# Copy ONLY the handler file - no dependencies, no app code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

# Verify handler imports
RUN python -c "import lambda_function; print('✓ Handler imports successfully')"

# Set handler
CMD ["lambda_function.lambda_handler"]
```

### lambda_function.py
```python
def lambda_handler(event, context):
    """AWS Lambda handler - using standard naming convention."""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": '{"status": "ok", "message": "Handler is working"}'
    }
```

### template.yaml (SAM Template)
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Zapier Triggers API - Serverless Application

Resources:
  # API Lambda Function
  ApiFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub ${ProjectName}-${Environment}-api
      PackageType: Image
      ImageUri: !Sub ${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com/${ProjectName}-${Environment}-api:latest
      ImageConfig:
        Command: ["lambda_function.lambda_handler"]
      Role: !Ref ApiRoleArn
      MemorySize: 1024
      Timeout: 60
      Environment:
        Variables:
          SQS_EVENT_QUEUE_URL: !Ref SqsEventQueueUrl
          SQS_DLQ_URL: !Ref SqsDlqUrl
          DYNAMODB_TABLE_NAME: !Ref DynamoDBTableName
          REDIS_ENDPOINT: !Ref RedisEndpoint
          RDS_ENDPOINT: !Ref RdsEndpoint
          RDS_PASSWORD: !Ref RdsPassword
          RDS_DATABASE: triggers_api
          RDS_USERNAME: triggers_api
          RDS_PORT: "5432"
      Events:
        ApiEvent:
          Type: Api
          Properties:
            Path: /{proxy+}
            Method: ANY
        RootEvent:
          Type: Api
          Properties:
            Path: /
            Method: ANY
```

## Key Observations

1. **Local Test Success**: The handler works perfectly when tested locally with Docker, proving:
   - The Docker image is correctly built
   - The handler function exists and is callable
   - The CMD format is correct
   - The entrypoint script can find and execute the handler

2. **Lambda INIT Phase Failure**: The error occurs during INIT phase, before any handler code runs, suggesting:
   - Lambda's runtime validator is failing
   - The handler might not be importable during Lambda's validation
   - There might be a difference in how Lambda reads the CMD vs local Docker

3. **Entrypoint Script Analysis**:
   ```bash
   # /lambda-entrypoint.sh from base image
   #!/bin/sh
   if [ $# -ne 1 ]; then
     echo "entrypoint requires the handler name to be the first argument" 1>&2
     exit 142
   fi
   export _HANDLER="$1"
   ```
   The script requires exactly 1 argument (the handler name).

4. **Lambda Function Configuration**:
   - Handler: `None` (correct for container images)
   - ImageUri: `971422717446.dkr.ecr.us-east-1.amazonaws.com/zapier-triggers-api-dev-api:latest`
   - ImageConfig: `null` (even after adding to template, it shows as null in get-function-configuration)
   - PackageType: `Image`
   - Architecture: `x86_64`

5. **Docker Image Inspection**:
   ```bash
   docker inspect <image> --format 'ENTRYPOINT: {{.Config.Entrypoint}} | CMD: {{.Config.Cmd}}'
   # Output: ENTRYPOINT: [/lambda-entrypoint.sh] | CMD: [lambda_function.lambda_handler]
   ```

6. **Local Runtime Logs** (when it works):
   ```
   11 Nov 2025 03:26:53,400 [INFO] (rapid) exec '/var/runtime/bootstrap' (cwd=/var/task, handler=)
   ```
   Note: `handler=` is empty in local logs, but it still works.

## Test Commands

### Build Image
```bash
DOCKER_BUILDKIT=0 docker build --platform linux/amd64 -f Dockerfile.lambda.minimal -t zapier-triggers-api-dev-api:latest .
```

### Test Locally (WORKS)
```bash
docker run --rm -p 9000:8080 zapier-triggers-api-dev-api:latest &
sleep 3
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{"test":"event"}'
# Returns: {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": "{\"status\": \"ok\", \"message\": \"Handler is working\"}"}
```

### Push to ECR
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 971422717446.dkr.ecr.us-east-1.amazonaws.com
docker tag zapier-triggers-api-dev-api:latest 971422717446.dkr.ecr.us-east-1.amazonaws.com/zapier-triggers-api-dev-api:latest
docker push 971422717446.dkr.ecr.us-east-1.amazonaws.com/zapier-triggers-api-dev-api:latest
```

### Update Lambda Function
```bash
aws lambda update-function-code \
  --function-name zapier-triggers-api-dev-api \
  --region us-east-1 \
  --image-uri 971422717446.dkr.ecr.us-east-1.amazonaws.com/zapier-triggers-api-dev-api:latest
```

### Test Lambda (FAILS)
```bash
curl "https://qvl62b4mhh.execute-api.us-east-1.amazonaws.com/Prod/health"
# Returns: {"message": "Internal server error"}
```

### Check Logs
```bash
aws logs tail /aws/lambda/zapier-triggers-api-dev-api --region us-east-1 --since 5m --format short
# Shows: Runtime.InvalidEntrypoint errors
```

## Environment Details

- **AWS Account**: 971422717446
- **Region**: us-east-1
- **ECR Repository**: `zapier-triggers-api-dev-api`
- **Base Image**: `public.ecr.aws/lambda/python:3.11`
- **Build Platform**: linux/amd64 (building on macOS ARM64)
- **SAM CLI Version**: 1.146.0
- **Docker Version**: Latest (with platform emulation)

## Questions for Investigation

1. Why does the handler work locally but fail in Lambda?
2. Is there a difference in how Lambda validates the handler vs local Docker?
3. Why does `ImageConfig` show as `null` even after setting it in the template?
4. Could there be an issue with how SAM/CloudFormation processes the ImageConfig?
5. Is there a specific format or requirement for the handler name in container images?
6. Could the issue be related to the base image version (Python 3.11)?
7. Should we try a different base image or build approach?

## Next Steps to Try

1. **Check Lambda Function ImageConfig via AWS Console**: Verify if ImageConfig is actually set
2. **Try Different Base Image**: Test with `public.ecr.aws/lambda/python:3.12` or `3.10`
3. **Explicit Entrypoint in Dockerfile**: Try setting both ENTRYPOINT and CMD explicitly
4. **Check CloudFormation Stack**: Verify the actual deployed configuration
5. **Try Direct Lambda Update**: Update ImageConfig directly via AWS CLI
6. **Compare with Working Worker Function**: Check if `lambda_worker.py` has different configuration
7. **Test with AWS Official Example**: Deploy AWS's official Python container example to verify setup

## Additional Files

### Dockerfile.lambda (current)
```dockerfile
# Dockerfile for Lambda deployment
FROM public.ecr.aws/lambda/python:3.11

# Copy requirements and install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ${LAMBDA_TASK_ROOT}/app
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

# Verify handler imports successfully during build
RUN python -c "import lambda_function; print('✓ Handler imports successfully'); print('Handler function:', lambda_function.lambda_handler)"

# Use standard AWS Lambda handler naming
CMD ["lambda_function.lambda_handler"]
```

### lambda_handler.py (original, also tested)
```python
"""AWS Lambda handler for FastAPI application."""

# Absolutely minimal handler - no imports, no path manipulation
def handler(event, context):
    """Minimal test handler."""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": '{"status": "ok", "message": "Handler is working"}'
    }
```

## Conclusion

The Docker image is correctly built and works locally, but Lambda's runtime validator fails during INIT phase. This suggests the issue is in how Lambda reads or validates the handler configuration, not in the Docker image itself. The problem persists even with:
- Ultra-minimal handler (no imports)
- Explicit ENTRYPOINT
- ImageConfig in template
- Standard AWS naming conventions

Further investigation needed into Lambda's container image handler validation process.

