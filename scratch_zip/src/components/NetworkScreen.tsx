import React, { useState } from 'react';
import { NETWORK_NODES } from '../data/mockData';
import { NetworkNode } from '../types';
import { 
  Network as NetworkIcon, 
  Activity, 
  Server, 
  Wifi, 
  Zap, 
  RefreshCw, 
  CheckCircle, 
  AlertTriangle, 
  Cpu, 
  Radio 
} from 'lucide-react';
import { playCyberSound } from '../utils/audio';

export const NetworkScreen: React.FC = () => {
  const [nodes, setNodes] = useState<NetworkNode[]>(NETWORK_NODES);
  const [selectedNode, setSelectedNode] = useState<NetworkNode>(NETWORK_NODES[0]);
  const [isPinging, setIsPinging] = useState(false);
  const [filterStatus, setFilterStatus] = useState<'all' | 'online' | 'warning'>('all');

  const handlePingNode = (node: NetworkNode) => {
    playCyberSound('scan');
    setIsPinging(true);
    setTimeout(() => {
      setIsPinging(false);
      playCyberSound('success');
    }, 600);
  };

  const filteredNodes = nodes.filter(n => filterStatus === 'all' || n.status === filterStatus);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-2 border-b border-white/5">
        <div>
          <h2 className="text-3xl lg:text-4xl font-bold tracking-tight text-[#dce1fb]">
            Telemetry Network Topology
          </h2>
          <p className="font-mono text-sm text-[#bcc9cd] mt-1">
            Real-time optical bus mesh, gateway routing, and packet drop monitoring.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="bg-[#191f31] p-1 rounded-lg border border-white/10 flex items-center font-mono text-xs">
            <button
              onClick={() => { playCyberSound('click'); setFilterStatus('all'); }}
              className={`px-3 py-1.5 rounded transition-colors ${
                filterStatus === 'all' ? 'bg-[#4cd7f6] text-[#003640] font-bold' : 'text-[#bcc9cd]'
              }`}
            >
              All (10)
            </button>
            <button
              onClick={() => { playCyberSound('click'); setFilterStatus('online'); }}
              className={`px-3 py-1.5 rounded transition-colors ${
                filterStatus === 'online' ? 'bg-[#4edea3] text-[#003824] font-bold' : 'text-[#bcc9cd]'
              }`}
            >
              Online (8)
            </button>
            <button
              onClick={() => { playCyberSound('click'); setFilterStatus('warning'); }}
              className={`px-3 py-1.5 rounded transition-colors ${
                filterStatus === 'warning' ? 'bg-[#ff6b6b] text-white font-bold' : 'text-[#bcc9cd]'
              }`}
            >
              Warning (2)
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Visual Topology Canvas (8 Cols) */}
        <div className="lg:col-span-8 glass-panel rounded-xl p-6 relative min-h-[460px] flex flex-col justify-between overflow-hidden">
          <div className="flex items-center justify-between z-10">
            <span className="font-mono text-xs uppercase tracking-widest text-[#4cd7f6] font-bold flex items-center gap-2">
              <NetworkIcon className="w-4 h-4" />
              Mesh Topology Map (10.240.0.0/16)
            </span>
            <span className="font-mono text-xs text-[#869397]">Click any node to inspect telemetry</span>
          </div>

          {/* Canvas SVG overlay with connection wires */}
          <div className="relative w-full h-[360px] my-4 rounded-lg bg-[#070d1f]/60 border border-white/5 overflow-hidden">
            <svg className="w-full h-full absolute inset-0 pointer-events-none">
              {/* Lines between nodes */}
              <line x1="50%" y1="15%" x2="20%" y2="40%" stroke="rgba(76,215,246,0.3)" strokeWidth="2" strokeDasharray="4 2" />
              <line x1="50%" y1="15%" x2="50%" y2="45%" stroke="rgba(76,215,246,0.5)" strokeWidth="2" />
              <line x1="50%" y1="15%" x2="80%" y2="40%" stroke="rgba(76,215,246,0.3)" strokeWidth="2" strokeDasharray="4 2" />

              <line x1="20%" y1="40%" x2="12%" y2="75%" stroke="rgba(76,215,246,0.3)" strokeWidth="1.5" />
              <line x1="20%" y1="40%" x2="28%" y2="80%" stroke="rgba(255,107,107,0.4)" strokeWidth="1.5" />

              <line x1="50%" y1="45%" x2="42%" y2="78%" stroke="rgba(255,107,107,0.4)" strokeWidth="1.5" />
              <line x1="50%" y1="45%" x2="58%" y2="82%" stroke="rgba(76,215,246,0.3)" strokeWidth="1.5" />

              <line x1="80%" y1="40%" x2="72%" y2="76%" stroke="rgba(78,222,163,0.4)" strokeWidth="1.5" />
              <line x1="80%" y1="40%" x2="88%" y2="78%" stroke="rgba(78,222,163,0.4)" strokeWidth="1.5" />
            </svg>

            {/* Render Nodes as Interactive Buttons */}
            {filteredNodes.map((node) => {
              const isSelected = selectedNode.id === node.id;
              return (
                <button
                  key={node.id}
                  onClick={() => {
                    playCyberSound('click');
                    setSelectedNode(node);
                  }}
                  style={{ left: `${node.x}%`, top: `${node.y}%` }}
                  className={`absolute -translate-x-1/2 -translate-y-1/2 p-2.5 rounded-lg font-mono text-xs flex items-center gap-2 transition-all group z-20 ${
                    isSelected
                      ? 'bg-[#4cd7f6] text-[#003640] font-bold shadow-[0_0_20px_rgba(76,215,246,0.8)] scale-110'
                      : node.status === 'warning'
                      ? 'bg-[#ff6b6b]/20 text-[#ffb4ab] border border-[#ff6b6b]/60 hover:bg-[#ff6b6b]/40'
                      : 'bg-[#151b2d] text-[#dce1fb] border border-white/10 hover:border-[#4cd7f6]/50 hover:bg-[#191f31]'
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full ${
                    node.status === 'online' ? 'bg-[#4edea3]' : 'bg-[#ff6b6b] animate-ping'
                  }`}></span>
                  <span className="truncate max-w-[110px]">{node.name}</span>
                </button>
              );
            })}
          </div>

          <div className="flex items-center justify-between text-xs font-mono text-[#869397] pt-2 border-t border-white/5">
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#4edea3]"></span> Nominal Route
              <span className="w-2 h-2 rounded-full bg-[#ff6b6b] ml-3"></span> Congestion / Drift
            </span>
            <span className="text-[#4cd7f6]">Total Bandwidth: 18.2 Gbps</span>
          </div>
        </div>

        {/* Selected Node Inspector (4 Cols) */}
        <div className="lg:col-span-4 glass-panel rounded-xl p-6 flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <h3 className="font-mono text-xs uppercase tracking-widest text-[#4cd7f6] font-bold">
                Node Inspector
              </h3>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                selectedNode.status === 'online' ? 'bg-[#4edea3]/20 text-[#4edea3]' : 'bg-[#ff6b6b]/20 text-[#ffb4ab]'
              }`}>
                {selectedNode.status.toUpperCase()}
              </span>
            </div>

            <div className="mt-4 space-y-3 font-mono text-xs">
              <div>
                <span className="text-[#869397]">Node Name:</span>
                <p className="text-[#dce1fb] font-bold text-sm mt-0.5">{selectedNode.name}</p>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="p-2.5 rounded bg-[#151b2d] border border-white/5">
                  <span className="text-[#869397] block text-[10px]">IP Address:</span>
                  <span className="text-[#4cd7f6] font-bold">{selectedNode.ip}</span>
                </div>
                <div className="p-2.5 rounded bg-[#151b2d] border border-white/5">
                  <span className="text-[#869397] block text-[10px]">Ping Latency:</span>
                  <span className={`${selectedNode.ping > 2 ? 'text-[#ffb4ab]' : 'text-[#4edea3]'} font-bold`}>
                    {selectedNode.ping} ms
                  </span>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-[#869397]">CPU & Bus Load:</span>
                  <span className="text-[#4cd7f6] font-bold">{selectedNode.load}%</span>
                </div>
                <div className="w-full bg-[#151b2d] h-2 rounded-full overflow-hidden border border-white/5">
                  <div 
                    className={`h-full rounded-full transition-all ${
                      selectedNode.load > 75 ? 'bg-[#ff6b6b]' : 'bg-[#4cd7f6]'
                    }`}
                    style={{ width: `${selectedNode.load}%` }}
                  ></div>
                </div>
              </div>

              <div className="p-3 rounded bg-[#151b2d]/90 border border-white/5 text-[11px] text-[#bcc9cd] space-y-1">
                <div className="flex justify-between">
                  <span className="text-[#869397]">Packet Loss:</span>
                  <span className="text-[#4edea3]">0.001%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#869397]">Protocol:</span>
                  <span>TLS 1.3 / TelemetryStream</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#869397]">Firmware:</span>
                  <span>SpecOS v4.19-RT</span>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-2 pt-4 border-t border-white/10">
            <button
              onClick={() => handlePingNode(selectedNode)}
              disabled={isPinging}
              className="w-full py-2 bg-[#4cd7f6]/10 hover:bg-[#4cd7f6]/20 border border-[#4cd7f6]/40 text-[#4cd7f6] rounded-lg text-xs font-mono font-bold flex items-center justify-center gap-2 transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isPinging ? 'animate-spin' : ''}`} />
              {isPinging ? 'Sending ICMP Ping...' : 'Ping Node'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
