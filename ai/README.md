# AI Module — Legal Metrology Inspection System

## Overview

This module contains the AI/Computer Vision pipeline for extracting and
analyzing declarations from packaged commodity images.

## Pipeline Architecture

```
Image File
    │
    ▼ BasePreprocessor (ai/pipeline/base.py)
    │  - Noise reduction
    │  - Deskewing / perspective correction
    │  - Contrast enhancement
    │  - ROI detection
    │
    ▼ BaseOCREngine (ai/pipeline/base.py)
    │  - Text detection (bounding boxes)
    │  - Text recognition
    │  - Confidence scores per region
    │
    ▼ BaseExtractor (ai/pipeline/base.py)
    │  - Map OCR text → structured declarations
    │  - Field: mrp, net_quantity, manufacturer_name, etc.
    │  - Normalize values (currency, units, dates)
    │
    ▼ PipelineResult
       - Passed to rule engine (in backend service layer)
       - Rule engine is DETERMINISTIC (not AI)
```

## Current Implementation Status

| Component | Status | Phase |
|-----------|--------|-------|
| `StubPipeline` | ✅ Available | Phase 1 |
| `OpenCVPreprocessor` | 🔲 Planned | Phase 2 |
| `PaddleOCREngine` | 🔲 Planned | Phase 2 |
| `RegexExtractor` | 🔲 Planned | Phase 3 |
| Font size analysis | 🔲 Planned | Phase 6 |
| RAG / LLM assistant | 🔲 Planned | Phase 7 |

## Phase 1 — Stub

The `StubPipeline` in `pipeline/stub_pipeline.py` returns a clearly marked
`DEV_STUB` result with no real analysis. Every stub result includes:

```python
PipelineResult(
    pipeline_status="DEV_STUB",
    notice="⚠ AI PIPELINE NOT IMPLEMENTED ...",
    declarations=[],
    ocr_regions=[],
)
```

## Implementing Phase 2 (PaddleOCR)

To integrate PaddleOCR:

1. Implement `BaseOCREngine` in `pipeline/ocr_engine.py`
2. Implement `BasePreprocessor` in `pipeline/preprocessor.py`
3. Create `PaddleOCRPipeline(BasePipeline)` in `pipeline/paddleocr_pipeline.py`
4. Update `get_pipeline()` in `stub_pipeline.py` to return the new pipeline
5. Set `AI_PIPELINE_MODE=paddleocr` in `.env`

### Interface Contract

```python
class MyOCREngine(BaseOCREngine):
    def recognize(self, image: np.ndarray) -> List[OCRTextRegion]:
        # image is BGR numpy array from OpenCV
        # return list of OCRTextRegion with text + bounding_box + confidence
        ...
```

## Declared Fields

The extraction pipeline targets these mandatory declaration fields:

| field_name | Legal Metrology Field | Rule |
|------------|-----------------------|------|
| `mrp` | Maximum Retail Price | Rule 6(1)(f) |
| `net_quantity` | Net Quantity | Rule 6(1)(b) |
| `manufacturer_name` | Manufacturer/Packer Name | Rule 6(1)(c) |
| `manufacturer_address` | Manufacturer Address | Rule 6(1)(c) |
| `manufacturing_date` | Date of Manufacturing/Packing | Rule 6(1)(e) |
| `consumer_care_info` | Consumer Care Contact | Rule 6(1)(l) |
| `country_of_origin` | Country of Origin | Rule 6(1)(k) |

## Design Principle

> **The AI pipeline is NOT the legal decision-maker.**
> 
> The pipeline outputs structured `PipelineResult` data.
> The **deterministic rule engine** (in `/rule-engine/`) makes compliance decisions.
> LLM/RAG (Phase 7) is used only for natural-language explanation of violations.

## Requirements

```
# Phase 2+ requirements (not needed for Phase 1 stub)
paddlepaddle>=2.6.0
paddleocr>=2.7.0
opencv-python>=4.9.0
numpy>=1.26.0
Pillow>=10.0.0
```
