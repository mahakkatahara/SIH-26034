import { useAuthStore } from '@/store/authStore';
import { User, Bell, Shield, Database, Cpu } from 'lucide-react';

export default function SettingsPage() {
  const { user } = useAuthStore();

  return (
    <div className="page-container max-w-2xl">
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">Application configuration and profile management</p>
      </div>

      <div className="space-y-5">
        {/* Profile */}
        <div className="card-static">
          <div className="flex items-center gap-2 mb-4">
            <User size={15} className="text-indigo-400" />
            <h2 className="section-title">Profile</h2>
          </div>
          <dl className="space-y-3 text-sm">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <dt className="form-label">Full Name</dt>
                <dd className="text-slate-300">{user?.full_name}</dd>
              </div>
              <div>
                <dt className="form-label">Role</dt>
                <dd><span className="badge-review badge">{user?.role}</span></dd>
              </div>
              <div>
                <dt className="form-label">Email</dt>
                <dd className="text-slate-300 font-mono text-xs">{user?.email}</dd>
              </div>
              <div>
                <dt className="form-label">Employee ID</dt>
                <dd className="text-slate-300">{user?.employee_id || '—'}</dd>
              </div>
              <div>
                <dt className="form-label">Department</dt>
                <dd className="text-slate-300">{user?.department || '—'}</dd>
              </div>
              <div>
                <dt className="form-label">Last Login</dt>
                <dd className="text-slate-300 text-xs">
                  {user?.last_login ? new Date(user.last_login).toLocaleString('en-IN') : '—'}
                </dd>
              </div>
            </div>
          </dl>
        </div>

        {/* System Info */}
        <div className="card-static">
          <div className="flex items-center gap-2 mb-4">
            <Database size={15} className="text-indigo-400" />
            <h2 className="section-title">System Information</h2>
          </div>
          <dl className="space-y-2 text-sm">
            {[
              ['Application', 'Legal Metrology Inspection System'],
              ['Version', '1.0.0 (Phase 1)'],
              ['Problem Statement', 'SIH-26034'],
              ['Legal Framework', 'Legal Metrology (PC) Rules, 2011'],
              ['AI Pipeline', 'Phase 1 — Development Stub'],
              ['Rule Engine', 'Phase 1 — Skeleton (Phase 4 full implementation)'],
              ['Reports', 'Phase 1 — Stub (Phase 8 PDF/DOCX implementation)'],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between py-1.5 border-b border-indigo-500/5 last:border-0">
                <dt className="text-slate-500">{k}</dt>
                <dd className="text-slate-300 font-medium text-xs text-right max-w-xs">{v}</dd>
              </div>
            ))}
          </dl>
        </div>

        {/* AI Settings info */}
        <div className="card-static">
          <div className="flex items-center gap-2 mb-4">
            <Cpu size={15} className="text-indigo-400" />
            <h2 className="section-title">AI Pipeline Configuration</h2>
          </div>
          <div className="stub-notice">
            <p className="font-semibold text-amber-400 mb-1">Phase 1 — Stub Mode Active</p>
            <p className="text-xs opacity-80">
              The AI pipeline is currently in stub mode. Configure <code className="font-mono">AI_PIPELINE_MODE</code> in
              your <code className="font-mono">.env</code> file to switch to real OCR (Phase 2+).
              The confidence threshold for human review recommendation is <strong>75%</strong>.
            </p>
          </div>
        </div>

        {/* Security */}
        <div className="card-static">
          <div className="flex items-center gap-2 mb-4">
            <Shield size={15} className="text-indigo-400" />
            <h2 className="section-title">Security</h2>
          </div>
          <p className="text-xs text-slate-500 mb-3">
            To change your password, contact the system administrator.
          </p>
          <div className="p-3 rounded-lg bg-indigo-500/5 border border-indigo-500/10 text-xs text-slate-400">
            Sessions are secured with JWT tokens. Access tokens expire in 30 minutes
            and are automatically refreshed. All API calls use HTTPS in production.
          </div>
        </div>
      </div>
    </div>
  );
}
