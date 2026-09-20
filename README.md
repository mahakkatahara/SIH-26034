# SIH-26034 — AI-Powered Legal Metrology Compliance Inspection System

> **Smart India Hackathon 2026 | Problem Statement 26034**  
> Ministry of Consumer Affairs, Food & Public Distribution — Legal Metrology Division

---

## Overview

A production-quality web application for enforcement officials to:

- Upload and scan images of packaged commodities
- Extract mandatory declarations and bounding boxes from package labels using multimodal Vision AI (Google Gemini Vision)
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
  ├─ AI Pipeline (Gemini Vision / Stub Fallback)
  │    ├─ Gemini Vision Client (google-genai / gemini-2.5-flash)
  │    │    ├─ Structured Declaration Extractor
  │    │    └─ OCR Region & Bounding Box Detector
  │    ├─ Value Normalizers (MRP, Net Qty, Dates)
  │    └─ Offline/Dev Fallback (StubPipeline / Planned PaddleOCR)
  ├─ Rule Engine (deterministic, data-driven, rules.json)
  └─ Report Generator (PDF / DOCX — Phase 8 stub)
        │
        ▼
PostgreSQL (SQLAlchemy + Alembic)
```

**Design Principle:** The AI/LLM is NEVER the legal decision-maker.  
Pipeline: Image → Gemini Vision Extraction (Text & Bounding Boxes) → Normalization → Deterministic Rule Engine (`rule-engine/engine.py`) → Statutory Compliance Result  

Gemini Vision acts purely as an extraction engine, converting visual package labels into structured JSON declarations and spatial bounding boxes. The deterministic rule engine strictly executes the statutory requirements of the Legal Metrology (Packaged Commodities) Rules, 2011 to determine compliance (`COMPLIANT`, `NON_COMPLIANT`, `WARNING`, or `NEEDS_REVIEW`). An LLM never adjudicates compliance. LLM/RAG is planned only for natural language assistance and legal provision explanation (Phase 7).

### AI Pipeline & External Dependencies

- **Primary Vision Engine:** Google Gemini Vision via `google-genai` SDK (`gemini-2.5-flash` or `gemini-3.5-flash-lite`).
- **Network & API Key:** Requires outbound internet access to Google's Generative AI API and a valid `GEMINI_API_KEY` configured in `.env`.
- **Data Transmission:** When `AI_PIPELINE_MODE=vision`, package label image bytes are sent externally to Google's API for extraction.
- **Offline / Stub Fallback:** When `AI_PIPELINE_MODE=stub` (or in air-gapped environments without API access), the system uses `StubPipeline`, returning `pipeline_status="DEV_STUB"` and downgrading overall status to `NEEDS_REVIEW` to safeguard statutory integrity. If `AI_PIPELINE_MODE=vision` and the API or network fails, the backend returns `HTTP 502 Bad Gateway`.
- **Local/Offline Alternative (Planned):** On-premise OCR using PaddleOCR is planned for fully air-gapped local deployments without external network access.

---

## Project Structure

```
SIH-26034/
├── frontend/       # React + TypeScript + Tailwind (Vite)
├── backend/        # FastAPI + SQLAlchemy + Alembic
├── ai/             # Gemini Vision pipeline & normalizers (offline stub fallback)
├── rule-engine/    # Deterministic JSON-driven compliance rule engine
├── database/       # Schema SQL & migrations
├── reports/        # PDF / DOCX generation (Phase 8)
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
git clone https://github.com/Aarav-Jainn/SIH-26034.git
cd SIH-26034
cp .env.example .env
# Edit .env with your secrets, including GEMINI_API_KEY
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
| Phase 1 | ✅ **Complete** | Skeleton, auth, DB models, dashboard, inspection CRUD, Alembic migrations baseline & automated schema drift tests |
| Phase 2 | 🟡 **In Progress** | Cloud multimodal OCR & text region extraction operational via Gemini Vision (`google-genai`); local offline OCR engine (PaddleOCR) pending for air-gapped deployments |
| Phase 3 | 🟡 **In Progress** | Structured declaration extraction (`PackageLabelAnalysis`), value normalizers (MRP, units, dates), multi-image reconciliation, and degenerate bounding box rejection operational; label orientation auto-correction pending |
| Phase 4 | ✅ **Complete** | Deterministic rule engine (`rule-engine/engine.py`): presence, format regex, legal units, conditional checks, Rule 24 wholesale scoping, decoupled confidence gates |
| Phase 5 | 🟡 **In Progress** | Visual evidence & bounding boxes: JSONB storage, degenerate box rejection, and interactive canvas bounding box overlay viewer functional; image aspect/resolution coordinate auto-scaling in progress |
| Phase 6 | 🟡 **In Progress** | Font size analysis: rule check (`FONT-001`) stubbed as `NOT_APPLICABLE` pending optical physical mm calibration against camera DPI and distance |
| Phase 7 | 🔲 Planned | RAG / legal knowledge base (LLM assistance only — not legal decision-maker) |
| Phase 8 | 🔲 Planned | PDF / DOCX report generation (API endpoint operational with stub notice; WeasyPrint/python-docx generation pending) |
| Phase 9 | ✅ **Complete** | Multi-container Docker Compose deployment (backend, frontend, PostgreSQL, Redis) with health checks & seed scripts |

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
| AI/CV | Google Gemini Vision (`google-genai`, `gemini-2.5-flash`), OpenCV, NumPy (PaddleOCR planned as offline alternative) |
| Rule Engine | Deterministic Python engine (`rule-engine/engine.py`), JSON-driven rules (`rules.json`) |
| Database | PostgreSQL 15, Redis 7 (caching) |
| Auth | JWT (python-jose), bcrypt |
| Reports | WeasyPrint (PDF), python-docx (DOCX) — Phase 8 |
| DevOps | Docker, Docker Compose |

---

## Legal Reference

Legal Metrology (Packaged Commodities) Rules, 2011 — Government of India  
Department of Consumer Affairs, Ministry of Consumer Affairs, Food & Public Distribution