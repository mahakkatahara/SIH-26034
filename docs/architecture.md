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
          │                     │  │ 1. Vision Engine        │   │
          │                     │  │    (Gemini 2.5 Flash)   │   │
          │                     │  ├─────────────────────────┤   │
          │                     │  │ 2. Structured Extraction│   │
          │                     │  │    & Bounding Boxes     │   │
          │                     │  ├─────────────────────────┤   │
          │                     │  │ 3. Value Normalizers    │   │
          │                     │  │    (MRP, Units, Dates)  │   │
          │                     │  ├─────────────────────────┤   │
          │                     │  │ 4. Deterministic Rule   │   │
          │                     │  │    Engine (rules.json)  │   │
          │                     │  ├─────────────────────────┤   │
          │                     │  │ 5. Offline/Stub Fallback│   │
          │                     │  │    (StubPipeline)       │   │
          │                     │  └─────────────────────────┘   │
          │                     │  [Planned: Local PaddleOCR]     │
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

> **The AI/LLM is NEVER the legal decision-maker.**
>
> Google Gemini Vision acts strictly as an extraction instrument to perceive text and bounding boxes from packaging images.
> The deterministic rule engine (`rule-engine/engine.py`) evaluates the extracted data against statutory provisions to make all legal compliance determinations.
> LLM/RAG (Phase 7) is reserved exclusively for natural language assistance and legal provision explanation.

```
Package Image File
  │
  ▼ Image Validation & Format Handling
  │  - Supported MIME formats (JPEG, PNG, WebP, TIFF)
  │  - Candidate path resolution & validation
  │
  ▼ Multimodal Extraction — Google Gemini Vision (google-genai SDK)
  │  - Active Model: gemini-2.5-flash (configurable to gemini-3.5-flash-lite)
  │  - Constrained JSON Schema: PackageLabelAnalysis
  │  - Extracts 11+ legal fields: value, raw_text, confidence, bounding_box [x1, y1, x2, y2]
  │  - Detects OCR text regions across package panels
  │  - Missing declaration policy: value=null, confidence=0.0 (strictly no hallucination)
  │
  ▼ Domain-Specific Value Normalization (ai/pipeline/vision_pipeline.py)
  │  - normalize_mrp: Currency symbol strip (₹, Rs., INR) & numeric float conversion
  │  - normalize_quantity: Amount float & canonical unit mapping (gm/g -> g, ltr/l -> l)
  │  - normalize_date: ISO 8601 (YYYY-MM-DD) normalization or ambiguous date flagging
  │
  ▼ Deterministic Rule Engine (rule-engine/engine.py)
  │  - Data-driven statutory evaluation against Legal Metrology (PC) Rules, 2011
  │  - presence_check: Mandatory declaration presence per Rule 6(1)
  │  - format_check: Syntax & regex pattern validation
  │  - unit_check: Second/Third Schedule measurement units (UNIT_NORMALIZATION_MAP)
  │  - conditional_check: Context-dependent rules (e.g. import origin Rule 6(1)(k))
  │  - wholesale_scoping: Rule 24 exemption evaluation for wholesale packages
  │  - font_size_check: PDP font size verification (FONT-001)
  │  - single-panel protection: Missing >= 3 declarations downgrades to NEEDS_REVIEW
  │
  ▼ Statutory Compliance Result
  │  - Status: COMPLIANT | NON_COMPLIANT | WARNING | NEEDS_REVIEW
  │  - Structured violations with rule_id, observed_value, expected, legal_reference
  │  - Bounding box coordinates for visual evidence overlay
  │
  ▼ LLM / RAG (Phase 7 — Natural Language Assistance Only)
     - Explains complex statutory violations in plain language for enforcement officers
     - Retrieves relevant case law and gazette notifications from knowledge base
     - Strictly excluded from compliance decision-making
```

### External AI Dependency & Operational Modes

