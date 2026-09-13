import { clsx } from 'clsx';
import type { ComplianceStatus, ViolationSeverity, InspectionStatus, PipelineStatus } from '@/types';

interface StatusBadgeProps {
  status: ComplianceStatus | ViolationSeverity | InspectionStatus | PipelineStatus | string;
  className?: string;
}

const statusConfig: Record<string, { className: string; label: string; dot?: boolean }> = {
  // Compliance
  COMPLIANT:     { className: 'badge-compliant', label: 'Compliant', dot: true },
  NON_COMPLIANT: { className: 'badge-non-compliant', label: 'Non-Compliant', dot: true },
  WARNING:       { className: 'badge-warning', label: 'Warning', dot: true },
  NEEDS_REVIEW:  { className: 'badge-review', label: 'Needs Review', dot: true },
  PENDING:       { className: 'badge-pending', label: 'Pending', dot: true },
  // Violations
  HIGH:   { className: 'badge-high', label: 'High' },
  MEDIUM: { className: 'badge-medium', label: 'Medium' },
  LOW:    { className: 'badge-low', label: 'Low' },
  INFO:   { className: 'badge-info', label: 'Info' },
  // Inspection status
  DRAFT:            { className: 'badge-pending', label: 'Draft' },
  IN_PROGRESS:      { className: 'badge-review', label: 'In Progress' },
  ANALYSIS_PENDING: { className: 'badge-warning', label: 'Analysis Pending' },
  ANALYSIS_COMPLETE:{ className: 'badge-review', label: 'Analysis Complete' },
  COMPLETED:        { className: 'badge-compliant', label: 'Completed' },
  CANCELLED:        { className: 'badge-non-compliant', label: 'Cancelled' },
  // Pipeline
  NOT_STARTED:  { className: 'badge-pending', label: 'Not Started' },
  PREPROCESSING:{ className: 'badge-review', label: 'Preprocessing' },
  OCR:          { className: 'badge-review', label: 'OCR' },
  EXTRACTION:   { className: 'badge-review', label: 'Extraction' },
  RULE_CHECK:   { className: 'badge-review', label: 'Rule Check' },
  FAILED:       { className: 'badge-non-compliant', label: 'Failed' },
  DEV_STUB:     { className: 'badge-stub', label: '⚠ Dev Stub' },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status] ?? { className: 'badge-pending', label: status };
  return (
    <span className={clsx(config.className, className)}>
      {config.dot && (
        <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" />
      )}
      {config.label}
    </span>
  );
}
