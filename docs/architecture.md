# System Architecture — Legal Metrology Inspection System (SIH-26034)

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                                 │
│  Browser (React 18 + TypeScript + Tailwind + Vite)             │
│  Pages: Login | Dashboard | Inspections | Products | Rules     │
│         New Inspection | Inspection Detail | Settings          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS / REST / JSON
                           │ JWT Bearer Token
┌──────────────────────────▼──────────────────────────────────────┐
│                    API GATEWAY LAYER                            │
│  FastAPI (Python 3.11) — Uvicorn / Gunicorn                    │
│  CORS | Rate Limiting | Request Validation | Error Handling     │
└────────┬───────────────────────────────┬────────────────────────┘
         │                               │
┌────────▼────────┐             ┌────────▼────────────────────────┐
│  Auth Service   │             │       Business Services         │
│  JWT / RBAC     │             │  InspectionService              │
│  Roles:         │             │  ProductService                 │
│  ADMIN          │             │  RuleService                    │
│  INSPECTOR      │             │  ReportService                  │
│  VIEWER         │             └────────┬────────────────────────┘
└────────┬────────┘                      │
         │                     ┌────────▼────────────────────────┐
         │                     │       AI PIPELINE               │
         │                     │  ┌─────────────────────────┐   │
         │                     │  │ 1. Image Preprocessor   │   │
         │                     │  │    (OpenCV)             │   │
         │                     │  ├─────────────────────────┤   │
         │                     │  │ 2. OCR Engine           │   │
         │                     │  │    (PaddleOCR — Ph.2)   │   │
         │                     │  ├─────────────────────────┤   │
         │                     │  │ 3. Declaration Extractor│   │
         │                     │  │    (Ph.3)               │   │
         │                     │  ├─────────────────────────┤   │
         │                     │  │ 4. Rule Engine          │   │
         │                     │  │    (Deterministic)      │   │
         │                     │  ├─────────────────────────┤   │
         │                     │  │ 5. LLM/RAG Assistant    │   │
         │                     │  │    (Legal explanations) │   │
         │                     │  │    [Ph.7 — NOT decision │   │
         │                     │  │     maker]              │   │
         │                     │  └─────────────────────────┘   │
         │                     │  ⚠ Phase 1: STUB pipeline      │
         │                     └────────┬────────────────────────┘
         │                              │
┌────────▼──────────────────────────────▼────────────────────────┐
│                    DATA LAYER                                   │
│  PostgreSQL 15       │  Redis 7                                │
│  (Primary store)     │  (Session cache, rate limiting)         │
│  SQLAlchemy 2 ORM    │                                         │
│  Alembic Migrations  │                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. AI Pipeline Design Principle

> **The LLM is NOT the legal decision-maker.**

```
Image
  │
  ▼ Image Preprocessing (OpenCV)
  │  - Noise reduction, contrast enhancement
  │  - Perspective correction, deskewing
  │  - ROI detection
  │
  ▼ OCR Engine (PaddleOCR — Phase 2)
  │  - Text detection + recognition
  │  - Bounding box extraction
  │  - Confidence scores per text region
  │
  ▼ Declaration Extractor (Phase 3)
  │  - Named entity recognition for declarations
  │  - Field mapping: MRP, net qty, manufacturer, etc.
  │  - Structured JSON output
  │
  ▼ Deterministic Rule Engine (Phase 4)
  │  - JSON-driven rules (Legal Metrology Rules 2011)
  │  - COMPLIANT / NON_COMPLIANT / WARNING / NEEDS_REVIEW
  │  - Every result has confidence score
  │  - Below threshold → "Human verification recommended"
  │
  ▼ Compliance Result
  │  - Structured violations list
  │  - Legal references
  │  - Evidence bounding boxes
  │
  ▼ LLM/RAG (Phase 7 — assistance only)
     - Natural language explanation of violations
     - Legal provision retrieval (RAG from knowledge base)
     - NOT used for compliance decisions
```

---

## 3. Database Schema

### Entity Relationship Diagram