- **External Network Dependency:**
  The real extraction pipeline invokes Google's Gemini Vision API via HTTPS. When active (`AI_PIPELINE_MODE=vision`), package label image bytes are transmitted externally to Google's endpoints for multimodal processing. An active outbound internet connection and `GEMINI_API_KEY` configured in `.env` are required.
- **Offline / Development Fallback (`AI_PIPELINE_MODE=stub`):**
  If `GEMINI_API_KEY` is omitted or `AI_PIPELINE_MODE=stub`, the system routes to `StubPipeline`. To prevent incorrect enforcement actions, the stub marks results with `pipeline_status="DEV_STUB"` and sets overall compliance to `NEEDS_REVIEW`.
- **API Failure Handling:**
  If network connectivity is lost or Gemini API returns an unrecoverable error during active inspection, the backend returns `HTTP 502 Bad Gateway` and marks the inspection pipeline status as `FAILED`.
- **Local/Offline Alternative (Planned):**
  For high-security air-gapped deployments where external image transmission is prohibited, a local on-premise pipeline using PaddleOCR is planned.

### Model Self-Reported Confidence Calibration & Safeguards

Modern multimodal LLMs like Google Gemini Vision do not natively emit true Bayesian or frequentist probability distributions for extraction tasks. Instead, Gemini outputs self-reported confidence scores (or verbalized confidences) requested via prompt formatting. In practice, this exhibits distinct characteristics and operational risks that our architecture explicitly mitigates:

1. **Overconfidence Tendency:**
   Multimodal foundation models are prone to overconfidence on clear text segments, typically self-reporting $\ge 0.95$ (often $0.98$–$0.99$) even when slight OCR character misrecognitions or field misattributions occur. Conversely, when text is inverted, blurred, or occluded, the model may either fail to detect the field altogether (returning `value: null, confidence: 0.0`) or output degraded text.

2. **Decoupling Confidence from Completeness (Coverage):**
   A critical defect in naive extraction pipelines is conflating *extraction confidence* (how sure the model is about the text it read) with *inspection coverage* (how many mandatory statutory fields were detected).
   - If an inspector photographs only one panel containing 3 declarations (MRP, net quantity, unit sale price), the vision model extracts all 3 with ~0.93 confidence.
   - If missing fields (confidence 0.0) are averaged into the mean, the system spuriously reports 0.25 overall confidence, obscuring the fact that the 3 extracted fields were parsed with high fidelity.
   - **Architectural Safeguard:** Mean extraction confidence is computed **exclusively over extracted fields** (`confidence > 0.0` and non-empty value). Inspection completeness is measured independently as `fields_extracted` / `total_mandatory_fields` (coverage ratio).

3. **Two Distinct `NEEDS_REVIEW` Failure Modes:**
   The deterministic rule engine distinguishes two completely different operational problems for enforcement officers:
   - **Incomplete Inspection (Missing Panels):** Triggered when $\ge 3$ mandatory fields are absent (`absent_mandatory_count >= 3`). The package is not declared non-compliant; instead, the officer is instructed to capture photos of the remaining package panels (e.g. front PDP, side panel).
   - **Low Extraction Confidence (Poor Image Quality):** Triggered when mean confidence over extracted fields falls below `AI_CONFIDENCE_THRESHOLD` (default 0.75). The officer is alerted that the photo is blurry, low-resolution, or glare-affected, requiring a clearer rescan.

4. **Multi-Image Reconciliation & Provenance:**
   When an inspection contains multiple images (e.g. front, back, sides), declarations are reconciled deterministically per field:
   - The highest-confidence declaration wins.
   - Absent (null / 0.0 confidence) declarations from subsequent panels never overwrite an already-extracted declaration.
   - Equal-confidence ties are broken deterministically by favoring more descriptive text (longer character length) and first-observed occurrence.
   - Full provenance is preserved, tagging each winning declaration with its source `image_id` and package `panel`.

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
