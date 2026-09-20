# AI Module — Legal Metrology Inspection System

## Overview

This module contains the Computer Vision and Multimodal AI extraction pipeline for extracting mandatory declarations and spatial text regions from packaged commodity images.

- **Active Engine:** `VisionPipeline` (`ai/pipeline/vision_pipeline.py`) utilizing Google Gemini Vision (`google-genai` SDK, `gemini-2.5-flash` or `gemini-3.5-flash-lite`).
- **Offline / Dev Fallback:** `StubPipeline` (`ai/pipeline/stub_pipeline.py`) for development and air-gapped testing.
- **Planned Local Alternative:** On-premise OCR using PaddleOCR is planned for air-gapped deployments where external image transmission is restricted.

---

## Pipeline Architecture

```
Package Image File
    │
    ▼ VisionPipeline.analyze(image_path, image_id)
    │  - Format detection (JPEG, PNG, WebP, TIFF)
    │  - Reads image bytes
    │
    ▼ Google Gemini Vision (google-genai SDK)
    │  - Model: gemini-2.5-flash (configurable via VISION_MODEL)
    │  - Structured JSON schema enforcement (PackageLabelAnalysis)
    │  - Zero-hallucination policy: missing declarations return null with confidence 0.0
    │  - Returns bounding boxes [x1, y1, x2, y2] for declarations & OCR text regions
    │
    ▼ Domain-Specific Normalizers (ai/pipeline/vision_pipeline.py)
    │  - normalize_mrp(): Currency symbol stripping (₹, Rs., INR) → clean numeric float
    │  - normalize_quantity(): Net quantity parsing → {amount: float, unit: str} with SI unit mapping
    │  - normalize_date(): Date normalization → ISO 8601 (YYYY-MM-DD) or flags ambiguous dates
    │
    ▼ PipelineResult
       - Structured declarations with bounding boxes & confidence scores
       - OCR text regions with spatial coordinates
       - Consumed by the deterministic RuleEngine (rule-engine/engine.py)
```

---

## Current Implementation Status

| Component | Status | Phase | Details |
|-----------|--------|-------|---------|
| `VisionPipeline` | ✅ **Complete** | Phase 2 | Real vision extraction via Google Gemini Vision (`gemini-2.5-flash`) |
| Structured Extraction Schema | ✅ **Complete** | Phase 3 | Pydantic `PackageLabelAnalysis` extracting 11+ statutory declarations |
| Normalization Utilities | ✅ **Complete** | Phase 3 | `normalize_mrp`, `normalize_quantity`, `normalize_date` |
| `StubPipeline` | ✅ **Complete** | Phase 1 | Offline/dev fallback (`DEV_STUB`, flags `NEEDS_REVIEW`) |
| Visual Evidence Coordinates | ✅ **Complete** | Phase 5 | Bounding boxes stored in DB and displayed on frontend canvas |
| Font Size Calibration | 🟡 **In Progress** | Phase 6 | `FONT-001` rule implemented; physical mm calibration against DPI/distance pending |
| RAG / LLM Assistant | 🔲 Planned | Phase 7 | Natural language statutory guidance (NOT decision-maker) |
| `PaddleOCREngine` | 🔲 Planned | Future | Local / air-gapped on-premise alternative |

---

## External Gemini Dependency & Network Behavior

1. **API Key Requirement:**
   The real extraction pipeline requires a valid `GEMINI_API_KEY` set in your `.env` file and configured in `app.core.config.settings`.
2. **Network Transmission:**
   Image bytes are transmitted over HTTPS to Google's Generative Language API endpoint (`generativelanguage.googleapis.com`). Ensure outbound HTTPS access is permitted by your firewall.
3. **Missing Key or Network Failure:**
   - When `AI_PIPELINE_MODE=vision`, network interruptions or invalid keys cause `VisionPipeline` to raise an exception, which the backend catches and surfaces as an `HTTP 502 Bad Gateway` error while updating inspection status to `FAILED`.
   - When `AI_PIPELINE_MODE=stub`, the system runs completely offline via `StubPipeline`, returning `pipeline_status="DEV_STUB"` and setting overall compliance to `NEEDS_REVIEW` to ensure that placeholder data is never mistaken for compliance.

---

## Mandatory Declared Fields Extracted

The extraction pipeline captures 11+ declaration fields defined by the Legal Metrology (Packaged Commodities) Rules, 2011:

| Field Name | Legal Metrology Declaration | Statutory Reference |
|------------|----------------------------|---------------------|
| `commodity_name` | Generic / Common Name of Commodity | Rule 6(1)(a) |
| `net_quantity` | Net Quantity (Weight, Measure, or Number) | Rule 6(1)(b) |
| `manufacturer_name` | Name of Manufacturer / Packer / Importer | Rule 6(1)(c) |
| `manufacturer_address` | Complete Address of Manufacturer / Packer | Rule 6(1)(c) |
| `manufacturing_date` | Month and Year of Manufacture / Packing | Rule 6(1)(e) |
| `best_before_date` | Expiry / Best Before Date (if applicable) | Rule 6(1)(e) proviso |
| `mrp` | Maximum Retail Price (inclusive of all taxes) | Rule 6(1)(f) |
| `consumer_care_info` | Name, Address, Phone, Email for Complaints | Rule 6(1)(l) |
| `country_of_origin` | Country of Origin (for imported commodities) | Rule 6(1)(k) |
| `batch_number` | Batch / Lot / Code Number | Rule 6(1)(g) / FSSAI |
| `unit_sale_price` | Unit Sale Price (per g/ml/piece where applicable) | Rule 6(1)(n) |

---

## Design Principle

> **The AI pipeline is NEVER the legal decision-maker.**
>
> The AI pipeline acts purely as a sensory extraction layer, translating raw packaging pixels into structured declaration data and bounding box coordinates.
> All compliance decisions (`COMPLIANT`, `NON_COMPLIANT`, `WARNING`, `NEEDS_REVIEW`) are made exclusively by the **deterministic rule engine** in `/rule-engine/engine.py`.
> An LLM never adjudicates whether a product complies with Indian law.

---

## Requirements

```
# Multimodal extraction dependencies
google-genai>=1.0.0
pydantic>=2.0.0
Pillow>=10.0.0
numpy>=1.26.0
```
