import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Plus, Search, Filter, ChevronLeft, ChevronRight } from 'lucide-react';
import { inspectionsApi } from '@/services/api';
import { StatusBadge } from '@/components/StatusBadge';
import type { Inspection, InspectionListResponse } from '@/types';

export default function InspectionsPage() {
  const [data, setData] = useState<InspectionListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchParams, setSearchParams] = useSearchParams();

  const page = parseInt(searchParams.get('page') || '1');
  const search = searchParams.get('search') || '';
  const complianceStatus = searchParams.get('compliance_status') || '';

  const load = async () => {
    setLoading(true);
    try {
      const result = await inspectionsApi.list({
        page, size: 15, search: search || undefined,
        compliance_status: complianceStatus || undefined,
      });
      setData(result);
    } catch {}
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [page, search, complianceStatus]);

  const setPage = (p: number) => setSearchParams((prev) => { prev.set('page', String(p)); return prev; });

  return (
    <div className="page-container">
      <div className="page-header flex items-start justify-between">
        <div>
          <h1 className="page-title">Inspections</h1>
          <p className="page-subtitle">Browse and manage all compliance inspections</p>
        </div>
        <Link to="/inspection/new" className="btn-primary">
          <Plus size={15} />
          New Inspection
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5">
        <div className="relative flex-1 min-w-60">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            id="search-inspections"
            type="text"
            placeholder="Search by inspection number..."
            defaultValue={search}
            onChange={(e) => {
              setSearchParams((prev) => { prev.set('search', e.target.value); prev.set('page', '1'); return prev; });
            }}
            className="form-input pl-9"
          />
        </div>
        <select
          id="filter-compliance"
          value={complianceStatus}
          onChange={(e) => setSearchParams((prev) => { prev.set('compliance_status', e.target.value); prev.set('page', '1'); return prev; })}
          className="form-input w-44"
        >
          <option value="">All Status</option>
          <option value="COMPLIANT">Compliant</option>
          <option value="NON_COMPLIANT">Non-Compliant</option>
          <option value="WARNING">Warning</option>
          <option value="NEEDS_REVIEW">Needs Review</option>
          <option value="PENDING">Pending</option>
        </select>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center h-64"><div className="spinner h-8 w-8" /></div>
      ) : (
        <>
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Inspection #</th>
                  <th>Status</th>
                  <th>Compliance</th>
                  <th>Pipeline</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data?.items.length === 0 && (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-slate-500">
                      No inspections found.{' '}
                      <Link to="/inspection/new" className="text-indigo-400 hover:underline">Create one</Link>
                    </td>
                  </tr>
                )}
                {data?.items.map((insp) => (
                  <tr key={insp.id}>
                    <td className="font-mono text-indigo-300 text-xs font-medium">{insp.inspection_number}</td>
                    <td><StatusBadge status={insp.status} /></td>
                    <td><StatusBadge status={insp.overall_compliance_status} /></td>
                    <td><StatusBadge status={insp.ai_pipeline_status} /></td>
                    <td className="text-slate-500 text-xs">
                      {new Date(insp.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
                    </td>
                    <td>
                      <Link
                        to={`/inspections/${insp.id}`}
                        className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                      >
                        View →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data && data.pages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <span className="text-sm text-slate-500">
                Showing {((page - 1) * 15) + 1}–{Math.min(page * 15, data.total)} of {data.total}
              </span>
              <div className="flex items-center gap-2">
                <button onClick={() => setPage(page - 1)} disabled={page === 1} className="btn-icon btn-secondary disabled:opacity-40">
                  <ChevronLeft size={15} />
                </button>
                <span className="text-sm text-slate-400">Page {page} of {data.pages}</span>
                <button onClick={() => setPage(page + 1)} disabled={page === data.pages} className="btn-icon btn-secondary disabled:opacity-40">
                  <ChevronRight size={15} />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
