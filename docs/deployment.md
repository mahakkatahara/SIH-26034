# Deployment Guide — Legal Metrology Inspection System

## Prerequisites

- Docker Engine 24+
- Docker Compose v2+
- 4GB RAM minimum (8GB recommended)
- 20GB disk space

## Quick Start (Docker Compose)

```bash
# 1. Clone repository
git clone https://github.com/your-org/SIH-26034.git
cd SIH-26034

# 2. Configure environment
cp .env.example .env
# Edit .env — change ALL passwords and secrets

# 3. Generate a secure JWT secret
openssl rand -hex 32

# 4. Start services
docker compose up -d

# 5. Run migrations
docker compose exec backend alembic upgrade head

# 6. Seed initial data
docker compose exec backend python -m app.scripts.seed

# 7. Verify
curl http://localhost:8000/health
```

## Service URLs

| Service | URL | Notes |
|---------|-----|-------|
| Frontend | http://localhost:5173 | React dev server |
| Backend API | http://localhost:8000 | FastAPI |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Database | localhost:5432 | PostgreSQL |
| Redis | localhost:6379 | Cache |

## Production Checklist

- [ ] Change all default passwords in `.env`
- [ ] Generate strong JWT_SECRET_KEY (min 32 chars)
- [ ] Set `APP_ENV=production`, `DEBUG=false`
- [ ] Configure HTTPS (Nginx + Let's Encrypt)
- [ ] Set up database backups
- [ ] Configure log aggregation
- [ ] Enable Redis password
- [ ] Restrict CORS origins

## Database Migrations

```bash
# Apply migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Rollback one step
alembic downgrade -1
```

## Scaling Notes (Phase 9)

For production deployment beyond single-server:
- Use Gunicorn with multiple Uvicorn workers
- Set up PostgreSQL read replicas for reporting queries
- Use Redis Sentinel for HA
- Store images in object storage (MinIO or AWS S3)
- Use Nginx as reverse proxy with SSL termination
