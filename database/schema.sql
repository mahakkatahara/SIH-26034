-- =============================================================================
-- Legal Metrology Inspection System — Reference Database Schema
-- Generated for: PostgreSQL 15+
-- Note: Alembic manages actual migrations. This file is for reference/Docker init.
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- ENUMS
-- =============================================================================

CREATE TYPE user_role AS ENUM ('ADMIN', 'INSPECTOR', 'VIEWER');

CREATE TYPE inspection_status AS ENUM (
    'DRAFT', 'IN_PROGRESS', 'ANALYSIS_PENDING', 
    'ANALYSIS_COMPLETE', 'COMPLETED', 'CANCELLED'
);

CREATE TYPE compliance_status AS ENUM (
    'COMPLIANT', 'NON_COMPLIANT', 'WARNING', 'NEEDS_REVIEW', 'PENDING'
);

CREATE TYPE image_label AS ENUM (
    'FRONT', 'BACK', 'SIDE', 'TOP', 'BOTTOM', 'OTHER'
);

CREATE TYPE processing_status AS ENUM (
    'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'STUB'
);

CREATE TYPE pipeline_status AS ENUM (
    'NOT_STARTED', 'PREPROCESSING', 'OCR', 'EXTRACTION', 
    'RULE_CHECK', 'COMPLETED', 'FAILED', 'DEV_STUB'
);

CREATE TYPE violation_severity AS ENUM ('HIGH', 'MEDIUM', 'LOW', 'INFO');

CREATE TYPE violation_status AS ENUM (
    'OPEN', 'ACKNOWLEDGED', 'RESOLVED', 'FALSE_POSITIVE'
);

CREATE TYPE report_type AS ENUM ('PDF', 'DOCX');

CREATE TYPE report_status AS ENUM (
    'PENDING', 'GENERATING', 'COMPLETED', 'FAILED', 'STUB'
);

-- =============================================================================
-- TABLES
-- =============================================================================

-- Users
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    role            user_role NOT NULL DEFAULT 'INSPECTOR',
    employee_id     VARCHAR(100),
    department      VARCHAR(255),
    phone           VARCHAR(20),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_login      TIMESTAMP WITH TIME ZONE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- Products
