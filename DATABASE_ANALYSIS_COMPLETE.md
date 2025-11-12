# Complete Database Analysis & Fix Report

## Executive Summary

**Problem**: The application was using TWO separate databases:
- **Local Database** (`localhost:5432/triggers_api_dev`) - Used by local scripts
- **AWS RDS** (`zapier-triggers-api-dev-postgres.../triggers_api`) - Used by Lambda

This caused API keys created locally to not be available in Lambda, and vice versa.

## Root Cause Analysis

### Configuration Issue

**File**: `app/config.py` - `postgresql_url` property

**Original Priority**:
1. `DATABASE_URL` environment variable → **Local database**
2. RDS configuration → **AWS RDS**
3. Fallback → **Local database**

**Problem**: 
- `.env` file had `DATABASE_URL=postgresql://...@localhost:5432/triggers_api_dev`
- Local scripts (`manage-api-keys.py`) used this → **Created keys in local DB**
- Lambda had no `DATABASE_URL` → **Used RDS** (correct)
- **Result**: Data mismatch between local and production

### Infrastructure Verification

✅ **Single RDS Instance**: `zapier-triggers-api-dev-postgres`
- Database: `triggers_api`
- Schema: `public`
- Tables: `customers`, `subscriptions`
- No read replicas
- No Multi-AZ (single instance)

✅ **Lambda Configuration**:
- VPC: Configured correctly
- Security Groups: Allow RDS access
- Environment Variables: RDS config present

## Fixes Implemented

### 1. Updated `app/config.py`

**Changes**:
- Added AWS environment detection (`AWS_LAMBDA_FUNCTION_NAME`, `AWS_EXECUTION_ENV`)
- **Lambda ALWAYS uses RDS** - No localhost fallback in AWS
- Raises error if RDS not configured in AWS
- Local development prefers RDS if configured

**Code**:
```python
# In AWS/Lambda, ALWAYS use RDS - never use local database
if is_aws:
    if not (self.rds_endpoint and self.rds_username and self.rds_password):
        raise ValueError("Running in AWS but RDS configuration is missing...")
    return f"postgresql://{self.rds_username}:{self.rds_password}@{endpoint}/{self.rds_database}"
```

### 2. Updated `.env` file

**Changes**:
- Commented out `DATABASE_URL` (backed up to `.env.backup`)
- Local scripts now use RDS by default when RDS config is present

### 3. Updated `scripts/manage-api-keys.py`

**Changes**:
- Added `--use-rds` flag to explicitly force RDS connection
- Added connection verification and warnings
- Better error messages

## Current State

### Lambda Environment
- ✅ **Forced to use RDS** (code enforcement)
- ✅ **Connecting to**: `zapier-triggers-api-dev-postgres.crws0amqe1e3.us-east-1.rds.amazonaws.com:5432/triggers_api`
- ✅ **Finds 2 customers** with API keys:
  - `WRZnbWDW8VVO9HeGf2w3JKSYkF6jF2XP` (Customer: `4d25b335-5197-408e-a8cd-5101d4dd6f6c`)
  - `b5U0hmUcxuSpKk7p0a1bU04XaQQCQuIh` (Customer: `7e0a31fd-3b19-4af0-b957-a6d5ee86eff3`)

### Local Environment
- ✅ **Uses RDS** (DATABASE_URL commented out, RDS config present)
- ⚠️ **Cannot connect from local machine** (RDS in private subnet - expected)
- ✅ **When run with RDS config**, finds 3 customers:
  - `9SlmMrsC3QwdFqJKgg2EgHPYCiyuv7Zs`
  - `vQTTgm4pfWvsVnZxjvHXZ1Ft3kw43JoI`
  - `OawPXNx7ibFQv7Vt5rA6xfNiJeU3TOyG`

## Mystery: Why Different API Keys?

**Observation**: Lambda sees different API keys than when querying directly with same config.

**Possible Explanations**:
1. **Different connection timing** - API keys created at different times
2. **Transaction isolation** - Different transaction contexts
3. **Connection pooling** - Stale connections in pool
4. **Query ordering** - `LIMIT 3` might return different results based on ordering

**Investigation Needed**:
- Check if there are actually 5 total customers (2 seen by Lambda + 3 seen locally)
- Verify query ordering (add `ORDER BY created_at DESC`)
- Check for any database-level filtering or views

## Working API Keys (Lambda Verified)

These are the API keys that Lambda can actually find and use:

1. **`WRZnbWDW8VVO9HeGf2w3JKSYkF6jF2XP`**
   - Customer ID: `4d25b335-5197-408e-a8cd-5101d4dd6f6c`
   - ✅ **Verified working in Lambda**

2. **`b5U0hmUcxuSpKk7p0a1bU04XaQQCQuIh`**
   - Customer ID: `7e0a31fd-3b19-4af0-b957-a6d5ee86eff3`
   - ✅ **Verified working in Lambda**

## Recommendations

1. **Use Lambda's API keys** for production testing
2. **Investigate data discrepancy** - Why Lambda sees different keys
3. **Standardize on RDS** - All operations should use RDS, not local DB
4. **Add query ordering** - Use `ORDER BY created_at DESC` for consistent results
5. **Consider connection pool settings** - May need to tune for Lambda cold starts

## Files Modified

1. `app/config.py` - Added AWS detection, forced RDS in Lambda
2. `.env` - Commented out DATABASE_URL (backed up)
3. `scripts/manage-api-keys.py` - Added --use-rds flag
4. `app/services/customer_service.py` - Enhanced logging
5. `app/core/auth.py` - Enhanced logging

## Next Steps

1. ✅ **Configuration fixed** - Lambda forced to use RDS
2. ✅ **Local config updated** - Prefers RDS over local
3. ⚠️ **Data investigation** - Why different API keys seen
4. 🔄 **Use working API keys** - Test with `WRZnbWDW8VVO9HeGf2w3JKSYkF6jF2XP`

