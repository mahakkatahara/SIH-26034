import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, X, Image as ImageIcon, AlertTriangle, ArrowRight, MapPin, FileText } from 'lucide-react';
import { inspectionsApi } from '@/services/api';
import type { ImageLabel } from '@/types';

const IMAGE_LABELS: ImageLabel[] = ['FRONT', 'BACK', 'SIDE', 'TOP', 'BOTTOM', 'OTHER'];

interface UploadedImage {
  file: File;
  preview: string;
  label: ImageLabel;
}

export default function NewInspectionPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState<1 | 2>(1);
  const [remarks, setRemarks] = useState('');
  const [location, setLocation] = useState('');
  const [images, setImages] = useState<UploadedImage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inspectionId, setInspectionId] = useState<string | null>(null);

  const handleFileDrop = (files: FileList | null) => {
    if (!files) return;
    const newImages: UploadedImage[] = [];
    Array.from(files).forEach((file) => {
      if (!file.type.startsWith('image/')) return;
      newImages.push({
        file,
        preview: URL.createObjectURL(file),
        label: 'FRONT',
      });
    });
    setImages((prev) => [...prev, ...newImages]);
  };

  const removeImage = (idx: number) => {
    setImages((prev) => {
      URL.revokeObjectURL(prev[idx].preview);
      return prev.filter((_, i) => i !== idx);
    });
  };

  const setImageLabel = (idx: number, label: ImageLabel) => {
    setImages((prev) => prev.map((img, i) => (i === idx ? { ...img, label } : img)));
  };

  const handleCreateAndUpload = async () => {
    setLoading(true);
    setError(null);
    try {
      // Step 1: Create inspection
      const insp = await inspectionsApi.create({ remarks, location });
      setInspectionId(insp.id);

      // Step 2: Upload images grouped by label
      if (images.length > 0) {
        const byLabel = images.reduce<Record<string, File[]>>((acc, img) => {
          acc[img.label] = acc[img.label] || [];
          acc[img.label].push(img.file);
          return acc;
        }, {});
        for (const [label, files] of Object.entries(byLabel)) {
          await inspectionsApi.uploadImages(insp.id, files, label);
        }
      }

      navigate(`/inspections/${insp.id}`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create inspection. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container max-w-3xl">
      <div className="page-header">
        <h1 className="page-title">New Inspection</h1>
        <p className="page-subtitle">Start a new Legal Metrology compliance inspection</p>
      </div>

      {/* Progress steps */}
      <div className="flex items-center gap-3 mb-7">
        {[{ n: 1, label: 'Inspection Details' }, { n: 2, label: 'Upload Images' }].map(({ n, label }) => (
          <div key={n} className="flex items-center gap-2">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold
              ${step === n ? 'bg-indigo-600 text-white' : step > n ? 'bg-emerald-600 text-white' : 'bg-slate-700 text-slate-400'}`}>
              {n}
            </div>
            <span className={`text-sm ${step === n ? 'text-white font-medium' : 'text-slate-500'}`}>{label}</span>
            {n < 2 && <ArrowRight size={14} className="text-slate-600" />}
          </div>
        ))}
      </div>

      {error && (
        <div className="mb-5 flex items-start gap-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
          <AlertTriangle size={16} className="text-red-400 flex-shrink-0 mt-0.5" />
          <span className="text-sm text-red-400">{error}</span>
        </div>
      )}

      {/* Step 1: Details */}
      <div className="space-y-5">
        <div className="card-static">
          <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <FileText size={16} className="text-indigo-400" />
            Inspection Details
          </h2>
          <div className="space-y-4">
            <div className="form-group">
              <label className="form-label">Location / Market</label>
              <div className="relative">
                <MapPin size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  id="location"
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="e.g., Sarojini Nagar Market, New Delhi"
                  className="form-input pl-9"
                />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Remarks / Notes</label>
              <textarea
                id="remarks"
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                placeholder="Field inspection notes, observations..."
                rows={3}
                className="form-input resize-none"
              />
            </div>
          </div>
        </div>

        {/* Step 2: Images */}
        <div className="card-static">
          <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <ImageIcon size={16} className="text-indigo-400" />
            Package Images
            <span className="ml-1 text-xs text-slate-500 font-normal">(optional — can upload later)</span>
          </h2>

          {/* Drop zone */}
          <div
            className="border-2 border-dashed border-indigo-500/30 rounded-xl p-8 text-center cursor-pointer
              hover:border-indigo-500/60 hover:bg-indigo-500/5 transition-all duration-200"
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => { e.preventDefault(); handleFileDrop(e.dataTransfer.files); }}
          >
            <Upload size={28} className="mx-auto mb-2 text-indigo-400 opacity-70" />
            <p className="text-sm text-slate-400">
              Drag &amp; drop images here, or <span className="text-indigo-400 font-medium">browse</span>
            </p>
            <p className="text-xs text-slate-600 mt-1">JPEG, PNG, WebP, TIFF — up to 20MB each</p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*"
              className="hidden"
              onChange={(e) => handleFileDrop(e.target.files)}
            />
          </div>

          {/* Image previews */}
          {images.length > 0 && (
            <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-3">
              {images.map((img, idx) => (
                <div key={idx} className="relative rounded-lg overflow-hidden border border-indigo-500/20 group">
                  <img
                    src={img.preview}
                    alt={`Upload ${idx + 1}`}
                    className="w-full h-32 object-cover"
                  />
                  <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 p-2">
                    <select
                      value={img.label}
                      onChange={(e) => setImageLabel(idx, e.target.value as ImageLabel)}
                      className="w-full text-xs bg-transparent text-white border border-white/20 rounded px-1 py-0.5"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {IMAGE_LABELS.map((l) => <option key={l} value={l}>{l}</option>)}
                    </select>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); removeImage(idx); }}
                    className="absolute top-1.5 right-1.5 w-5 h-5 rounded-full bg-red-600/80 flex items-center justify-center
                      opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X size={11} className="text-white" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Dev stub notice */}
        <div className="stub-notice flex items-start gap-3">
          <AlertTriangle size={16} className="flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Phase 1 — Development Stub</p>
            <p className="text-xs mt-0.5 opacity-80">
              AI analysis is not yet implemented. After creating this inspection, you can trigger analysis
              but will receive a stub response. Real OCR/CV analysis arrives in Phase 2.
            </p>
          </div>
        </div>

        {/* Submit */}
        <div className="flex items-center justify-end gap-3">
          <button onClick={() => navigate('/inspections')} className="btn-secondary">
            Cancel
          </button>
          <button
            id="create-inspection-btn"
            onClick={handleCreateAndUpload}
            disabled={loading}
            className="btn-primary"
          >
            {loading ? (
              <><div className="spinner h-4 w-4" /> Creating...</>
            ) : (
              <>Create Inspection <ArrowRight size={14} /></>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
