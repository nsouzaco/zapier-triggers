# RDS-Only Configuration

## Overview

This application **only uses AWS RDS** for all database operations. Local database is **not used** and has been disabled.

## Configuration

### Environment Variables Required

Set these in your `.env` file or environment:

```bash
# AWS RDS Configuration (REQUIRED)
RDS_ENDPOINT=zapier-triggers-api-dev-postgres.crws0amqe1e3.us-east-1.rds.amazonaws.com
RDS_PORT=5432
RDS_DATABASE=triggers_api
RDS_USERNAME=triggers_api
RDS_PASSWORD=<your-rds-password>

# DO NOT set DATABASE_URL to localhost
# DATABASE_URL is commented out in .env
```

### How It Works

1. **Lambda (AWS)**: Always uses RDS (enforced by code)
2. **Local Development**: Uses RDS if configured (no localhost fallback)
3. **Error if RDS not configured**: Raises ValueError instead of falling back to localhost

### Code Configuration

**File**: `app/config.py` - `postgresql_url` property

- ✅ Checks for AWS environment → Forces RDS
- ✅ Local environment → Uses RDS if configured
- ✅ No localhost fallback → Raises error if RDS not available
- ⚠️ Warns if `DATABASE_URL` points to localhost

## Local Development

### Connecting to RDS from Local Machine

**Note**: RDS is in a private subnet, so you **cannot connect directly** from your local machine unless:
- You have VPN access to the VPC
- You're using an AWS bastion host
- You're using AWS Systems Manager Session Manager

### For Local Development

1. **Use Lambda for testing**: Deploy and test via Lambda
2. **Use AWS CloudShell**: Access RDS from CloudShell
3. **Use VPN/Bastion**: If you have network access configured
4. **Use `manage-api-keys.py --use-rds`**: Script will attempt RDS connection

### Managing API Keys

```bash
# List API keys from RDS
python scripts/manage-api-keys.py --use-rds list

# Create API key in RDS
python scripts/manage-api-keys.py --use-rds create --name "Test Customer" --email "test@example.com"
```

## Docker Compose

The `docker-compose.yml` file has PostgreSQL service **commented out** because:
- We don't use local database
- All operations go to AWS RDS
- Only Redis and DynamoDB Local are needed for local development

To start only the services we use:
```bash
docker-compose up -d redis dynamodb-local
```

## Verification

### Check Configuration

```python
from app.config import get_settings
settings = get_settings()
print(settings.postgresql_url)  # Should show RDS endpoint, not localhost
```

### Test Connection

```bash
# This will fail from local machine (RDS in private subnet)
# But will work from Lambda
python scripts/manage-api-keys.py --use-rds list
```

## Troubleshooting

### "RDS configuration is required" Error

**Cause**: RDS environment variables not set

**Solution**: Set `RDS_ENDPOINT`, `RDS_USERNAME`, and `RDS_PASSWORD` in `.env`

### "Operation timed out" from Local Machine

**Cause**: RDS is in private subnet, not accessible from local network

**Solution**: This is expected. Use Lambda or AWS CloudShell to access RDS.

### Lambda Can't Connect to RDS

**Check**:
1. Lambda VPC configuration
2. Security group rules (Lambda SG → RDS SG)
3. RDS endpoint format (should include port if needed)
4. RDS password is correct

## Migration from Local Database

If you have API keys in a local database that need to be migrated:

1. Export from local database (if accessible)
2. Use `manage-api-keys.py --use-rds create` to recreate in RDS
3. Or connect via AWS CloudShell/SSM and run SQL directly

