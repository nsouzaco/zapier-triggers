# Database Configuration Fix - Summary

## Problem Identified

### Dual Database Issue
The application was configured to use **TWO separate databases**:

1. **Local Database** (`localhost:5432/triggers_api_dev`)
   - Used by local scripts when `DATABASE_URL` is set in `.env`
   - API keys created via `manage-api-keys.py` went here
   - **NOT accessible from Lambda**

2. **AWS RDS Database** (`zapier-triggers-api-dev-postgres.crws0amqe1e3.us-east-1.rds.amazonaws.com:5432/triggers_api`)
   - Used by Lambda function
   - Has different/older API keys
   - **This is the production database**

### Root Cause
The `app/config.py` `postgresql_url` property had this priority:
1. `DATABASE_URL` (from `.env`) → **Local database**
2. RDS configuration → **AWS RDS**
3. Fallback → **Local database**

Since `.env` had `DATABASE_URL=postgresql://...@localhost:5432/triggers_api_dev`, all local operations used the local database, while Lambda correctly used RDS, creating a **data mismatch**.

## Fixes Implemented

### 1. Updated `app/config.py`
- **Added AWS detection**: Checks for `AWS_LAMBDA_FUNCTION_NAME` or `AWS_EXECUTION_ENV`
- **Forces RDS in AWS**: Lambda will ALWAYS use RDS, never localhost
- **Raises error if RDS not configured in AWS**: Prevents silent fallback to localhost
- **Local development**: Prefers RDS if configured, falls back to local only if RDS not available

### 2. Updated `.env` file
- **Commented out `DATABASE_URL`**: Prevents local scripts from using local database
- **Backed up to `.env.backup`**: Original configuration preserved
- **Now uses RDS by default**: When RDS config is present, it's used

### 3. Updated `scripts/manage-api-keys.py`
- **Added `--use-rds` flag**: Explicitly force RDS connection
- **Added connection verification**: Warns if DATABASE_URL might override RDS
- **Better error messages**: Clear guidance on which database is being used

## Current Configuration

### Lambda Environment (AWS)
```
RDS_ENDPOINT=zapier-triggers-api-dev-postgres.crws0amqe1e3.us-east-1.rds.amazonaws.com:5432
RDS_PASSWORD=5iU_bQexQPBTyzdq102EJNmfHcQRJZIrjNTQCqxmJfI
RDS_USERNAME=triggers_api
RDS_DATABASE=triggers_api
RDS_PORT=5432
```
✅ **Lambda will ALWAYS use RDS** (enforced by code)

### Local Environment (.env)
```
#DATABASE_URL=postgresql://triggers_api:triggers_api_dev@localhost:5432/triggers_api_dev
RDS_ENDPOINT=zapier-triggers-api-dev-postgres.crws0amqe1e3.us-east-1.rds.amazonaws.com
RDS_PASSWORD=5iU_bQexQPBTyzdq102EJNmfHcQRJZIrjNTQCqxmJfI
RDS_USERNAME=triggers_api
RDS_DATABASE=triggers_api
```
✅ **Local scripts will use RDS** (DATABASE_URL commented out)

## Infrastructure Verification

### RDS Instance
- **Instance**: `zapier-triggers-api-dev-postgres`
- **Database**: `triggers_api`
- **Status**: Available
- **Multi-AZ**: No (single instance)
- **Read Replicas**: None
- **VPC**: Private subnet (accessible from Lambda via VPC)

### Lambda Configuration
- **VPC**: Configured with subnets and security groups
- **Security Group**: `sg-0cac7dfd9f87a5989`
- **RDS Security Group**: `sg-001fe2bd81954fac4` (allows VPC CIDR 172.31.0.0/16)
- **Connection**: Lambda can reach RDS on port 5432

## Next Steps

1. **Test Lambda with updated code**: Verify it uses RDS correctly
2. **Migrate API keys**: If needed, copy important keys from local DB to RDS
3. **Verify API key lookup**: Test that Lambda can find API keys in RDS
4. **Remove local database dependency**: Consider removing Docker PostgreSQL for production workflows

## API Keys in RDS

Current API keys in RDS database:
1. `9SlmMrsC3QwdFqJKgg2EgHPYCiyuv7Zs` - Test Customer
2. `vQTTgm4pfWvsVnZxjvHXZ1Ft3kw43JoI` - Customer Name  
3. `OawPXNx7ibFQv7Vt5rA6xfNiJeU3TOyG` - Lambda Test Customer

**Note**: Lambda logs show different API keys (`WRZnbWDW8V...`, `b5U0hmUcxu...`), which suggests either:
- Connection pooling with stale connections
- Different schema or database
- Transaction isolation issues

This needs further investigation.

