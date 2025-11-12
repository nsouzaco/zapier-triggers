# Database Configuration Analysis

## Problem Identified: Dual Database Issue

### Root Cause

The application is configured to use **TWO different databases**:

1. **Local Database** (Docker/Development):
   - Location: `localhost:5432`
   - Database: `triggers_api_dev`
   - User: `triggers_api`
   - Password: `triggers_api_dev`
   - Configured in: `.env` file as `DATABASE_URL`

2. **AWS RDS Database** (Production):
   - Location: `zapier-triggers-api-dev-postgres.crws0amqe1e3.us-east-1.rds.amazonaws.com:5432`
   - Database: `triggers_api`
   - User: `triggers_api`
   - Password: `5iU_bQexQPBTyzdq102EJNmfHcQRJZIrjNTQCqxmJfI`
   - Configured in: Lambda environment variables

### Configuration Priority Issue

In `app/config.py`, the `postgresql_url` property has this priority:

```python
1. If DATABASE_URL is set → Use it (LOCAL DATABASE)
2. If RDS_ENDPOINT + RDS_USERNAME + RDS_PASSWORD → Use RDS
3. Fallback → Use localhost (LOCAL DATABASE)
```

**Problem**: The `.env` file has `DATABASE_URL` set to localhost, so:
- **Local scripts** (`manage-api-keys.py`) → Connect to LOCAL database
- **Lambda function** → Should use RDS (no DATABASE_URL in env), but may have connection issues

### Current State

#### Local Environment (.env file):
```
DATABASE_URL=postgresql://triggers_api:triggers_api_dev@localhost:5432/triggers_api_dev
RDS_ENDPOINT=zapier-triggers-api-dev-postgres.crws0amqe1e3.us-east-1.rds.amazonaws.com
RDS_PASSWORD=5iU_bQexQPBTyzdq102EJNmfHcQRJZIrjNTQCqxmJfI
```

#### Lambda Environment Variables:
```
RDS_ENDPOINT=zapier-triggers-api-dev-postgres.crws0amqe1e3.us-east-1.rds.amazonaws.com:5432
RDS_PASSWORD=5iU_bQexQPBTyzdq102EJNmfHcQRJZIrjNTQCqxmJfI
RDS_USERNAME=triggers_api
RDS_DATABASE=triggers_api
RDS_PORT=5432
```

### Why Lambda Sees Different API Keys

The Lambda is connecting to RDS correctly, but:
1. API keys created via `manage-api-keys.py` go to **LOCAL database** (because `.env` has `DATABASE_URL`)
2. Lambda reads from **RDS database** (which has different/older API keys)
3. This creates a **data mismatch**

### Infrastructure Analysis

#### AWS RDS Instance:
- **Instance ID**: `zapier-triggers-api-dev-postgres`
- **Database Name**: `triggers_api`
- **Status**: Available
- **Endpoint**: `zapier-triggers-api-dev-postgres.crws0amqe1e3.us-east-1.rds.amazonaws.com:5432`
- **VPC**: Private subnet (Lambda can access via VPC)

#### Local Docker Database:
- **Container**: `triggers-api-postgres`
- **Database**: `triggers_api_dev` (different name!)
- **Port**: `5432` (exposed to host)
- **Purpose**: Local development only

### Solutions Required

1. **Remove local database fallback** - Force use of RDS in production
2. **Update .env file** - Remove or comment out `DATABASE_URL` for production use
3. **Fix config.py** - Ensure Lambda always uses RDS, never localhost
4. **Update manage-api-keys.py** - Add option to target RDS explicitly
5. **Migrate API keys** - Move any important keys from local DB to RDS

