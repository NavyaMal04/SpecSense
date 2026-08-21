import React, { useState, useRef, useEffect } from 'react';
import { Terminal as TerminalIcon, CornerDownLeft, Sparkles, Trash2, Cpu } from 'lucide-react';
import { playCyberSound } from '../utils/audio';

interface TerminalLine {
  id: string;
  type: 'input' | 'output' | 'error' | 'success' | 'system';
  text: string;
}

export const TerminalScreen: React.FC = () => {
  const [inputVal, setInputVal] = useState('');
  const [history, setHistory] = useState<TerminalLine[]>([
    { id: '1', type: 'system', text: 'SpecSense Precision Operations CLI [Version 4.19.0-RT]' },
    { id: '2', type: 'system', text: 'Connected to SpecSense telemetry stream (Host: 10.240.0.1:8080)' },
    { id: '3', type: 'system', text: 'Type "help" to view available diagnostic commands or click command chips below.' },
  ]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history]);

  const runCommand = (cmd: string) => {
    const trimmed = cmd.trim();
    if (!trimmed) return;

    playCyberSound('click');

    const newHistory: TerminalLine[] = [
      ...history,
      { id: Date.now().toString(), type: 'input', text: `$ ${trimmed}` }
    ];

    const lower = trimmed.toLowerCase();

    if (lower === 'clear') {
      setHistory([]);
      setInputVal('');
      return;
    }

    if (lower === 'help') {
      newHistory.push(
        { id: (Date.now() + 1).toString(), type: 'output', text: 'AVAILABLE COMMANDS:' },
        { id: (Date.now() + 2).toString(), type: 'output', text: '  status          - Query real-time health across all 14,293 catalog assets.' },
        { id: (Date.now() + 3).toString(), type: 'output', text: '  telemetry       - Stream current telemetry packet throughput and integrity.' },
        { id: (Date.now() + 4).toString(), type: 'output', text: '  anomalies       - List active pending anomalies requiring operator triage.' },
        { id: (Date.now() + 5).toString(), type: 'output', text: '  scan --deep     - Execute full spectral and phase coherence validation.' },
        { id: (Date.now() + 6).toString(), type: 'output', text: '  resolve-all     - Auto-remediate pending drift anomalies with firmware patches.' },
        { id: (Date.now() + 7).toString(), type: 'output', text: '  benchmark       - Benchmark edge FPGA neural coprocessor TOPS throughput.' },
        { id: (Date.now() + 8).toString(), type: 'output', text: '  ping gw-core    - Check optical bridge latency to gateway router.' },
        { id: (Date.now() + 9).toString(), type: 'output', text: '  clear           - Clear terminal buffer.' }
      );
    } else if (lower === 'status') {
      newHistory.push(
        { id: (Date.now() + 1).toString(), type: 'success', text: 'SYSTEM STATUS: OPTIMAL (14,293 / 14,293 nodes responding)' },
        { id: (Date.now() + 2).toString(), type: 'output', text: '  - Sensors Bay: 4,200 units (99.9% uptime)' },
        { id: (Date.now() + 3).toString(), type: 'output', text: '  - Optics Array: 3,150 units (99.8% accuracy)' },
        { id: (Date.now() + 4).toString(), type: 'output', text: '  - Actuators Grid: 5,100 units (nominal torque)' },
        { id: (Date.now() + 5).toString(), type: 'output', text: '  - Logic Matrix: 1,843 units (48.2 TOPS active)' }
      );
    } else if (lower === 'telemetry') {
      newHistory.push(
        { id: (Date.now() + 1).toString(), type: 'output', text: '[TELEMETRY STREAM METRICS]' },
        { id: (Date.now() + 2).toString(), type: 'output', text: '  Data Integrity: 94% processed (Extracted: 82%, Inferred: 12%, Flagged: 6%)' },
        { id: (Date.now() + 3).toString(), type: 'output', text: '  Carrier: 40.0 kHz | Jitter: ±0.4 ps | Bandwidth: 18.2 Gbps' }
      );
    } else if (lower === 'anomalies') {
      newHistory.push(
        { id: (Date.now() + 1).toString(), type: 'error', text: '⚠ 42 PENDING ANOMALIES DETECTED:' },
        { id: (Date.now() + 2).toString(), type: 'output', text: '  1. ERR-OPT-882 (OPT-3120-X): Phase Angle Variance (14.8 mrad > 2.0 mrad)' },
        { id: (Date.now() + 3).toString(), type: 'output', text: '  2. ERR-ACT-409 (ACT-5100-M): Core Temperature (78.4°C > 65.0°C)' },
        { id: (Date.now() + 4).toString(), type: 'output', text: '  3. WARN-SNS-991 (SNS-4200-Q): Resonance Shift (±4.2 Hz > ±0.5 Hz)' },
        { id: (Date.now() + 5).toString(), type: 'output', text: '  ... +39 additional items in queue. Run "resolve-all" to batch auto-tune.' }
      );
    } else if (lower === 'scan --deep') {
      playCyberSound('scan');
      newHistory.push(
        { id: (Date.now() + 1).toString(), type: 'system', text: '>> Initiating deep spectral scan across 14,293 nodes...' },
        { id: (Date.now() + 2).toString(), type: 'output', text: '>> Scanning Laser Interferometer prisms... [OK]' },
        { id: (Date.now() + 3).toString(), type: 'output', text: '>> Validating Piezo PWM frequencies... [OK]' },
        { id: (Date.now() + 4).toString(), type: 'success', text: '>> DEEP SCAN COMPLETE: 99.8% Accuracy Verified. Zero fatal hardware faults.' }
      );
    } else if (lower === 'resolve-all') {
      playCyberSound('success');
      newHistory.push(
        { id: (Date.now() + 1).toString(), type: 'success', text: '>> Broadcasted auto-calibration payload to 42 anomaly nodes.' },
        { id: (Date.now() + 2).toString(), type: 'success', text: '>> All 42 anomalies calibrated to within ±0.01% nominal threshold.' }
      );
    } else if (lower.startsWith('ping')) {
      newHistory.push(
        { id: (Date.now() + 1).toString(), type: 'output', text: 'PING 10.240.0.1 (gw-core): 56 data bytes' },
        { id: (Date.now() + 2).toString(), type: 'output', text: '64 bytes from 10.240.0.1: icmp_seq=1 ttl=64 time=0.214 ms' },
        { id: (Date.now() + 3).toString(), type: 'output', text: '64 bytes from 10.240.0.1: icmp_seq=2 ttl=64 time=0.198 ms' },
        { id: (Date.now() + 4).toString(), type: 'success', text: '--- 10.240.0.1 ping statistics: 0% packet loss, min/avg = 0.198/0.206 ms' }
      );
    } else if (lower === 'benchmark') {
      newHistory.push(
        { id: (Date.now() + 1).toString(), type: 'output', text: '>> Running neural coprocessor matrix tensor benchmark...' },
        { id: (Date.now() + 2).toString(), type: 'success', text: '>> Result: 48.2 TOPS sustained @ 52.3°C (99.99% throughput efficiency)' }
      );
    } else {
      newHistory.push({
        id: (Date.now() + 1).toString(),
        type: 'error',
        text: `Command not recognized: "${trimmed}". Type "help" for a list of valid commands.`
      });
    }

    setHistory(newHistory);
    setInputVal('');
  };

  const commandChips = [
    'help',
    'status',
    'telemetry',
    'anomalies',
    'scan --deep',
    'resolve-all',
    'benchmark',
    'ping gw-core'
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-2 border-b border-white/5">
        <div>
          <h2 className="text-3xl lg:text-4xl font-bold tracking-tight text-[#dce1fb] flex items-center gap-2">
            <TerminalIcon className="w-8 h-8 text-[#4cd7f6]" />
            SpecSense Cyber CLI
          </h2>
          <p className="font-mono text-sm text-[#bcc9cd] mt-1">
            Low-level diagnostic terminal and firmware command bus.
          </p>
        </div>

        <button
          onClick={() => {
            playCyberSound('click');
            setHistory([]);
          }}
          className="flex items-center gap-1 px-3 py-1.5 bg-[#191f31] hover:bg-white/10 text-[#869397] hover:text-white rounded-lg text-xs font-mono border border-white/10 transition-colors"
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>Clear</span>
        </button>
      </div>

      {/* Quick Command Chips */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs text-[#869397]">Quick Run:</span>
        {commandChips.map((chip) => (
          <button
            key={chip}
            onClick={() => runCommand(chip)}
            className="px-2.5 py-1 rounded bg-[#191f31] hover:bg-[#4cd7f6]/20 border border-[#4cd7f6]/30 text-[#4cd7f6] text-xs font-mono transition-colors"
          >
            {chip}
          </button>
        ))}
      </div>

      {/* Terminal Window */}
      <div className="glass-panel rounded-xl p-5 font-mono text-xs min-h-[480px] max-h-[560px] flex flex-col justify-between overflow-hidden border border-[#4cd7f6]/30 shadow-2xl">
        {/* Terminal Header Bar */}
        <div className="flex items-center justify-between pb-3 border-b border-white/10 text-[#869397] mb-3">
          <div className="flex items-center gap-2">
            <div className="flex gap-1.5">
              <span className="w-3 h-3 rounded-full bg-[#ff6b6b]/60 inline-block"></span>
              <span className="w-3 h-3 rounded-full bg-[#f6ad55]/60 inline-block"></span>
              <span className="w-3 h-3 rounded-full bg-[#4edea3]/60 inline-block"></span>
            </div>
            <span className="text-[11px] ml-2 text-[#bcc9cd]">root@specsense-core:~#</span>
          </div>
          <span className="text-[10px] text-[#4cd7f6]">SESSION ID: #9941-RT</span>
        </div>

        {/* Terminal Stream */}
        <div className="flex-1 overflow-y-auto space-y-1.5 pr-2">
          {history.map((line) => (
            <div
              key={line.id}
              className={`leading-relaxed ${
                line.type === 'input'
                  ? 'text-[#4cd7f6] font-bold'
                  : line.type === 'success'
                  ? 'text-[#4edea3]'
                  : line.type === 'error'
                  ? 'text-[#ffb4ab]'
                  : line.type === 'system'
                  ? 'text-[#d0bcff]'
                  : 'text-[#dce1fb]'
              }`}
            >
              {line.text}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Terminal Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            runCommand(inputVal);
          }}
          className="mt-4 pt-3 border-t border-white/10 flex items-center gap-2"
        >
          <span className="text-[#4cd7f6] font-bold">$</span>
          <input
            type="text"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder="Type command here (e.g., status, anomalies, scan --deep)..."
            className="flex-1 bg-transparent text-[#dce1fb] font-mono text-xs focus:outline-none placeholder:text-[#869397]"
            autoFocus
          />
          <button
            type="submit"
            className="p-1.5 text-[#4cd7f6] hover:bg-[#4cd7f6]/20 rounded transition-colors"
          >
            <CornerDownLeft className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
