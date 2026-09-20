import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import InspectionDetailPage from '@/pages/InspectionDetailPage';
import { inspectionsApi } from '@/services/api';
import type { InspectionDetail, AnalysisResult } from '@/types';

// Mock inspectionsApi methods
vi.mock('@/services/api', () => ({
  inspectionsApi: {
    get: vi.fn(),
    analyze: vi.fn(),
  },
  reportsApi: {
    generate: vi.fn(),
  },
}));

const mockInspectionWithImages: InspectionDetail = {
  id: 'insp-1234',
  inspection_number: 'LMIS-20260919-TEST',
  status: 'IN_PROGRESS',
  overall_compliance_status: 'PENDING',
  inspector_id: 'user-1',
  ai_pipeline_status: 'NOT_STARTED',
  ai_confidence_score: undefined,
  remarks: 'Test inspection',
  location: 'Mumbai Depot',
  created_at: '2026-09-19T10:00:00Z',
  updated_at: '2026-09-19T10:00:00Z',
  images: [
    {
      id: 'img-1',
      inspection_id: 'insp-1234',
      image_path: 'uploads/insp-1234/label.jpeg',
      label: 'FRONT',
      processing_status: 'UPLOADED',
      created_at: '2026-09-19T10:00:00Z',
    },
  ],
  declarations: [],
  violations: [],
};

const mockAnalysisResult: AnalysisResult = {
  inspection_id: 'insp-1234',
  pipeline_status: 'COMPLETED',
  declarations: [
    {
      id: 'decl-1',
      inspection_id: 'insp-1234',
      field_name: 'commodity_name',
      field_value: 'Basmati Rice',
      raw_text: 'Basmati Rice',
      confidence_score: 0.98,
      is_verified: false,
      created_at: '2026-09-19T10:05:00Z',
    },
  ],
  violations: [
    {
      id: 'viol-1',
      inspection_id: 'insp-1234',
      rule_id: 'MRP-001',
      severity: 'HIGH',
      status: 'OPEN',
      description: 'MRP is missing on label',
      legal_reference: 'Rule 6(1)(f)',
      created_at: '2026-09-19T10:05:00Z',
    },
  ],
  overall_compliance_status: 'NON_COMPLIANT',
  confidence_score: 0.98,
};

function renderPage(inspectionId = 'insp-1234') {
  return render(
    <MemoryRouter initialEntries={[`/inspections/${inspectionId}`]}>
      <Routes>
        <Route path="/inspections/:id" element={<InspectionDetailPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('InspectionDetailPage — Analyze Action', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls POST analyze endpoint with inspection id on button click', async () => {
    vi.mocked(inspectionsApi.get).mockResolvedValue(mockInspectionWithImages);
    vi.mocked(inspectionsApi.analyze).mockResolvedValue(mockAnalysisResult);

    renderPage();

    // Wait for initial load
    expect(await screen.findByText('LMIS-20260919-TEST')).toBeInTheDocument();

    const analyzeBtn = screen.getByRole('button', { name: /analyze/i });
    expect(analyzeBtn).toBeInTheDocument();

    await userEvent.click(analyzeBtn);

    expect(inspectionsApi.analyze).toHaveBeenCalledTimes(1);
    expect(inspectionsApi.analyze).toHaveBeenCalledWith('insp-1234');
  });

  it('shows loading state while analysis is running and restores button after', async () => {
    let resolveAnalysis: (val: AnalysisResult) => void;
    const analysisPromise = new Promise<AnalysisResult>((resolve) => {
      resolveAnalysis = resolve;
    });

    vi.mocked(inspectionsApi.get).mockResolvedValue(mockInspectionWithImages);
    vi.mocked(inspectionsApi.analyze).mockReturnValue(analysisPromise);

    renderPage();
    await screen.findByText('LMIS-20260919-TEST');

    const analyzeBtn = screen.getByRole('button', { name: /analyze/i });
    await userEvent.click(analyzeBtn);

    // Verify loading state is shown
    expect(screen.getByText(/analyzing\.\.\./i)).toBeInTheDocument();
    expect(analyzeBtn).toBeDisabled();

    // Resolve analysis
    resolveAnalysis!(mockAnalysisResult);

    await waitFor(() => {
      expect(screen.queryByText(/analyzing\.\.\./i)).not.toBeInTheDocument();
    });
  });

  it('refreshes inspection page data when analysis completes', async () => {
    const updatedInspection: InspectionDetail = {
      ...mockInspectionWithImages,
      ai_pipeline_status: 'COMPLETED',
      overall_compliance_status: 'NON_COMPLIANT',
      declarations: mockAnalysisResult.declarations,
      violations: mockAnalysisResult.violations,
    };

    vi.mocked(inspectionsApi.get)
      .mockResolvedValueOnce(mockInspectionWithImages) // initial load
      .mockResolvedValueOnce(updatedInspection);      // refresh after analysis

    vi.mocked(inspectionsApi.analyze).mockResolvedValue(mockAnalysisResult);

    renderPage();
    await screen.findByText('LMIS-20260919-TEST');

    const analyzeBtn = screen.getByRole('button', { name: /analyze/i });
    await userEvent.click(analyzeBtn);

    // inspectionsApi.get called twice: initial load and refresh
    await waitFor(() => {
      expect(inspectionsApi.get).toHaveBeenCalledTimes(2);
    });

    // Check newly extracted declarations and violations are displayed
    expect(await screen.findByText('Basmati Rice')).toBeInTheDocument();
    expect(await screen.findByText('MRP is missing on label')).toBeInTheDocument();
  });

  it('surfaces backend error message to user instead of failing silently', async () => {
    vi.mocked(inspectionsApi.get).mockResolvedValue(mockInspectionWithImages);
    vi.mocked(inspectionsApi.analyze).mockRejectedValue({
      response: {
        data: { detail: 'AI vision pipeline quota exceeded. Please retry.' },
      },
    });

    renderPage();
    await screen.findByText('LMIS-20260919-TEST');

    const analyzeBtn = screen.getByRole('button', { name: /analyze/i });
    await userEvent.click(analyzeBtn);

    // Error banner must be visible to user
    const errorAlert = await screen.findByRole('alert');
    expect(errorAlert).toBeInTheDocument();
    expect(errorAlert).toHaveTextContent('AI vision pipeline quota exceeded. Please retry.');
  });

  it('surfaces user-friendly error when analyzing an inspection with no images', async () => {
    const inspectionWithoutImages: InspectionDetail = {
      ...mockInspectionWithImages,
      images: [],
    };

    vi.mocked(inspectionsApi.get).mockResolvedValue(inspectionWithoutImages);

    renderPage();
    await screen.findByText('LMIS-20260919-TEST');

    const analyzeBtn = screen.getByRole('button', { name: /analyze/i });
    await userEvent.click(analyzeBtn);

    // Must surface an error and not call backend API
    const errorAlert = await screen.findByRole('alert');
    expect(errorAlert).toBeInTheDocument();
    expect(errorAlert).toHaveTextContent(/please upload at least one package image/i);
    expect(inspectionsApi.analyze).not.toHaveBeenCalled();
  });
});
