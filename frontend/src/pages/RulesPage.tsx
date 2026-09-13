import { useEffect, useState } from 'react';
import { BookOpen, Shield, ExternalLink, Filter } from 'lucide-react';
import { rulesApi } from '@/services/api';
import { StatusBadge } from '@/components/StatusBadge';
import type { Rule, RuleListResponse } from '@/types';

export default function RulesPage() {
  const [data, setData] = useState<RuleListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      setData(await rulesApi.list({ severity: severityFilter || undefined }));
    } catch {}
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [severityFilter]);

  const fieldGroups = data?.items.reduce<Record<string, Rule[]>>((acc, rule) => {
    acc[rule.field] = acc[rule.field] || [];
    acc[rule.field].push(rule);
    return acc;
  }, {}) ?? {};

  return (
    <div className="page-container">
      <div className="page-header flex items-start justify-between">
        <div>
          <h1 className="page-title">Compliance Rules</h1>
          <p className="page-subtitle">
            Legal Metrology (Packaged Commodities) Rules, 2011 — Active rule set
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-slate-500" />
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="form-input w-36 text-sm"
          >
            <option value="">All Severity</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
            <option value="INFO">Info</option>
          </select>
        </div>
      </div>

      {/* Rule engine notice */}
      <div className="stub-notice mb-6 flex items-start gap-3">
        <Shield size={16} className="flex-shrink-0 mt-0.5 text-amber-400" />
        <div>
          <p className="font-semibold text-amber-400">Deterministic Rule Engine</p>
          <p className="text-xs mt-0.5 opacity-80">
            These rules are evaluated deterministically — no AI/LLM makes compliance decisions.
            Full rule evaluation is implemented in Phase 4. Phase 1 shows the rule catalog only.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64"><div className="spinner h-8 w-8" /></div>
      ) : (
        <div className="space-y-6">
          {Object.entries(fieldGroups).map(([field, rules]) => (
            <div key={field} className="card-static">
              <div className="flex items-center gap-2 mb-4">
                <BookOpen size={15} className="text-indigo-400" />
                <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
                  {field.replace(/_/g, ' ')}
                </h2>
                <span className="text-xs text-slate-500">({rules.length} rule{rules.length !== 1 ? 's' : ''})</span>
              </div>
              <div className="space-y-3">
                {rules.map((rule) => (
                  <div key={rule.id} className={`p-4 rounded-lg border transition-colors
                    ${rule.is_active ? 'border-indigo-500/15 bg-slate-800/30' : 'border-slate-700/30 bg-slate-900/20 opacity-50'}`}>
                    <div className="flex items-start gap-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <code className="text-xs font-mono text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded">
                            {rule.rule_id}
                          </code>
                          <StatusBadge status={rule.severity} />
                          {rule.mandatory && (
                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 font-medium">
                              Mandatory
                            </span>
                          )}
                          {!rule.is_active && (
                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-600/30 text-slate-500">
                              Inactive
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-slate-300">{rule.description}</p>
                        {rule.legal_reference && (
                          <p className="text-xs text-slate-500 mt-1.5 flex items-center gap-1">
                            <ExternalLink size={11} />
                            {rule.legal_reference}
                          </p>
                        )}
                        {rule.validation_logic && (
                          <div className="mt-2">
                            <span className="text-[10px] text-slate-600 uppercase tracking-wider font-medium">Validation: </span>
                            <code className="text-[10px] text-slate-500 font-mono">
                              {rule.validation_logic.type as string}
                            </code>
                          </div>
                        )}
                      </div>
                      <span className="text-xs text-slate-600 flex-shrink-0">v{rule.rule_version}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
          {Object.keys(fieldGroups).length === 0 && (
            <div className="text-center py-20 text-slate-500">
              <BookOpen size={40} className="mx-auto mb-3 opacity-30" />
              No rules found. Run the database seed to load initial rules.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
