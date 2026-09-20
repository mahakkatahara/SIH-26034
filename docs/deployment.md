# Deployment Guide — Legal Metrology Inspection System

## Prerequisites

- Docker Engine 24+
- Docker Compose v2+
- 4GB RAM minimum (8GB recommended)
- 20GB disk space
- Outbound internet access to Google Generative AI API (if using live Gemini Vision)

---

## Quick Start (Docker Compose)

```bash
# 1. Clone repository
git clone https://github.com/Aarav-Jainn/SIH-26034.git
cd SIH-26034

# 2. Configure environment
cp .env.example .env
# Edit .env — set GEMINI_API_KEY and change ALL default passwords

# 3. Generate a secure JWT secret
openssl rand -hex 32

# 4. Start services
docker compose up -d

# 5. Run Alembic migrations (single source of schema truth)
docker compose exec backend alembic upgrade head

# 6. Seed initial administrative and rules data
docker compose exec backend python -m app.scripts.seed

# 7. Verify health
curl http://localhost:8000/health
```

---

## AI Pipeline & External Network Configuration

### Gemini Vision Pipeline (Default Production Mode)
The live vision extraction pipeline utilizes Google Gemini Vision (`gemini-2.5-flash`) via the `google-genai` SDK:
- **`GEMINI_API_KEY`**: Must be set in `.env`.
- **`AI_PIPELINE_MODE`**: Set to `vision`.
- **`VISION_MODEL`**: Set to `gemini-2.5-flash` (or `gemini-3.5-flash-lite`).
- **Network Access**: Outbound HTTPS connectivity to `generativelanguage.googleapis.com` on port 443 is required. Package image bytes are transmitted externally to Google's endpoints for extraction.

### Air-Gapped / Offline Fallback Mode
If deployed in a fully air-gapped environment without outbound internet access:
- Set `AI_PIPELINE_MODE=stub` in `.env`.
- The system operates offline via `StubPipeline`. Analysis results will return `pipeline_status="DEV_STUB"` and overall compliance will be marked `NEEDS_REVIEW` to mandate manual verification.
- Local OCR via PaddleOCR is planned as a future on-premise engine for air-gapped installations.

---

## Service URLs

| Service | URL | Notes |
|---------|-----|-------|
| Frontend | http://localhost:5173 | React Vite development server |
| Backend API | http://localhost:8000 | FastAPI Application |
| API Docs | http://localhost:8000/docs | OpenAPI / Swagger UI |
| Database | localhost:5432 | PostgreSQL 15 |
| Redis | localhost:6379 | In-memory cache & rate limiter |

---

## Production Checklist

- [ ] Change all default passwords and secrets in `.env`
- [ ] Configure valid `GEMINI_API_KEY` with appropriate quotas
- [ ] Verify outbound firewall allows `generativelanguage.googleapis.com:443`
- [ ] Generate strong `JWT_SECRET_KEY` (min 32 random characters)
- [ ] Set `APP_ENV=production` and `DEBUG=false`
- [ ] Run `alembic upgrade head` to ensure all schema migrations are applied
- [ ] Configure HTTPS reverse proxy (Nginx + Let's Encrypt)
- [ ] Set up automated PostgreSQL database backups
- [ ] Configure log aggregation and error monitoring (e.g. Sentry)
- [ ] Enable Redis password authentication
- [ ] Restrict `BACKEND_CORS_ORIGINS` to authorized frontend domains

---

## Database Migrations

Alembic is the **single source of truth** for database schema definitions:

```bash
# Apply migrations to head
alembic upgrade head

# Create a new migration revision after modifying SQLAlchemy models
alembic revision --autogenerate -m "description_of_change"

# Test migration reversibility
alembic downgrade -1
alembic upgrade head

# Regenerate database/schema.sql snapshot
make dump-schema
```

---

## Scaling Notes (Phase 9)

For high-throughput production deployment beyond single-server:
- Run FastAPI via Gunicorn with multiple Uvicorn worker processes (`uvicorn.workers.UvicornWorker`).
- Set up PostgreSQL read replicas for intensive analytical queries.
- Use Redis Sentinel or Redis Cluster for high availability caching.
- Store inspection images in an S3-compatible object store (e.g., MinIO or AWS S3) instead of the local filesystem.
- Terminate SSL and handle rate limiting at the Nginx reverse proxy layer.
