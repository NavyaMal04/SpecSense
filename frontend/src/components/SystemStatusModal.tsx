import React, { useEffect, useState } from 'react';
import { CheckCircle2, XCircle, X, Loader2 } from 'lucide-react';
import { playCyberSound } from '../utils/audio';
import { api } from '../api';
import { TelemetryResponse } from '../types';

interface SystemStatusModalProps {
  onClose: () => void;
}

export const SystemStatusModal: React.FC<SystemStatusModalProps> = ({ onClose }) => {
  const [connected, setConnected] = useState<boolean | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryResponse | null>(null);

  useEffect(() => {
    api
      .ping()
      .then(() => setConnected(true))
      .catch(() => setConnected(false));
    api.getTelemetry().then(setTelemetry).catch(() => {});
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className={`glass-panel-glow max-w-xl w-full rounded-2xl p-6 relative border shadow-2xl ${connected ? 'border-[#4edea3]/40' : 'border-[#ff6b6b]/40'}`}>
        <div className="flex items-center justify-between pb-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center border ${connected ? 'bg-[#4edea3]/10 border-[#4edea3]/30 text-[#4edea3]' : 'bg-[#ff6b6b]/10 border-[#ff6b6b]/30 text-[#ff6b6b]'}`}>
              {connected === null ? <Loader2 className="w-6 h-6 animate-spin" /> : connected ? <CheckCircle2 className="w-6 h-6" /> : <XCircle className="w-6 h-6" />}
            </div>
            <div>
              <h3 className="text-xl font-bold text-[#dce1fb] font-sans">
                {connected === null ? 'Checking connection…' : connected ? 'Everything is running' : 'Connection issue'}
              </h3>
              <p className="font-mono text-xs text-[#869397]">
                {connected === null ? '' : connected ? 'The catalog is up to date and reachable.' : 'The catalog could not be reached.'}
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              playCyberSound('click');
              onClose();
            }}
            className="text-[#869397] hover:text-white p-1"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="mt-4 space-y-4 font-mono text-xs">
          {!connected && connected !== null && (
            <div className="p-3.5 bg-[#151b2d] rounded-lg border border-[#ff6b6b]/20 text-[#ffb4ab]">
              We couldn't load your catalog right now. Try refreshing, or check back in a moment.
            </div>
          )}

          <div className="p-3 bg-[#151b2d] rounded-lg border border-white/5">
            <span className="text-[#869397] block text-[10px]">Total Products:</span>
            <span className="text-xl text-[#4edea3] font-bold mt-1 block">{telemetry?.total_records ?? '—'}</span>
          </div>

          <div className="p-3.5 bg-[#070d1f] rounded-lg border border-white/5 space-y-2 text-[#bcc9cd]">
            <div className="flex justify-between">
              <span className="text-[#869397]">Extracted fields:</span>
              <span className="text-[#4cd7f6]">{telemetry?.provenance.extracted_pct ?? '—'}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#869397]">Inferred fields:</span>
              <span className="text-[#4edea3]">{telemetry?.provenance.inferred_pct ?? '—'}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#869397]">Unavailable fields:</span>
              <span className="text-[#ffb4ab]">{telemetry?.provenance.unavailable_pct ?? '—'}%</span>
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={() => {
              playCyberSound('click');
              onClose();
            }}
            className="px-4 py-2 bg-[#4edea3]/20 hover:bg-[#4edea3]/30 text-[#4edea3] font-bold rounded-lg font-mono text-xs border border-[#4edea3]/40 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
