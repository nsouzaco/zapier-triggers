# Alternative Deployment Options for Zapier Triggers API

Given the persistent `Runtime.InvalidEntrypoint` issue with Lambda container images, here are viable alternative deployment strategies.

## Option 1: Lambda Zip Deployment with Layers (RECOMMENDED)

**Pros:**
- ✅ Avoids container image issues entirely
- ✅ Faster deployments (zip upload vs image push)
- ✅ Lower cold start times
- ✅ Simpler debugging
- ✅ Already using Mangum (Lambda-compatible)

**Cons:**
- ⚠️ 50MB code limit (can use layers for dependencies)
- ⚠️ Need to manage dependencies separately

**Implementation:**
- Package code as zip
- Put dependencies in Lambda Layer
- Use standard Lambda handler format

**Estimated Setup Time:** 1-2 hours

---

## Option 2: ECS Fargate with Application Load Balancer

**Pros:**
- ✅ Full control over container runtime
- ✅ No Lambda-specific limitations
- ✅ Better for long-running connections
- ✅ Already have Dockerfile
- ✅ Auto-scaling built-in

**Cons:**
- ⚠️ Higher cost (always running)
- ⚠️ More complex infrastructure
- ⚠️ Need to manage ALB, ECS service, etc.

**Implementation:**
- Use existing `Dockerfile`
- Deploy to ECS Fargate
- Configure ALB for API Gateway integration

**Estimated Setup Time:** 3-4 hours

---

## Option 3: AWS App Runner

**Pros:**
- ✅ Fully managed container service
- ✅ Automatic scaling
- ✅ Simple deployment (just push to ECR)
- ✅ Built-in load balancing
- ✅ Pay per use

**Cons:**
- ⚠️ Still uses container images (might have same issue)
- ⚠️ Less control than ECS
- ⚠️ Newer service (less documentation)

**Implementation:**
- Push image to ECR
- Create App Runner service
- Configure environment variables

**Estimated Setup Time:** 2-3 hours

---

## Option 4: SAM with Zip Packaging (No Container)

**Pros:**
- ✅ Avoids container image entirely
- ✅ Uses SAM (familiar tooling)
- ✅ Lambda Layers for dependencies
- ✅ Fast deployments

**Cons:**
- ⚠️ Need to restructure for zip deployment
- ⚠️ Dependency management via layers

**Implementation:**
- Convert to zip-based SAM template
- Create Lambda Layer for dependencies
- Update handler to use zip format

**Estimated Setup Time:** 2-3 hours

---

## Option 5: Terraform Direct Lambda Deployment

**Pros:**
- ✅ Full control over Lambda configuration
- ✅ Bypass SAM/CloudFormation issues
- ✅ Direct zip upload
- ✅ More explicit configuration

**Cons:**
- ⚠️ More manual setup
- ⚠️ Need to write Terraform for Lambda

**Implementation:**
- Create Terraform Lambda resource
- Package and upload zip
- Configure API Gateway integration

**Estimated Setup Time:** 3-4 hours

---

## Detailed Implementation: Option 1 (Zip + Layers)

This is the **fastest path to a working deployment** and avoids all container image issues.

### Step 1: Create Lambda Layer for Dependencies

```bash
# Create layer directory structure
mkdir -p lambda-layer/python
cd lambda-layer/python

# Install dependencies
pip install -r ../../requirements.txt -t .

# Remove unnecessary files to reduce size
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete

# Create zip
cd ..
zip -r ../dependencies-layer.zip python/
```

### Step 2: Create Lambda Handler for Zip

```python
# lambda_handler_zip.py
from mangum import Mangum
from app.main import app

# Disable lifespan for Lambda
handler = Mangum(app, lifespan="off")
```

### Step 3: Package Application Code

```bash
# Create deployment package
zip -r function.zip app/ lambda_handler_zip.py -x "*.pyc" "__pycache__/*" "*.git*"
```

### Step 4: Update SAM Template for Zip

```yaml
Resources:
  DependenciesLayer:
    Type: AWS::Serverless::LayerVersion
    Properties:
      LayerName: zapier-triggers-api-dependencies
      ContentUri: dependencies-layer.zip
      CompatibleRuntimes:
        - python3.11
      CompatibleArchitectures:
        - x86_64

  ApiFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub ${ProjectName}-${Environment}-api
      Runtime: python3.11
      Handler: lambda_handler_zip.handler
      CodeUri: function.zip
      Layers:
        - !Ref DependenciesLayer
      MemorySize: 1024
      Timeout: 60
      # ... rest of config
```

### Step 5: Deploy

```bash
sam build
sam deploy
```

---

## Detailed Implementation: Option 2 (ECS Fargate)

### Step 1: Create ECS Task Definition

```json
{
  "family": "zapier-triggers-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [{
    "name": "api",
    "image": "<ECR_IMAGE_URI>",
    "portMappings": [{
      "containerPort": 8000,
      "protocol": "tcp"
    }],
    "environment": [
      {"name": "ENVIRONMENT", "value": "dev"},
      // ... other env vars
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/zapier-triggers-api",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "ecs"
      }
    }
  }]
}
```

### Step 2: Create ECS Service

```hcl
# terraform/ecs.tf
resource "aws_ecs_service" "api" {
  name            = "zapier-triggers-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }
}
```

### Step 3: Configure ALB

```hcl
resource "aws_lb" "api" {
  name               = "zapier-triggers-api"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
}

resource "aws_lb_target_group" "api" {
  name     = "zapier-triggers-api"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path = "/health"
  }
}
```

---

## Comparison Matrix

| Option | Setup Time | Cost | Complexity | Reliability | Recommended |
|--------|-----------|------|------------|-------------|-------------|
| **Zip + Layers** | 1-2h | Low | Low | High | ⭐⭐⭐⭐⭐ |
| ECS Fargate | 3-4h | Medium | Medium | High | ⭐⭐⭐⭐ |
| App Runner | 2-3h | Medium | Low | Medium | ⭐⭐⭐ |
| SAM Zip | 2-3h | Low | Low | High | ⭐⭐⭐⭐ |
| Terraform Direct | 3-4h | Low | High | High | ⭐⭐⭐ |

---

## Recommendation

**Start with Option 1 (Zip + Layers)** because:
1. Fastest to implement (1-2 hours)
2. Avoids all container image issues
3. Lower cost than ECS
4. Simpler debugging
5. You're already using Mangum (perfect fit)

If Option 1 doesn't work or you need more control, **Option 2 (ECS Fargate)** is the next best choice since you already have a working Dockerfile.

---

## Quick Start: Option 1 Implementation

Would you like me to:
1. Create the Lambda Layer build script?
2. Update the SAM template for zip deployment?
3. Create the zip-compatible handler?
4. Set up the deployment pipeline?

Let me know which option you'd like to pursue!

