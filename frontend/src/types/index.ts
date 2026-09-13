// TypeScript type definitions for the LMIS application

export type UserRole = 'ADMIN' | 'INSPECTOR' | 'VIEWER';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  employee_id?: string;
  department?: string;
  phone?: string;
  is_active: boolean;
  last_login?: string;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// ─── Products ─────────────────────────────────────────────────────────────────

export interface Product {
  id: string;
  name: string;
  category?: string;
  brand?: string;
  barcode?: string;
  description?: string;
  manufacturer_name?: string;
  manufacturer_address?: string;
  country_of_origin?: string;
  created_by_id?: string;
  created_at: string;
  updated_at: string;
}

export interface ProductListResponse {
  items: Product[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// ─── Inspections ──────────────────────────────────────────────────────────────

export type InspectionStatus =
  | 'DRAFT'
  | 'IN_PROGRESS'
  | 'ANALYSIS_PENDING'
  | 'ANALYSIS_COMPLETE'
  | 'COMPLETED'
  | 'CANCELLED';

export type ComplianceStatus =
  | 'COMPLIANT'
  | 'NON_COMPLIANT'
  | 'WARNING'
  | 'NEEDS_REVIEW'
  | 'PENDING';

export type PipelineStatus =
  | 'NOT_STARTED'
  | 'PREPROCESSING'
  | 'OCR'
  | 'EXTRACTION'
  | 'RULE_CHECK'
  | 'COMPLETED'
  | 'FAILED'
  | 'DEV_STUB';

export type ImageLabel = 'FRONT' | 'BACK' | 'SIDE' | 'TOP' | 'BOTTOM' | 'OTHER';

export interface InspectionImage {
  id: string;
  inspection_id: string;
  image_path: string;
  label: ImageLabel;
  original_filename?: string;
  file_size?: number;
  mime_type?: string;
  width?: number;
  height?: number;
  processing_status: string;
  processed_at?: string;
  created_at: string;
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Declaration {
  id: string;
  inspection_id: string;
  image_id?: string;
  field_name: string;
  field_value?: string;
  raw_text?: string;
  confidence_score?: number;
  bounding_box?: BoundingBox;
  extraction_method?: string;
  is_verified: boolean;
  created_at: string;
}

export type ViolationSeverity = 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
export type ViolationStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED' | 'FALSE_POSITIVE';

export interface Violation {
  id: string;
  inspection_id: string;
  rule_id?: string;
  declaration_id?: string;
  severity: ViolationSeverity;
  status: ViolationStatus;
  description: string;
  legal_reference?: string;
  evidence_region?: BoundingBox & { image_id?: string };
  notes?: string;
  created_at: string;
}

export interface Inspection {
  id: string;
  inspection_number: string;
  status: InspectionStatus;
  overall_compliance_status: ComplianceStatus;
  product_id?: string;
  inspector_id: string;
  ai_pipeline_status: PipelineStatus;
  ai_confidence_score?: number;
  remarks?: string;
  location?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface InspectionDetail extends Inspection {
  images: InspectionImage[];
  declarations: Declaration[];
  violations: Violation[];
}

export interface InspectionListResponse {
  items: Inspection[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface AnalysisResult {
  inspection_id: string;
  pipeline_status: PipelineStatus;
  notice?: string;
  declarations: Declaration[];
  violations: Violation[];
  overall_compliance_status: ComplianceStatus;
  confidence_score?: number;
  processing_time_ms?: number;
}

// ─── Rules ────────────────────────────────────────────────────────────────────

export interface Rule {
  id: string;
  rule_id: string;
  field: string;
  category?: string;
  mandatory: boolean;
  severity: ViolationSeverity;
  description: string;
  validation_logic?: Record<string, unknown>;
  legal_reference?: string;
  rule_version: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RuleListResponse {
  items: Rule[];
  total: number;
}

// ─── Reports ──────────────────────────────────────────────────────────────────

export interface Report {
  id: string;
  inspection_id: string;
  report_type: 'PDF' | 'DOCX';
  file_path?: string;
  generation_status: string;
  generated_by_id?: string;
  generated_at?: string;
  created_at: string;
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export interface DashboardStats {
  total_inspections: number;
  compliant: number;
  non_compliant: number;
  needs_review: number;
  warning: number;
  compliance_percentage: number;
  total_violations: number;
  inspections_this_month: number;
  inspections_this_week: number;
}

export interface TrendDataPoint {
  date: string;
  total: number;
  compliant: number;
  non_compliant: number;
}

export interface TopViolation {
  description: string;
  severity: ViolationSeverity;
  count: number;
}

// ─── API Pagination ───────────────────────────────────────────────────────────

export interface PaginatedRequest {
  page?: number;
  size?: number;
  search?: string;
}

export interface APIError {
  detail: string;
  error_code?: string;
}
