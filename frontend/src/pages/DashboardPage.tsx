import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ClipboardList, CheckCircle, XCircle, AlertTriangle,
  Activity, TrendingUp, Plus, RefreshCw
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area,
} from 'recharts';
import { dashboardApi } from '@/services/api';
import { StatusBadge } from '@/components/StatusBadge';
import type { DashboardStats, TrendDataPoint, TopViolation, Inspection } from '@/types';

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [trend, setTrend] = useState<TrendDataPoint[]>([]);
  const [recent, setRecent] = useState<Inspection[]>([]);
  const [topViolations, setTopViolations] = useState<TopViolation[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [s, t, r, v] = await Promise.all([
        dashboardApi.stats(),
        dashboardApi.trend(30),
        dashboardApi.recent(8),
        dashboardApi.topViolations(5),
      ]);
      setStats(s); setTrend(t); setRecent(r as any); setTopViolations(v);
    } catch {}
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const statCards = stats ? [
    {
      label: 'Total Inspections',
      value: stats.total_inspections,
      icon: ClipboardList,
      color: 'text-indigo-400',
      bg: 'bg-indigo-500/10',
      sub: `${stats.inspections_this_month} this month`,
    },
    {
      label: 'Compliant',
      value: stats.compliant,
      icon: CheckCircle,
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/10',
      sub: `${stats.compliance_percentage}% rate`,
    },
    {
      label: 'Non-Compliant',
      value: stats.non_compliant,
      icon: XCircle,
      color: 'text-red-400',
      bg: 'bg-red-500/10',
      sub: 'Requires action',
    },
    {
      label: 'Total Violations',
      value: stats.total_violations,
      icon: AlertTriangle,
      color: 'text-amber-400',
      bg: 'bg-amber-500/10',
      sub: `${stats.needs_review} needs review`,
    },
  ] : [];

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header flex items-start justify-between">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Compliance monitoring for Legal Metrology enforcement</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} className="btn-secondary btn-sm">
            <RefreshCw size={13} />
            Refresh
          </button>
          <Link to="/inspection/new" className="btn-primary btn-sm">
            <Plus size={13} />
            New Inspection
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="spinner h-8 w-8" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Stat cards */}
          <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
            {statCards.map(({ label, value, icon: Icon, color, bg, sub }) => (
              <div key={label} className="stat-card">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="stat-label">{label}</div>
                    <div className="stat-value mt-1">{value.toLocaleString()}</div>
                  </div>
                  <div className={`w-10 h-10 rounded-lg ${bg} flex items-center justify-center`}>
                    <Icon size={18} className={color} />
                  </div>
                </div>
                <div className={`text-xs ${color} font-medium`}>{sub}</div>
              </div>
            ))}
          </div>

          {/* Charts row */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
            {/* Trend chart */}
            <div className="xl:col-span-2 card-static">
              <div className="section-header">
                <div className="flex items-center gap-2">
                  <TrendingUp size={16} className="text-indigo-400" />
                  <h2 className="section-title">Inspection Trend (30 days)</h2>
                </div>
              </div>
              {trend.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <AreaChart data={trend}>
                    <defs>
                      <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="colorCompliant" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.1)" />
                    <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} />
                    <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{ background: '#1a1740', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 8, color: '#f1f5f9' }}
                    />
                    <Area type="monotone" dataKey="total" stroke="#6366f1" fill="url(#colorTotal)" strokeWidth={2} name="Total" />
                    <Area type="monotone" dataKey="compliant" stroke="#10b981" fill="url(#colorCompliant)" strokeWidth={2} name="Compliant" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-56 flex flex-col items-center justify-center text-slate-500">
                  <Activity size={32} className="mb-2 opacity-40" />
                  <p className="text-sm">No trend data yet. Start inspecting!</p>
                </div>
              )}
            </div>

            {/* Top violations */}
            <div className="card-static">
              <div className="section-header">
                <div className="flex items-center gap-2">
                  <AlertTriangle size={16} className="text-amber-400" />
                  <h2 className="section-title">Top Violations</h2>
                </div>
              </div>
              {topViolations.length > 0 ? (
                <div className="space-y-2.5">
                  {topViolations.map((v, i) => (
                    <div key={i} className="flex items-start gap-3 p-2.5 rounded-lg bg-slate-800/40">
                      <StatusBadge status={v.severity} className="mt-0.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="text-xs text-slate-300 truncate">{v.description}</div>
                        <div className="text-xs text-slate-500 mt-0.5">{v.count} instances</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="h-40 flex items-center justify-center text-slate-500 text-sm">
                  No violations recorded yet
                </div>
              )}
            </div>
          </div>

          {/* Recent inspections */}
          <div className="card-static">
            <div className="section-header">
              <div className="flex items-center gap-2">
                <ClipboardList size={16} className="text-indigo-400" />
                <h2 className="section-title">Recent Inspections</h2>
              </div>
              <Link to="/inspections" className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
                View all →
              </Link>
            </div>
            {recent.length > 0 ? (
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Inspection #</th>
                      <th>Status</th>
                      <th>Compliance</th>
                      <th>Date</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {recent.map((insp: any) => (
                      <tr key={insp.id}>
                        <td className="font-mono text-indigo-300 text-xs">{insp.inspection_number}</td>
                        <td><StatusBadge status={insp.status} /></td>
                        <td><StatusBadge status={insp.overall_compliance_status} /></td>
                        <td className="text-slate-500 text-xs">
                          {new Date(insp.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
                        </td>
                        <td>
                          <Link to={`/inspections/${insp.id}`} className="text-xs text-indigo-400 hover:underline">
                            View
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-12 text-center">
                <ClipboardList size={40} className="mx-auto mb-3 text-slate-600" />
                <p className="text-slate-400 text-sm">No inspections yet.</p>
                <Link to="/inspection/new" className="btn-primary btn-sm mt-4 inline-flex">
                  <Plus size={13} />
                  Start First Inspection
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
