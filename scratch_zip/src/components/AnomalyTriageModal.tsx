import React, { useState } from 'react';
import { AnomalyItem } from '../types';
import { 
  AlertTriangle, 
  CheckCircle, 
  Sliders, 
  ShieldAlert, 
  CheckCircle2, 
  Wrench, 
  XCircle, 
  Sparkles, 
  Filter, 
  Check, 
  RotateCcw 
} from 'lucide-react';
import { playCyberSound } from '../utils/audio';

interface AnomalyTriageModalProps {
  anomalies: AnomalyItem[];
  onClose: () => void;
  onResolveAnomaly: (id: string) => void;
  onQuarantineAnomaly: (id: string) => void;
  onResolveAll: () => void;
}

export const AnomalyTriageModal: React.FC<AnomalyTriageModalProps> = ({
  anomalies,
  onClose,
  onResolveAnomaly,
  onQuarantineAnomaly,
  onResolveAll,
}) => {
  const [filterSeverity, setFilterSeverity] = useState<'all' | 'critical' | 'warning' | 'info'>('all');
  const [filterCategory, setFilterCategory] = useState<'all' | 'Sensors' | 'Optics' | 'Actuators' | 'Logic'>('all');

  const filtered = anomalies.filter(a => {
    const matchesSev = filterSeverity === 'all' || a.severity === filterSeverity;
    const matchesCat = filterCategory === 'all' || a.category === filterCategory;
    return matchesSev && matchesCat;
  });

  const pendingCount = anomalies.filter(a => a.status === 'pending').length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="glass-panel-glow max-w-4xl w-full max-h-[85vh] rounded-2xl flex flex-col overflow-hidden border border-[#ff6b6b]/40 shadow-2xl shadow-[#ff6b6b]/10">
        {/* Header */}
        <div className="p-6 border-b border-white/10 bg-[#070d1f]/90 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#ff6b6b]/20 flex items-center justify-center border border-[#ff6b6b]/40 text-[#ffb4ab]">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-xl font-bold text-[#dce1fb]">Anomaly Triage Command</h3>
                <span className="px-2.5 py-0.5 rounded-full bg-[#ff6b6b]/20 text-[#ffb4ab] text-xs font-mono font-bold border border-[#ff6b6b]/40">
                  {pendingCount} Pending
                </span>
              </div>
              <p className="font-mono text-xs text-[#bcc9cd] mt-0.5">
                Telemetry variance detection and firmware auto-remediation queue.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {pendingCount > 0 && (
              <button
                onClick={() => {
                  playCyberSound('success');
                  onResolveAll();
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-[#4edea3] hover:bg-[#6ffbbe] text-[#003824] font-bold rounded-lg text-xs font-mono transition-all shadow-[0_0_15px_rgba(78,222,163,0.4)]"
              >
                <Sparkles className="w-4 h-4" />
                <span>Auto-Resolve All ({pendingCount})</span>
              </button>
            )}
            <button
              onClick={() => {
                playCyberSound('click');
                onClose();
              }}
              className="text-[#869397] hover:text-white p-1 rounded font-mono text-base"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="px-6 py-3 bg-[#151b2d]/90 border-b border-white/5 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
          <div className="flex items-center gap-2">
            <span className="text-[#869397]">Severity:</span>
            {(['all', 'critical', 'warning', 'info'] as const).map((sev) => (
              <button
                key={sev}
                onClick={() => {
                  playCyberSound('click');
                  setFilterSeverity(sev);
                }}
                className={`px-2.5 py-1 rounded capitalize transition-colors ${
                  filterSeverity === sev
                    ? 'bg-[#4cd7f6] text-[#003640] font-bold'
                    : 'text-[#bcc9cd] hover:text-white'
                }`}
              >
                {sev}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[#869397]">Category:</span>
            {(['all', 'Sensors', 'Optics', 'Actuators', 'Logic'] as const).map((cat) => (
              <button
                key={cat}
                onClick={() => {
                  playCyberSound('click');
                  setFilterCategory(cat);
                }}
                className={`px-2.5 py-1 rounded transition-colors ${
                  filterCategory === cat
                    ? 'bg-[#4cd7f6]/20 text-[#4cd7f6] border border-[#4cd7f6]/40 font-bold'
                    : 'text-[#869397] hover:text-[#dce1fb]'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Anomalies List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-3">
          {filtered.length === 0 ? (
            <div className="text-center py-12 font-mono text-sm text-[#4edea3] flex flex-col items-center gap-2">
              <CheckCircle2 className="w-10 h-10 text-[#4edea3]" />
              <p className="font-bold">Zero active anomalies in current filter!</p>
              <span className="text-xs text-[#869397]">All catalog telemetry operating within nominal ±0.01% tolerance.</span>
            </div>
          ) : (
            filtered.map((anom) => {
              const isResolved = anom.status === 'resolved';
              const isQuarantined = anom.status === 'quarantined';

              return (
                <div
                  key={anom.id}
                  className={`p-4 rounded-xl border transition-all ${
                    isResolved
                      ? 'bg-[#4edea3]/5 border-[#4edea3]/20 opacity-60'
                      : isQuarantined
                      ? 'bg-[#ff6b6b]/5 border-[#ff6b6b]/20 opacity-60'
                      : anom.severity === 'critical'
                      ? 'bg-[#191f31] border-[#ff6b6b]/40 hover:border-[#ff6b6b]'
                      : 'bg-[#191f31] border-white/10 hover:border-[#4cd7f6]/40'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                        anom.severity === 'critical'
                          ? 'bg-[#ff6b6b]/20 text-[#ffb4ab] border border-[#ff6b6b]/40'
                          : anom.severity === 'warning'
                          ? 'bg-[#f6ad55]/20 text-[#f6ad55] border border-[#f6ad55]/40'
                          : 'bg-[#4cd7f6]/20 text-[#4cd7f6] border border-[#4cd7f6]/40'
                      }`}>
                        {anom.code}
                      </span>
                      <span className="font-mono text-xs text-[#4cd7f6] font-semibold">{anom.assetId}</span>
                      <span className="text-xs font-mono text-[#869397]">({anom.category})</span>
                    </div>

                    <div className="flex items-center gap-2 text-xs font-mono text-[#869397]">
                      <span>{anom.timestamp}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] ${
                        isResolved ? 'bg-[#4edea3]/20 text-[#4edea3]' :
                        isQuarantined ? 'bg-[#ff6b6b]/20 text-[#ffb4ab]' :
                        'bg-white/5 text-[#bcc9cd]'
                      }`}>
                        {anom.status.toUpperCase()}
                      </span>
                    </div>
                  </div>

                  <h4 className="text-sm font-semibold text-[#dce1fb] mt-2">{anom.title}</h4>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2 font-mono text-xs">
                    <div className="p-2 bg-[#070d1f] rounded border border-white/5">
                      <span className="text-[#869397]">Telemetry Metric: </span>
                      <span className="text-[#dce1fb]">{anom.metric}</span>
                      <div className="flex justify-between mt-1 text-[11px]">
                        <span className="text-[#ffb4ab]">Actual: {anom.currentValue}</span>
                        <span className="text-[#4edea3]">Expected: {anom.expectedValue}</span>
                      </div>
                    </div>
                    <div className="p-2 bg-[#070d1f] rounded border border-white/5 text-[11px] text-[#bcc9cd] flex items-center">
                      <span>💡 <strong className="text-[#4cd7f6]">Remedy:</strong> {anom.resolutionSuggestion}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  {anom.status === 'pending' && (
                    <div className="mt-3 pt-3 border-t border-white/5 flex items-center justify-end gap-2 font-mono text-xs">
                      <button
                        onClick={() => {
                          playCyberSound('click');
                          onQuarantineAnomaly(anom.id);
                        }}
                        className="px-2.5 py-1 bg-white/5 hover:bg-[#ff6b6b]/20 text-[#ffb4ab] rounded border border-white/10 hover:border-[#ff6b6b]/30 transition-colors"
                      >
                        Quarantine Node
                      </button>
                      <button
                        onClick={() => {
                          playCyberSound('success');
                          onResolveAnomaly(anom.id);
                        }}
                        className="px-3 py-1 bg-[#4cd7f6]/15 hover:bg-[#4cd7f6]/30 text-[#4cd7f6] rounded border border-[#4cd7f6]/40 font-bold transition-all flex items-center gap-1.5"
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>Apply Calibration</span>
                      </button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
