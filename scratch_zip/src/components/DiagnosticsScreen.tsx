import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  Play, 
  CheckCircle2, 
  AlertCircle, 
  RefreshCw, 
  ShieldCheck, 
  Sliders, 
  Radio, 
  Cpu, 
  Layers, 
  Flame, 
  Clock 
} from 'lucide-react';
import { playCyberSound } from '../utils/audio';

export const DiagnosticsScreen: React.FC = () => {
  const [isRunningScan, setIsRunningScan] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [activeTab, setActiveTab] = useState<'matrix' | 'spectral' | 'recalibration'>('matrix');
  const [waveOffset, setWaveOffset] = useState(0);

  // Animated waveform effect
  useEffect(() => {
    const interval = setInterval(() => {
      setWaveOffset((prev) => (prev + 1) % 100);
    }, 50);
    return () => clearInterval(interval);
  }, []);

  const handleStartScan = () => {
    playCyberSound('scan');
    setIsRunningScan(true);
    setScanProgress(0);

    const timer = setInterval(() => {
      setScanProgress((prev) => {
        if (prev >= 100) {
          clearInterval(timer);
          setIsRunningScan(false);
          playCyberSound('success');
          return 100;
        }
        return prev + 10;
      });
    }, 250);
  };

  const diagnosticChecks = [
    { name: 'Optics Collimation Array', id: 'DIAG-OPT-01', status: 'PASS', score: '99.4%', latency: '0.8ms', risk: 'Low' },
    { name: 'Piezoelectric PWM Frequency', id: 'DIAG-ACT-04', status: 'WARN', score: '92.1%', latency: '2.4ms', risk: 'Medium' },
    { name: 'Quantum MEMS Gyro Drift', id: 'DIAG-SNS-12', status: 'PASS', score: '99.9%', latency: '1.1ms', risk: 'Low' },
    { name: 'FPGA Neural Bus Bandwidth', id: 'DIAG-LOG-09', status: 'PASS', score: '100.0%', latency: '0.2ms', risk: 'Zero' },
    { name: 'Ultrasonic Pulse Coherence', id: 'DIAG-SNS-18', status: 'PASS', score: '97.8%', latency: '1.4ms', risk: 'Low' },
    { name: 'Thermal Dissipation Loop', id: 'DIAG-ACT-22', status: 'WARN', score: '88.5%', latency: '3.8ms', risk: 'Medium' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-2 border-b border-white/5">
        <div>
          <h2 className="text-3xl lg:text-4xl font-bold tracking-tight text-[#dce1fb]">
            Precision Diagnostics Engine
          </h2>
          <p className="font-mono text-sm text-[#bcc9cd] mt-1">
            Sub-millisecond telemetry matrix verification and spectral wave analysis.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="bg-[#191f31] p-1 rounded-lg border border-white/10 flex items-center font-mono text-xs">
            <button
              onClick={() => { playCyberSound('click'); setActiveTab('matrix'); }}
              className={`px-3 py-1.5 rounded transition-colors ${
                activeTab === 'matrix' ? 'bg-[#4cd7f6] text-[#003640] font-bold' : 'text-[#bcc9cd]'
              }`}
            >
              Health Matrix
            </button>
            <button
              onClick={() => { playCyberSound('click'); setActiveTab('spectral'); }}
              className={`px-3 py-1.5 rounded transition-colors ${
                activeTab === 'spectral' ? 'bg-[#4cd7f6] text-[#003640] font-bold' : 'text-[#bcc9cd]'
              }`}
            >
              Spectral Oscilloscope
            </button>
            <button
              onClick={() => { playCyberSound('click'); setActiveTab('recalibration'); }}
              className={`px-3 py-1.5 rounded transition-colors ${
                activeTab === 'recalibration' ? 'bg-[#4cd7f6] text-[#003640] font-bold' : 'text-[#bcc9cd]'
              }`}
            >
              Auto-Tune
            </button>
          </div>

          <button
            onClick={handleStartScan}
            disabled={isRunningScan}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-mono text-xs uppercase font-bold tracking-wider transition-all shadow-lg ${
              isRunningScan
                ? 'bg-[#4cd7f6]/20 text-[#4cd7f6] border border-[#4cd7f6]/50 animate-pulse'
                : 'bg-[#4cd7f6] text-[#003640] hover:bg-[#6ffbbe] shadow-[#4cd7f6]/20'
            }`}
          >
            {isRunningScan ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
            <span>{isRunningScan ? `Scanning (${scanProgress}%)` : 'Run Deep Scan'}</span>
          </button>
        </div>
      </div>

      {/* Real-time Oscilloscope Banner */}
      <div className="glass-panel rounded-xl p-6 relative overflow-hidden border border-[#4cd7f6]/20">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-[#4cd7f6] animate-pulse" />
            <span className="font-mono text-xs uppercase tracking-widest text-[#4cd7f6] font-bold">
              Real-Time Signal Frequency Oscilloscope (40.0 kHz Telemetry Carrier)
            </span>
          </div>
          <span className="font-mono text-xs text-[#4edea3]">LOCK: 99.98% Phase Alignment</span>
        </div>

        {/* Animated Wave Canvas representation */}
        <div className="h-32 w-full bg-[#070d1f]/90 rounded-lg p-2 relative overflow-hidden border border-white/5">
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-20">
            <div className="w-full border-b border-dashed border-[#4cd7f6]"></div>
          </div>
          <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 800 120">
            <path
              d={`M 0,60 ${Array.from({ length: 40 })
                .map((_, i) => {
                  const x = i * 20;
                  const y = 60 + Math.sin((i + waveOffset * 0.2) * 0.5) * 35 + Math.cos(i * 0.8) * 10;
                  return `L ${x},${y}`;
                })
                .join(' ')}`}
              fill="none"
              stroke="#4cd7f6"
              strokeWidth="2.5"
              className="drop-shadow-[0_0_8px_#4cd7f6]"
            />
            <path
              d={`M 0,60 ${Array.from({ length: 40 })
                .map((_, i) => {
                  const x = i * 20;
                  const y = 60 + Math.cos((i + waveOffset * 0.15) * 0.4) * 20;
                  return `L ${x},${y}`;
                })
                .join(' ')}`}
              fill="none"
              stroke="#4edea3"
              strokeWidth="1.5"
              strokeDasharray="4 2"
              className="opacity-70"
            />
          </svg>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4 text-xs font-mono text-[#bcc9cd]">
          <div className="p-2.5 rounded bg-[#151b2d] border border-white/5">
            <span className="text-[#869397]">Jitter:</span> <span className="text-[#4edea3] font-bold">±0.4 ps</span>
          </div>
          <div className="p-2.5 rounded bg-[#151b2d] border border-white/5">
            <span className="text-[#869397]">Harmonic Distortion:</span> <span className="text-[#4cd7f6] font-bold">-94.2 dB</span>
          </div>
          <div className="p-2.5 rounded bg-[#151b2d] border border-white/5">
            <span className="text-[#869397]">Signal-to-Noise:</span> <span className="text-[#4edea3] font-bold">118 dB</span>
          </div>
          <div className="p-2.5 rounded bg-[#151b2d] border border-white/5">
            <span className="text-[#869397]">Phase Coherence:</span> <span className="text-[#d0bcff] font-bold">99.98%</span>
          </div>
        </div>
      </div>

      {/* Main Diagnostic Table Matrix */}
      <div className="glass-panel rounded-xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-mono text-sm uppercase tracking-widest text-[#dce1fb] font-bold flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#4cd7f6]" />
            Subsystem Validation Matrix
          </h3>
          <span className="font-mono text-xs text-[#869397]">Last Full Verification: 14s ago</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="border-b border-white/10 text-[#869397] uppercase text-[10px] tracking-wider">
                <th className="py-3 px-4">Subsystem ID</th>
                <th className="py-3 px-4">Module Name</th>
                <th className="py-3 px-4">Validation Score</th>
                <th className="py-3 px-4">Bus Latency</th>
                <th className="py-3 px-4">Risk Profile</th>
                <th className="py-3 px-4 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {diagnosticChecks.map((item) => (
                <tr key={item.id} className="hover:bg-white/5 transition-colors">
                  <td className="py-3 px-4 text-[#4cd7f6] font-bold">{item.id}</td>
                  <td className="py-3 px-4 text-[#dce1fb]">{item.name}</td>
                  <td className="py-3 px-4">
                    <span className="text-[#4edea3] font-bold">{item.score}</span>
                  </td>
                  <td className="py-3 px-4 text-[#bcc9cd]">{item.latency}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-0.5 rounded text-[10px] ${
                      item.risk === 'Zero' ? 'bg-[#4edea3]/20 text-[#4edea3]' :
                      item.risk === 'Low' ? 'bg-[#4cd7f6]/20 text-[#4cd7f6]' :
                      'bg-[#ff6b6b]/20 text-[#ffb4ab]'
                    }`}>
                      {item.risk}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span className={`inline-flex items-center gap-1 font-bold ${
                      item.status === 'PASS' ? 'text-[#4edea3]' : 'text-[#ffb4ab]'
                    }`}>
                      {item.status === 'PASS' ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
                      {item.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
