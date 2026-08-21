import React from 'react';
import { CheckCircle2, Server, Shield, Cpu, Clock, Zap, X, User } from 'lucide-react';
import { playCyberSound } from '../utils/audio';

interface SystemStatusModalProps {
  onClose: () => void;
}

export const SystemStatusModal: React.FC<SystemStatusModalProps> = ({ onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="glass-panel-glow max-w-xl w-full rounded-2xl p-6 relative border border-[#4edea3]/40 shadow-2xl">
        <div className="flex items-center justify-between pb-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#4edea3]/10 flex items-center justify-center border border-[#4edea3]/30 text-[#4edea3]">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-[#dce1fb] font-sans">System Status: Optimal</h3>
              <p className="font-mono text-xs text-[#4edea3]">SpecSense Core Telemetry Operating at 100% SLA</p>
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
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-[#151b2d] rounded-lg border border-white/5">
              <span className="text-[#869397] block text-[10px]">Telemetry Ingestion Rate:</span>
              <span className="text-xl text-[#4cd7f6] font-bold mt-1 block">14,293 ops/sec</span>
              <span className="text-[10px] text-[#4edea3]">Zero packet drop</span>
            </div>
            <div className="p-3 bg-[#151b2d] rounded-lg border border-white/5">
              <span className="text-[#869397] block text-[10px]">Uptime SLA:</span>
              <span className="text-xl text-[#4edea3] font-bold mt-1 block">99.998%</span>
              <span className="text-[10px] text-[#869397]">Continuous 90 Days</span>
            </div>
          </div>

          <div className="p-3.5 bg-[#070d1f] rounded-lg border border-white/5 space-y-2 text-[#bcc9cd]">
            <div className="flex items-center justify-between text-xs pb-2 border-b border-white/5">
              <span className="text-[#869397] flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-[#4cd7f6]" /> Current Operator:
              </span>
              <span className="text-[#4cd7f6] font-bold">OPR-7792 // LVL-4 ACCESS</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#869397]">Telemetry Bus Carrier:</span>
              <span className="text-[#4edea3]">40.0 kHz Optical Fiber</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#869397]">Hardware Acceleration:</span>
              <span className="text-[#dce1fb]">Edge FPGA Matrix (Active)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#869397]">Redundant Node Failover:</span>
              <span className="text-[#4edea3]">READY (Hot Standby)</span>
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
            Close Status
          </button>
        </div>
      </div>
    </div>
  );
};