```
users
  id, email, hashed_password, full_name, role, is_active
  created_at, updated_at, last_login

products
  id, name, category, brand, barcode, description
  manufacturer_name, manufacturer_address
  created_by_id → users.id
  created_at, updated_at

inspections
  id, inspection_number, status, overall_compliance_status
  product_id → products.id
  inspector_id → users.id
  ai_pipeline_status, ai_confidence_score
  remarks, started_at, completed_at
  created_at, updated_at

inspection_images
  id, inspection_id → inspections.id
  image_path, label (FRONT/BACK/SIDE/TOP/BOTTOM)
  original_filename, file_size, mime_type
  processing_status, processed_at
  created_at

declarations
  id, inspection_id → inspections.id
  image_id → inspection_images.id
  field_name, field_value, raw_text
  confidence_score, bounding_box (JSON)
  extraction_method, is_verified
  created_at

violations
  id, inspection_id → inspections.id
  rule_id → rules.id
  declaration_id → declarations.id
  severity (HIGH/MEDIUM/LOW/INFO)
  status (OPEN/ACKNOWLEDGED/RESOLVED/FALSE_POSITIVE)
  description, legal_reference
  evidence_region (JSON)
  created_at

rules
  id, rule_id (unique code), field, category
  mandatory, severity, description
  validation_logic (JSON), legal_reference
  rule_version, is_active
  created_at, updated_at

reports
  id, inspection_id → inspections.id
  report_type (PDF/DOCX), file_path
  generated_by_id → users.id
  generation_status, generated_at
  created_at
```

---

## 4. API Design

Base URL: `http://localhost:8000/api/v1`

### Authentication
```
POST /auth/login          → Access + Refresh tokens
POST /auth/refresh        → New access token
POST /auth/logout         → Invalidate refresh token
GET  /auth/me             → Current user profile
```

### Inspections
```
GET    /inspections               → List (paginated, filterable)
POST   /inspections               → Create new inspection
GET    /inspections/:id           → Get inspection detail
PUT    /inspections/:id           → Update inspection
DELETE /inspections/:id           → Delete (ADMIN only)
POST   /inspections/:id/images    → Upload image(s)
POST   /inspections/:id/analyze   → Trigger AI analysis
GET    /inspections/:id/report    → Get/generate report
```

### Products
```
GET    /products          → List products
POST   /products          → Create product
GET    /products/:id      → Get product
PUT    /products/:id      → Update product
DELETE /products/:id      → Delete (ADMIN only)
```

### Rules
```
GET    /rules             → List rules
GET    /rules/:id         → Get rule
POST   /rules             → Create rule (ADMIN)
PUT    /rules/:id         → Update rule (ADMIN)
```

### Reports
```
GET    /reports                   → List reports
POST   /reports/generate          → Generate PDF/DOCX
GET    /reports/:id/download      → Download file
```

### Dashboard
```
GET    /dashboard/stats           → Summary statistics
GET    /dashboard/recent          → Recent inspections
GET    /dashboard/violations      → Top violation types
GET    /dashboard/trend           → Inspection trend data
```

---

## 5. Role-Based Access Control

| Resource | ADMIN | INSPECTOR | VIEWER |
|----------|-------|-----------|--------|
| View dashboard | ✅ | ✅ | ✅ |
| View inspections | ✅ | ✅ | ✅ |
| Create inspection | ✅ | ✅ | ❌ |
| Edit own inspection | ✅ | ✅ | ❌ |
| Delete inspection | ✅ | ❌ | ❌ |
| Upload images | ✅ | ✅ | ❌ |
| Trigger AI analysis | ✅ | ✅ | ❌ |
| View products | ✅ | ✅ | ✅ |
| Manage products | ✅ | ✅ | ❌ |
| View rules | ✅ | ✅ | ✅ |
| Manage rules | ✅ | ❌ | ❌ |
| Generate reports | ✅ | ✅ | ✅ |
| Manage users | ✅ | ❌ | ❌ |

---

## 6. Security Considerations

- JWT access tokens expire in 30 minutes
- Refresh tokens expire in 7 days (stored securely)
- Passwords hashed with bcrypt (cost factor 12)
- File uploads validated: type, size, content
- SQL injection prevented via ORM parameterized queries
- XSS prevention via Pydantic validation + CSP headers
- CORS restricted to allowed origins
- Rate limiting on auth endpoints (10 req/minute)
- Uploaded images stored outside webroot

---

## 7. Deployment Architecture (Phase 9)

```
Internet
   │
   ▼
Nginx (Reverse Proxy + SSL termination)
   │
   ├─► Frontend (Static files or Next.js SSR)
   │
   └─► Backend (FastAPI via Gunicorn + Uvicorn workers)
            │
            ├─► PostgreSQL (Primary + Read replica)
            ├─► Redis (Sentinel cluster)
            └─► Object Storage (MinIO / S3 for images)
```
