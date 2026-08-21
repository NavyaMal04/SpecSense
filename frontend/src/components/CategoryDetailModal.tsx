import React from 'react';
import { CategoryData } from '../types';
import { Layers, Activity, Cpu, CheckCircle, Radio, X } from 'lucide-react';
import { playCyberSound } from '../utils/audio';

interface CategoryDetailModalProps {
  category: CategoryData;
  onClose: () => void;
}

export const CategoryDetailModal: React.FC<CategoryDetailModalProps> = ({ category, onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="glass-panel-glow max-w-xl w-full rounded-2xl p-6 relative border border-[#4cd7f6]/40 shadow-2xl">
        <div className="flex items-center justify-between pb-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#4cd7f6]/10 flex items-center justify-center border border-[#4cd7f6]/30 text-[#4cd7f6]">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-[#dce1fb] font-sans">{category.name} Telemetry Cluster</h3>
              <p className="font-mono text-xs text-[#4cd7f6]">{category.description}</p>
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
              <span className="text-[#869397] block text-[10px]">Total Monitored Assets:</span>
              <span className="text-2xl text-[#4cd7f6] font-bold mt-1 block">{category.count.toLocaleString()}</span>
              <span className="text-[10px] text-[#4edea3]">{(category.activeNodes / category.count * 100).toFixed(1)}% Operational</span>
            </div>
            <div className="p-3 bg-[#151b2d] rounded-lg border border-white/5">
              <span className="text-[#869397] block text-[10px]">Telemetry Latency:</span>
              <span className="text-2xl text-[#4edea3] font-bold mt-1 block">{category.avgLatency}</span>
              <span className="text-[10px] text-[#869397]">Jitter: ±0.05ms</span>
            </div>
          </div>

          <div className="p-3.5 bg-[#070d1f] rounded-lg border border-white/5 space-y-2">
            <div className="flex justify-between">
              <span className="text-[#869397]">Active Telemetry Nodes:</span>
              <span className="text-[#dce1fb] font-bold">{category.activeNodes} / {category.count}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#869397]">Error Rate:</span>
              <span className="text-[#4edea3] font-bold">{category.errorRate}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#869397]">Telemetry Polling Cycle:</span>
              <span className="text-[#4cd7f6] font-bold">100 Hz (10ms interval)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#869397]">Firmware Calibration:</span>
              <span className="text-[#d0bcff] font-bold">AUTO-PHASE LOCK V4</span>
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={() => {
              playCyberSound('click');
              onClose();
            }}
            className="px-4 py-2 bg-[#4cd7f6]/20 hover:bg-[#4cd7f6]/30 text-[#4cd7f6] rounded-lg font-mono text-xs font-bold border border-[#4cd7f6]/40 transition-colors"
          >
            Acknowledge
          </button>
        </div>
      </div>
    </div>
  );
};
