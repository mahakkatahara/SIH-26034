# API Reference — Legal Metrology Inspection System

Base URL: `http://localhost:8000/api/v1`

All endpoints require `Authorization: Bearer <access_token>` unless marked `[PUBLIC]`.

---

## Authentication

### POST /auth/login `[PUBLIC]`
Login and receive tokens.

**Request:**
```json
{ "email": "admin@legalmetrology.gov.in", "password": "Admin@123" }
```

**Response 200:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "uuid",
    "email": "admin@legalmetrology.gov.in",
    "full_name": "System Administrator",
    "role": "ADMIN"
  }
}
```

### POST /auth/refresh
Refresh access token using refresh token.

### GET /auth/me
Get current authenticated user profile.

---

## Inspections

### GET /inspections
List inspections with filtering and pagination.

**Query params:** `page`, `size`, `status`, `compliance_status`, `product_id`, `inspector_id`, `date_from`, `date_to`, `search`

**Response 200:**
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "size": 20,
  "pages": 8
}
```

### POST /inspections
Create a new inspection.

**Request:**
```json
{
  "product_id": "uuid",
  "remarks": "Field inspection — market survey"
}
```

### POST /inspections/{id}/images
Upload image(s) for an inspection. `multipart/form-data`

**Fields:** `images` (multiple files), `label` (FRONT|BACK|SIDE|TOP|BOTTOM)

### POST /inspections/{id}/analyze
Trigger AI analysis pipeline on uploaded images.

**Response 200:**
```json
{
  "inspection_id": "uuid",
  "pipeline_status": "DEV_STUB",
  "notice": "⚠ AI pipeline not yet implemented. This is a Phase 1 development stub.",
  "declarations": [],
  "violations": [],
  "overall_compliance_status": "NEEDS_REVIEW"
}
```

---

## Dashboard

### GET /dashboard/stats
```json
{
  "total_inspections": 523,
  "compliant": 341,
  "non_compliant": 127,
  "needs_review": 55,
  "compliance_percentage": 65.2,
  "total_violations": 389,
  "inspections_this_month": 47
}
```

### GET /dashboard/trend
Returns inspection counts grouped by date for charting.

---

## Rules

### GET /rules
List all compliance rules.

**Response item:**
```json
{
  "rule_id": "MRP-001",
  "field": "mrp",
  "mandatory": true,
  "severity": "HIGH",
  "description": "Maximum Retail Price must be declared on the package",
  "legal_reference": "Rule 6(1)(f) - Legal Metrology (PC) Rules 2011",
  "rule_version": "1.0",
  "is_active": true
}
```

---

## Error Responses

All errors follow:
```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE",
  "timestamp": "2026-09-13T19:00:00Z"
}
```

| Status | Meaning |
|--------|---------|
| 400 | Validation error |
| 401 | Not authenticated |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 422 | Request body validation failed |
| 500 | Internal server error |