CREATE TABLE IF NOT EXISTS products (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                 VARCHAR(500) NOT NULL,
    category             VARCHAR(255),
    brand                VARCHAR(255),
    barcode              VARCHAR(100),
    description          TEXT,
    manufacturer_name    VARCHAR(500),
    manufacturer_address TEXT,
    country_of_origin    VARCHAR(100),
    created_by_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_products_barcode ON products(barcode);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_name ON products USING gin(to_tsvector('english', name));

-- Inspections
CREATE TABLE IF NOT EXISTS inspections (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    inspection_number       VARCHAR(50) UNIQUE NOT NULL,
    status                  inspection_status NOT NULL DEFAULT 'DRAFT',
    overall_compliance_status compliance_status NOT NULL DEFAULT 'PENDING',
    product_id              UUID REFERENCES products(id) ON DELETE RESTRICT,
    inspector_id            UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    ai_pipeline_status      pipeline_status NOT NULL DEFAULT 'NOT_STARTED',
    ai_confidence_score     FLOAT,
    remarks                 TEXT,
    location                VARCHAR(500),
    started_at              TIMESTAMP WITH TIME ZONE,
    completed_at            TIMESTAMP WITH TIME ZONE,
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_inspections_status ON inspections(status);
CREATE INDEX idx_inspections_product_id ON inspections(product_id);
CREATE INDEX idx_inspections_inspector_id ON inspections(inspector_id);
CREATE INDEX idx_inspections_compliance ON inspections(overall_compliance_status);
CREATE INDEX idx_inspections_created_at ON inspections(created_at DESC);

-- Inspection Images
CREATE TABLE IF NOT EXISTS inspection_images (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    inspection_id     UUID NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    image_path        VARCHAR(1000) NOT NULL,
    label             image_label NOT NULL DEFAULT 'OTHER',
    original_filename VARCHAR(500),
    file_size         BIGINT,
    mime_type         VARCHAR(100),
    width             INTEGER,
    height            INTEGER,
    processing_status processing_status NOT NULL DEFAULT 'PENDING',
    processed_at      TIMESTAMP WITH TIME ZONE,
    created_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_images_inspection_id ON inspection_images(inspection_id);

-- Declarations (extracted from images)
CREATE TABLE IF NOT EXISTS declarations (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    inspection_id     UUID NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    image_id          UUID REFERENCES inspection_images(id) ON DELETE SET NULL,
    field_name        VARCHAR(100) NOT NULL,  -- mrp, net_quantity, manufacturer, etc.
    field_value       TEXT,
    raw_text          TEXT,
    confidence_score  FLOAT,
    bounding_box      JSONB,  -- {"x": 10, "y": 20, "width": 100, "height": 30}
    extraction_method VARCHAR(100),  -- paddleocr, manual, stub
    is_verified       BOOLEAN NOT NULL DEFAULT FALSE,
    verified_by_id    UUID REFERENCES users(id),
    created_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_declarations_inspection_id ON declarations(inspection_id);
CREATE INDEX idx_declarations_field_name ON declarations(field_name);

-- OCR Regions (raw text regions detected on images)
CREATE TABLE IF NOT EXISTS ocr_regions (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    inspection_id    UUID NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    image_id         UUID REFERENCES inspection_images(id) ON DELETE SET NULL,
    text             TEXT NOT NULL,
    confidence_score FLOAT,
    bounding_box     JSONB,
    language         VARCHAR(50),
    created_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ocr_regions_inspection_id ON ocr_regions(inspection_id);
CREATE INDEX idx_ocr_regions_image_id ON ocr_regions(image_id);

-- Compliance Rules
CREATE TABLE IF NOT EXISTS rules (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id           VARCHAR(50) UNIQUE NOT NULL,  -- e.g., MRP-001
    field             VARCHAR(100) NOT NULL,
    category          VARCHAR(255),  -- NULL = applies to all
    mandatory         BOOLEAN NOT NULL DEFAULT TRUE,
    severity          violation_severity NOT NULL DEFAULT 'HIGH',
    description       TEXT NOT NULL,
    validation_logic  JSONB,
    legal_reference   TEXT,
    rule_version      VARCHAR(20) NOT NULL DEFAULT '1.0',
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rules_rule_id ON rules(rule_id);
CREATE INDEX idx_rules_field ON rules(field);
CREATE INDEX idx_rules_is_active ON rules(is_active);

-- Violations
CREATE TABLE IF NOT EXISTS violations (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    inspection_id    UUID NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    rule_id          UUID REFERENCES rules(id) ON DELETE SET NULL,
    declaration_id   UUID REFERENCES declarations(id) ON DELETE SET NULL,
    severity         violation_severity NOT NULL,
    status           violation_status NOT NULL DEFAULT 'OPEN',
    description      TEXT NOT NULL,
    legal_reference  TEXT,
    evidence_region  JSONB,
    notes            TEXT,
    resolved_at      TIMESTAMP WITH TIME ZONE,
    resolved_by_id   UUID REFERENCES users(id),
    created_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_violations_inspection_id ON violations(inspection_id);
CREATE INDEX idx_violations_severity ON violations(severity);
CREATE INDEX idx_violations_status ON violations(status);

-- Reports
CREATE TABLE IF NOT EXISTS reports (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    inspection_id     UUID NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    report_type       report_type NOT NULL DEFAULT 'PDF',
    file_path         VARCHAR(1000),
    generation_status report_status NOT NULL DEFAULT 'PENDING',
    generated_by_id   UUID REFERENCES users(id),
    generated_at      TIMESTAMP WITH TIME ZONE,
    created_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reports_inspection_id ON reports(inspection_id);

-- =============================================================================
-- TRIGGERS: updated_at auto-update
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_inspections_updated_at BEFORE UPDATE ON inspections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_rules_updated_at BEFORE UPDATE ON rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
