-- =============================================================================
-- Seed Data — Legal Metrology Inspection System
-- Initial users, rules, and categories
-- =============================================================================

-- =============================================================================
-- DEFAULT USERS
-- Passwords are bcrypt hashed. Defaults:
--   admin@legalmetrology.gov.in     → Admin@123
--   inspector@legalmetrology.gov.in → Inspector@123
--   viewer@legalmetrology.gov.in    → Viewer@123
-- CHANGE THESE IN PRODUCTION!
-- =============================================================================

INSERT INTO users (id, email, hashed_password, full_name, role, employee_id, department, is_active)
VALUES
(
    uuid_generate_v4(),
    'admin@legalmetrology.gov.in',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',  -- Admin@123
    'System Administrator',
    'ADMIN',
    'ADMIN-001',
    'Legal Metrology Division',
    TRUE
),
(
    uuid_generate_v4(),
    'inspector@legalmetrology.gov.in',
    '$2b$12$LHzRx6DPz3EMKEv8mE.Z/OnBVZIFi07n4KJwdnO2qiMZOmjLKNs0C',  -- Inspector@123
    'Field Inspector',
    'INSPECTOR',
    'INS-001',
    'Enforcement Wing',
    TRUE
),
(
    uuid_generate_v4(),
    'viewer@legalmetrology.gov.in',
    '$2b$12$QZdVWG3VKHmZfhPJFiL.0.NkGbpY7H4Lm.G8XL9RfKDLxW1n7EZoi',  -- Viewer@123
    'Report Viewer',
    'VIEWER',
    'VIW-001',
    'Compliance Monitoring',
    TRUE
)
ON CONFLICT (email) DO NOTHING;

-- =============================================================================
-- COMPLIANCE RULES
-- Based on Legal Metrology (Packaged Commodities) Rules, 2011
-- =============================================================================

INSERT INTO rules (rule_id, field, category, mandatory, severity, description, validation_logic, legal_reference, rule_version, is_active)
VALUES

-- MRP Rules
(
    'MRP-001',
    'mrp',
    NULL,
    TRUE,
    'HIGH',
    'Maximum Retail Price (MRP) must be declared on every pre-packaged commodity',
    '{"type": "presence_check", "field": "mrp", "format": "numeric_currency"}',
    'Rule 6(1)(f) — Legal Metrology (Packaged Commodities) Rules, 2011',
    '1.0',
    TRUE
),
(
    'MRP-002',
    'mrp',
    NULL,
    TRUE,
    'HIGH',
    'MRP must be declared as "MRP Rs." or "MRP ₹" followed by the price inclusive of all taxes',
    '{"type": "format_check", "pattern": "MRP\\s*(Rs\\.?|₹)\\s*[0-9]+", "case_insensitive": true}',
    'Rule 6(1)(f) — Legal Metrology (Packaged Commodities) Rules, 2011',
    '1.0',
    TRUE
),
(
    'MRP-003',
    'mrp',
    NULL,
    TRUE,
    'MEDIUM',
    'MRP declaration must not be obscured, overprinted or struck through',
    '{"type": "visibility_check", "field": "mrp"}',
    'Rule 6(1)(f) — Legal Metrology (Packaged Commodities) Rules, 2011',
    '1.0',
    TRUE
),

-- Net Quantity Rules
(
    'NQ-001',
    'net_quantity',
    NULL,
    TRUE,
    'HIGH',
    'Net quantity must be declared on all pre-packaged commodities',
    '{"type": "presence_check", "field": "net_quantity"}',
    'Rule 6(1)(b) — Legal Metrology (Packaged Commodities) Rules, 2011',
    '1.0',
    TRUE
),
(
    'NQ-002',
    'net_quantity',
    NULL,
    TRUE,
    'MEDIUM',
    'Net quantity must be expressed in standard units: g, kg, ml, l, cm, m, number',
    '{"type": "unit_check", "allowed_units": ["g", "gm", "kg", "ml", "l", "ltr", "cm", "m", "nos", "pcs", "units"]}',
    'Rule 7 — Legal Metrology (Packaged Commodities) Rules, 2011',
    '1.0',
    TRUE
),

-- Manufacturer/Packer/Importer Rules
(
    'MFR-001',
    'manufacturer_name',
    NULL,
    TRUE,
    'HIGH',
    'Name and address of manufacturer/packer/importer must be declared',
    '{"type": "presence_check", "field": "manufacturer_name"}',
    'Rule 6(1)(c) — Legal Metrology (Packaged Commodities) Rules, 2011',
    '1.0',
    TRUE
),
(
    'MFR-002',
    'manufacturer_address',
    NULL,
    TRUE,
    'HIGH',
    'Complete postal address of manufacturer must be declared including PIN code',
    '{"type": "presence_check", "field": "manufacturer_address"}',
    'Rule 6(1)(c) — Legal Metrology (Packaged Commodities) Rules, 2011',
    '1.0',
    TRUE
),

-- Date Rules
(
    'DATE-001',
    'manufacturing_date',
    NULL,
    TRUE,
    'HIGH',
    'Month and year of manufacture/packing must be declared',
    '{"type": "presence_check", "field": "manufacturing_date", "format": "month_year"}',
    'Rule 6(1)(e) — Legal Metrology (Packaged Commodities) Rules, 2011',
    '1.0',
    TRUE
),

-- Consumer Care Rules
(
    'CC-001',
    'consumer_care_info',
    NULL,
    TRUE,
    'MEDIUM',
    'Consumer care details (name/email/phone) must be declared for consumer complaints',
    '{"type": "presence_check", "field": "consumer_care_info"}',
    'Rule 6(1)(l) — Legal Metrology (Packaged Commodities) Rules, 2011',
    '1.0',
    TRUE
),

-- Country of Origin
(
    'COO-001',
    'country_of_origin',
    NULL,
    FALSE,
    'MEDIUM',
    'Country of origin must be declared for imported commodities',
    '{"type": "conditional_check", "condition": "is_imported", "field": "country_of_origin"}',
    'Rule 6(1)(k) — Legal Metrology (Packaged Commodities) Rules, 2011 + Consumer Protection Rules',
    '1.0',
    TRUE
)

ON CONFLICT (rule_id) DO NOTHING;
