# Docker Setup Guide

## Starting Docker

### macOS
1. **Open Docker Desktop**
   - Launch Docker Desktop from Applications
   - Wait for Docker to start (whale icon in menu bar should be steady)
   - You'll see "Docker Desktop is running" when ready

2. **Verify Docker is running:**
   ```bash
   docker ps
   ```
   Should return without errors (empty list is fine)

### Linux
```bash
# Start Docker service
sudo systemctl start docker

# Enable Docker to start on boot
sudo systemctl enable docker

# Verify
docker ps
```

### Windows
1. **Open Docker Desktop**
   - Launch Docker Desktop from Start menu
   - Wait for Docker to start

2. **Verify:**
   ```bash
   docker ps
   ```

## Starting Local Services

Once Docker is running:

```bash
# Start all services (PostgreSQL, Redis, DynamoDB Local)
make docker-up

# Check status
docker-compose ps

# View logs
make docker-logs

# Stop services
make docker-down
```

## Services

### PostgreSQL
- **Port**: 5432
- **Database**: triggers_api_dev
- **User**: triggers_api
- **Password**: triggers_api_dev

### Redis
- **Port**: 6379
- **No password** (local development)

### DynamoDB Local
- **Port**: 8000
- **Endpoint**: http://localhost:8000

## Troubleshooting

### "Cannot connect to Docker daemon"
- **Solution**: Start Docker Desktop (macOS/Windows) or Docker service (Linux)
- **Verify**: Run `docker ps` to confirm Docker is running

### Port already in use
- **Solution**: Stop the service using the port or change the port in docker-compose.yml
- **Check**: `lsof -i :5432` (for PostgreSQL) or `lsof -i :6379` (for Redis)

### Services won't start
- **Check logs**: `docker-compose logs`
- **Restart**: `make docker-down && make docker-up`
- **Clean up**: `docker-compose down -v` (removes volumes)

## Without Docker

If you don't want to use Docker, the application will work but:
- **PostgreSQL**: You'll need to install and run PostgreSQL locally
- **Redis**: You'll need to install and run Redis locally
- **DynamoDB**: The app will use local mode (no persistence)

The application gracefully handles missing services and will work in development mode.

