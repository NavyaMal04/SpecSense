import React from 'react';
import { HelpCircle, BookOpen, Terminal, PhoneCall, Radio, X } from 'lucide-react';
import { playCyberSound } from '../utils/audio';

interface SupportModalProps {
  onClose: () => void;
}

export const SupportModal: React.FC<SupportModalProps> = ({ onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="glass-panel-glow max-w-xl w-full rounded-2xl p-6 relative border border-[#4cd7f6]/40 shadow-2xl">
        <div className="flex items-center justify-between pb-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#4cd7f6]/10 flex items-center justify-center border border-[#4cd7f6]/30 text-[#4cd7f6]">
              <HelpCircle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-[#dce1fb] font-sans">Operator Support & Manual</h3>
              <p className="font-mono text-xs text-[#4cd7f6]">SpecSense Precision Telemetry Reference</p>
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

        <div className="mt-4 space-y-3 font-mono text-xs">
          <div className="p-3 bg-[#151b2d] rounded-lg border border-white/5 space-y-1">
            <div className="flex items-center gap-2 text-[#4cd7f6] font-bold">
              <BookOpen className="w-4 h-4" />
              <span>Calibration Guidelines</span>
            </div>
            <p className="text-[#bcc9cd] text-[11px]">
              When accuracy drops below 99.5%, trigger the auto-collimation cycle or use the Terminal command <code className="text-[#4cd7f6]">scan --deep</code>.
            </p>
          </div>

          <div className="p-3 bg-[#151b2d] rounded-lg border border-white/5 space-y-1">
            <div className="flex items-center gap-2 text-[#4edea3] font-bold">
              <Radio className="w-4 h-4" />
              <span>Telemetry Ingestion API</span>
            </div>
            <p className="text-[#bcc9cd] text-[11px]">
              Real-time streams use binary WebSocket over TLS at <code className="text-[#4edea3]">wss://specsense.internal:8080/stream/v4</code>.
            </p>
          </div>

          <div className="p-3 bg-[#151b2d] rounded-lg border border-white/5 space-y-1">
            <div className="flex items-center gap-2 text-[#d0bcff] font-bold">
              <PhoneCall className="w-4 h-4" />
              <span>Emergency Engineering Dispatch</span>
            </div>
            <p className="text-[#bcc9cd] text-[11px]">
              Hardware triage hotline: Intercom channel #99-ALERT or call internal ext. 4200.
            </p>
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={() => {
              playCyberSound('click');
              onClose();
            }}
            className="px-4 py-2 bg-[#4cd7f6]/20 hover:bg-[#4cd7f6]/30 text-[#4cd7f6] rounded-lg font-mono text-xs font-bold border border-[#4cd7f6]/40 transition-colors"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
};
