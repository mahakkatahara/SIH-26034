import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Brain, AlertTriangle, CheckCircle, FileText,
  Image as ImageIcon, Eye, Download, RefreshCw, Loader2
} from 'lucide-react';
import { inspectionsApi, reportsApi } from '@/services/api';
import { StatusBadge } from '@/components/StatusBadge';
import type { InspectionDetail, AnalysisResult } from '@/types';

export default function InspectionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [inspection, setInspection] = useState<InspectionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const API_URL = import.meta.env.VITE_API_URL || '';

  const load = async (showSpinner = false) => {
    if (!id) return;
    if (showSpinner) setLoading(true);
    try {
      const data = await inspectionsApi.get(id);
      setInspection(data);
      if (data.images.length > 0 && !selectedImage) {
        setSelectedImage(data.images[0].image_path);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load inspection details.');
    } finally {
      if (showSpinner) setLoading(false);
    }
  };

  useEffect(() => { load(true); }, [id]);

  const handleAnalyze = async () => {
    if (!id) return;
    if (!inspection?.images || inspection.images.length === 0) {
      setError('Please upload at least one package image before running analysis.');
      return;
    }
    setAnalyzing(true);
    setError(null);
    try {
      const result = await inspectionsApi.analyze(id);
      setAnalysisResult(result);
      await load(false); // Refresh inspection status & violations
    } catch (err: any) {
      const message =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        'Analysis failed. Please check the backend connection and try again.';
      setError(message);
      console.error('Analysis error:', err);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleGenerateReport = async (type: 'PDF' | 'DOCX') => {
    if (!id) return;
    setGeneratingReport(true);
    try {
      await reportsApi.generate(id, type);
      alert(`${type} report generation queued. (Phase 8 — stub: actual generation not yet implemented)`);
    } catch {}
    finally { setGeneratingReport(false); }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="spinner h-8 w-8" />
      </div>
    );
  }

  if (!inspection) {
    return (
      <div className="page-container text-center py-24">
        <p className="text-slate-400">Inspection not found.</p>
        <Link to="/inspections" className="btn-secondary mt-4 inline-flex">← Back</Link>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* Header */}
      <div className="flex items-start gap-4 mb-6">
        <button onClick={() => navigate('/inspections')} className="btn-icon btn-secondary mt-1">
          <ArrowLeft size={15} />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="page-title">{inspection.inspection_number}</h1>
            <StatusBadge status={inspection.overall_compliance_status} />
            <StatusBadge status={inspection.status} />
          </div>
          <p className="page-subtitle">
            Created {new Date(inspection.created_at).toLocaleString('en-IN')}
            {inspection.location && ` · ${inspection.location}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => handleGenerateReport('PDF')} disabled={generatingReport} className="btn-secondary btn-sm">
            <Download size={13} /> PDF Report
          </button>
          <button onClick={() => handleGenerateReport('DOCX')} disabled={generatingReport} className="btn-secondary btn-sm">
            <Download size={13} /> DOCX
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {/* Left: Images + AI */}
        <div className="xl:col-span-2 space-y-5">
          {/* Image viewer */}
          <div className="card-static">
            <div className="section-header">
              <div className="flex items-center gap-2">
                <ImageIcon size={15} className="text-indigo-400" />
                <h2 className="section-title">Package Images ({inspection.images.length})</h2>
              </div>
              <Link to={`/inspection/new`} className="text-xs text-indigo-400 hover:underline">
                + Add images
              </Link>
            </div>

            {inspection.images.length === 0 ? (
              <div className="py-10 text-center text-slate-500 text-sm">
                No images uploaded yet.
              </div>
            ) : (
              <>
                {/* Main image */}
                {selectedImage && (
                  <div className="rounded-lg overflow-hidden bg-slate-900 mb-3 aspect-video flex items-center justify-center">
                    <img
                      src={`${API_URL}/${selectedImage}`}
                      alt="Package"
                      className="max-h-full max-w-full object-contain"
                    />
                  </div>
                )}
                {/* Thumbnails */}
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {inspection.images.map((img) => (
                    <button
                      key={img.id}
                      onClick={() => setSelectedImage(img.image_path)}
                      className={`flex-shrink-0 rounded-md overflow-hidden border-2 transition-all
                        ${selectedImage === img.image_path ? 'border-indigo-500' : 'border-transparent'}`}
                    >
                      <div className="relative">
                        <img
                          src={`${API_URL}/${img.image_path}`}
                          alt={img.label}
                          className="w-16 h-14 object-cover"
                        />
                        <div className="absolute bottom-0 inset-x-0 bg-black/60 text-center text-[9px] text-white py-0.5">
                          {img.label}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* AI Analysis */}
          <div className="card-static">
            <div className="section-header">
              <div className="flex items-center gap-2">
                <Brain size={15} className="text-indigo-400" />
                <h2 className="section-title">AI Analysis</h2>
                <StatusBadge status={inspection.ai_pipeline_status} />
              </div>
              <button
                id="analyze-btn"
                data-testid="analyze-button"
                onClick={handleAnalyze}
                disabled={analyzing}
                className="btn-primary btn-sm flex items-center gap-1.5"
              >
                {analyzing ? (
                  <>
                    <Loader2 size={13} className="animate-spin" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <RefreshCw size={13} />
                    <span>Analyze</span>
                  </>
                )}
              </button>
            </div>

            {/* Error message */}
            {error && (
              <div
                role="alert"
                className="mb-4 flex items-start gap-2 p-3 rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 text-sm"
              >
                <AlertTriangle size={16} className="flex-shrink-0 mt-0.5 text-red-400" />
                <div className="flex-1">
                  <p>{error}</p>
                </div>
                <button
                  onClick={() => setError(null)}
                  className="text-xs text-red-400 hover:text-red-200 ml-2"
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* Loading state banner */}
            {analyzing && (
              <div className="py-6 text-center text-indigo-300 text-sm bg-indigo-950/20 border border-indigo-500/20 rounded-lg mb-4">
                <Loader2 size={24} className="animate-spin mx-auto mb-2 text-indigo-400" />
                <p className="font-medium">AI analysis in progress...</p>
                <p className="text-xs text-slate-400 mt-1">
                  Extracting mandatory declarations and verifying Legal Metrology compliance.
                </p>
              </div>
            )}

            {/* Stub notice */}
            {(inspection.ai_pipeline_status === 'DEV_STUB' || analysisResult?.pipeline_status === 'DEV_STUB') && (
              <div className="stub-notice mb-4 flex items-start gap-2">
                <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
                <p className="text-xs">
                  {analysisResult?.notice ||
                    'AI pipeline not yet implemented (Phase 1). Human review required for all inspections.'}
                </p>
              </div>
            )}

            {inspection.ai_pipeline_status === 'NOT_STARTED' && !analysisResult && !analyzing && (
              <div className="py-8 text-center text-slate-500 text-sm">
                <Brain size={32} className="mx-auto mb-2 opacity-30" />
                Analysis not yet started. Upload images and click "Analyze".
              </div>
            )}

            {/* Declarations */}
            {(() => {
              const decls = (analysisResult && analysisResult.declarations.length > 0)
                ? analysisResult.declarations
                : (inspection.declarations || []);
              if (decls.length === 0) return null;
              return (
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold text-slate-300">
                    Extracted Declarations ({decls.length})
                  </h3>
                  {decls.map((d) => (
                    <div key={d.id} className="flex items-center justify-between p-3 rounded-lg bg-slate-800/40">
                      <div>
                        <span className="text-xs font-mono text-indigo-300">{d.field_name}</span>
                        <span className="mx-2 text-slate-600">·</span>
                        <span className="text-sm text-white">{d.field_value || <em className="text-slate-500">Not declared</em>}</span>
                      </div>
                      {d.confidence_score != null && (
                        <span className="text-xs text-slate-500">
                          {(d.confidence_score * 100).toFixed(0)}% confidence
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              );
            })()}
          </div>
        </div>

        {/* Right: Info + Violations */}
        <div className="space-y-5">
          {/* Inspection info */}
          <div className="card-static">
            <h2 className="section-title mb-4">Inspection Info</h2>
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="form-label">Inspection ID</dt>
                <dd className="font-mono text-indigo-300 text-xs break-all">{inspection.id}</dd>
              </div>
              <div>
                <dt className="form-label">Status</dt>
                <dd><StatusBadge status={inspection.status} /></dd>
              </div>
              <div>
                <dt className="form-label">Compliance</dt>
                <dd><StatusBadge status={inspection.overall_compliance_status} /></dd>
              </div>
              {inspection.remarks && (
                <div>
                  <dt className="form-label">Remarks</dt>
                  <dd className="text-slate-300">{inspection.remarks}</dd>
                </div>
              )}
              {inspection.ai_confidence_score != null && (
                <div>
                  <dt className="form-label">Confidence Score</dt>
                  <dd className="text-slate-300">{(inspection.ai_confidence_score * 100).toFixed(1)}%</dd>
                </div>
              )}
            </dl>
          </div>

          {/* Violations */}
          <div className="card-static">
            <div className="section-header">
              <div className="flex items-center gap-2">
                <AlertTriangle size={15} className="text-amber-400" />
                <h2 className="section-title">Violations ({inspection.violations.length})</h2>
              </div>
            </div>
            {inspection.violations.length === 0 ? (
              <div className="py-6 text-center">
                <CheckCircle size={28} className="mx-auto mb-2 text-emerald-400 opacity-60" />
                <p className="text-sm text-slate-500">No violations detected</p>
              </div>
            ) : (
              <div className="space-y-2">
                {inspection.violations.map((v) => (
                  <div key={v.id} className="p-3 rounded-lg border border-red-500/15 bg-red-500/5">
                    <div className="flex items-center gap-2 mb-1">
                      <StatusBadge status={v.severity} />
                      <StatusBadge status={v.status} />
                    </div>
                    <p className="text-sm text-slate-300">{v.description}</p>
                    {v.legal_reference && (
                      <p className="text-xs text-slate-500 mt-1">{v.legal_reference}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Confidence threshold warning */}
          {inspection.ai_confidence_score != null &&
            inspection.ai_confidence_score < 0.75 && (
            <div className="stub-notice flex items-start gap-2">
              <Eye size={14} className="flex-shrink-0 mt-0.5" />
              <p className="text-xs">
                <strong>Human verification recommended.</strong><br />
                Confidence score ({(inspection.ai_confidence_score * 100).toFixed(1)}%) is below the threshold of 75%.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
