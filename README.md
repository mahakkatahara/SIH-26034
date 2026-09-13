# SIH-26034 — AI-Powered Legal Metrology Compliance Inspection System

> **Smart India Hackathon 2026 | Problem Statement 26034**  
> Ministry of Consumer Affairs, Food & Public Distribution — Legal Metrology Division

---

## Overview

A production-quality web application for enforcement officials to:

- Upload and scan images of packaged commodities
- Extract mandatory declarations from package labels using OCR/CV
- Validate declarations against Legal Metrology (Packaged Commodities) Rules, 2011
- Detect missing, misleading, or non-compliant declarations
- Analyse readability and estimate font size
- Generate compliance/non-compliance reports (PDF & DOCX)
- Maintain inspection history with searchable product repository
- Provide enforcement dashboards with trend analytics

---

## Architecture

```
Frontend (React + TypeScript + Tailwind)
        │
        │  REST / JWT
        ▼
Backend (FastAPI + Python)
  ├─ Auth Service (JWT RBAC)
  ├─ Inspection Service
  ├─ Product Service
  ├─ AI Pipeline (Phase 2+)
  │    ├─ Image Preprocessor (OpenCV)
  │    ├─ OCR Engine (PaddleOCR)
  │    ├─ Declaration Extractor
  │    └─ [STUB in Phase 1 — clearly marked]
  ├─ Rule Engine (deterministic, data-driven)
  └─ Report Generator (PDF / DOCX)
        │
        ▼
PostgreSQL (SQLAlchemy + Alembic)
```

**Design Principle:** The LLM is NOT the legal decision-maker.  
Pipeline: Image → Preprocessing → OCR → Extraction → Rule Engine → Compliance Result  
LLM/RAG is used only for legal explanation and NL assistance (Phase 7).

---

## Project Structure

```
SIH-26034/
├── frontend/       # React + TypeScript + Tailwind (Vite)
├── backend/        # FastAPI + SQLAlchemy
├── ai/             # AI/CV pipeline (stubs → real in Phase 2+)
├── rule-engine/    # JSON-driven compliance rule engine
├── database/       # Schema & seed SQL
├── reports/        # PDF / DOCX generation (stubs → real in Phase 8)
├── docs/           # Architecture, API, deployment docs
├── docker-compose.yml
├── .env.example
└── Makefile
```

---

## Quick Start

### Prerequisites
- Docker + Docker Compose v2
- Node.js 20+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

### 1. Clone & Configure

```bash
git clone https://github.com/your-org/SIH-26034.git
cd SIH-26034
cp .env.example .env
# Edit .env with your secrets
```

### 2. Run with Docker

```bash
make up
```

Services will be available at:
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Database:** localhost:5432

### 3. Local Development

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -m app.main
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## Default Credentials (Development)

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@legalmetrology.gov.in | Admin@123 |
| Inspector | inspector@legalmetrology.gov.in | Inspector@123 |
| Viewer | viewer@legalmetrology.gov.in | Viewer@123 |

> ⚠️ Change all passwords before any production deployment.

---

## Implementation Phases

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ **Complete** | Skeleton, auth, DB models, dashboard, inspection CRUD |
| Phase 2 | 🔲 Planned | PaddleOCR integration |
| Phase 3 | 🔲 Planned | Declaration extraction |
| Phase 4 | 🔲 Planned | Full rule engine evaluation |
| Phase 5 | 🔲 Planned | Visual evidence & bounding boxes |
| Phase 6 | 🔲 Planned | Font size / readability analysis |
| Phase 7 | 🔲 Planned | RAG / legal knowledge base (LLM assistance only) |
| Phase 8 | 🔲 Planned | PDF / DOCX report generation |
| Phase 9 | 🔲 Planned | Full Dockerization & deployment |

---

## Documentation

- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [AI Module README](ai/README.md)
- [Rule Engine README](rule-engine/README.md)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Tailwind CSS, Vite, Zustand, Recharts |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 |
| AI/CV | OpenCV, PaddleOCR (Phase 2+), NumPy |
| Database | PostgreSQL 15, Redis (caching) |
| Auth | JWT (python-jose), bcrypt |
| Reports | WeasyPrint (PDF), python-docx (DOCX) — Phase 8 |
| DevOps | Docker, Docker Compose |

---

## Legal Reference

Legal Metrology (Packaged Commodities) Rules, 2011 — Government of India  
Department of Consumer Affairs, Ministry of Consumer Affairs, Food & Public Distribution