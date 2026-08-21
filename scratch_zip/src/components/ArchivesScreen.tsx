import React, { useState } from 'react';
import { MOCK_ASSETS } from '../data/mockData';
import { CatalogAsset } from '../types';
import { 
  Search, 
  Filter, 
  Download, 
  FolderGit2, 
  SlidersHorizontal, 
  ChevronRight, 
  FileText, 
  CheckCircle2, 
  AlertCircle,
  ExternalLink
} from 'lucide-react';
import { playCyberSound } from '../utils/audio';

export const ArchivesScreen: React.FC = () => {
  const [assets, setAssets] = useState<CatalogAsset[]>(MOCK_ASSETS);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedAsset, setSelectedAsset] = useState<CatalogAsset | null>(null);

  const filteredAssets = assets.filter((asset) => {
    const matchesSearch = asset.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          asset.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          asset.specNumber.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || asset.category.toLowerCase() === selectedCategory.toLowerCase();
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-2 border-b border-white/5">
        <div>
          <h2 className="text-3xl lg:text-4xl font-bold tracking-tight text-[#dce1fb]">
            Asset & Spec Archives
          </h2>
          <p className="font-mono text-sm text-[#bcc9cd] mt-1">
            Historical calibrations, hardware spec sheets, and telemetry telemetry logs.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              playCyberSound('click');
              const blob = new Blob([JSON.stringify(assets, null, 2)], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `specsense-catalog-archive-${new Date().toISOString().slice(0, 10)}.json`;
              a.click();
            }}
            className="flex items-center gap-2 px-3.5 py-1.5 bg-[#4cd7f6]/10 hover:bg-[#4cd7f6]/20 border border-[#4cd7f6]/40 text-[#4cd7f6] rounded-lg text-xs font-mono transition-all"
          >
            <Download className="w-4 h-4" />
            <span>Export Catalog (JSON)</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1 relative">
          <Search className="w-4 h-4 text-[#869397] absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by Asset ID, Spec #, or Component Name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-[#191f31] border border-white/10 rounded-lg text-xs font-mono text-[#dce1fb] placeholder:text-[#869397] focus:outline-none focus:border-[#4cd7f6]"
          />
        </div>

        {/* Category Pills */}
        <div className="flex items-center gap-1.5 bg-[#191f31] p-1 rounded-lg border border-white/10 overflow-x-auto">
          {['all', 'Sensors', 'Optics', 'Actuators', 'Logic'].map((cat) => (
            <button
              key={cat}
              onClick={() => {
                playCyberSound('click');
                setSelectedCategory(cat);
              }}
              className={`px-3 py-1 rounded text-xs font-mono capitalize transition-colors ${
                selectedCategory.toLowerCase() === cat.toLowerCase()
                  ? 'bg-[#4cd7f6] text-[#003640] font-bold'
                  : 'text-[#bcc9cd] hover:text-[#dce1fb]'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Asset Table Matrix */}
      <div className="glass-panel rounded-xl overflow-hidden border border-white/10">
        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="bg-[#070d1f]/80 border-b border-white/10 text-[#869397] uppercase text-[10px] tracking-wider">
                <th className="py-3.5 px-4">Asset ID</th>
                <th className="py-3.5 px-4">Component Name</th>
                <th className="py-3.5 px-4">Category</th>
                <th className="py-3.5 px-4">Spec #</th>
                <th className="py-3.5 px-4">Throughput</th>
                <th className="py-3.5 px-4">Drift Rate</th>
                <th className="py-3.5 px-4">Health</th>
                <th className="py-3.5 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filteredAssets.map((asset) => (
                <tr 
                  key={asset.id} 
                  className="hover:bg-white/5 transition-colors cursor-pointer"
                  onClick={() => {
                    playCyberSound('click');
                    setSelectedAsset(asset);
                  }}
                >
                  <td className="py-3.5 px-4 text-[#4cd7f6] font-bold">{asset.id}</td>
                  <td className="py-3.5 px-4 text-[#dce1fb] font-medium">{asset.name}</td>
                  <td className="py-3.5 px-4">
                    <span className="px-2 py-0.5 rounded bg-[#151b2d] border border-white/10 text-[#bcc9cd] text-[10px]">
                      {asset.category}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-[#869397]">{asset.specNumber}</td>
                  <td className="py-3.5 px-4 text-[#bcc9cd]">{asset.throughput}</td>
                  <td className="py-3.5 px-4 text-[#4edea3]">{asset.drift}</td>
                  <td className="py-3.5 px-4">
                    <span className={`inline-flex items-center gap-1 font-bold ${
                      asset.health > 95 ? 'text-[#4edea3]' : 'text-[#ffb4ab]'
                    }`}>
                      {asset.health}%
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <button className="text-[#4cd7f6] hover:text-[#acedff] inline-flex items-center gap-1">
                      <span>Inspect</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Asset Detail Drawer / Modal */}
      {selectedAsset && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
          <div className="glass-panel-glow max-w-xl w-full rounded-2xl p-6 relative border border-[#4cd7f6]/40 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-white/10">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-[#4cd7f6]" />
                <h3 className="font-bold text-lg text-[#dce1fb]">{selectedAsset.name}</h3>
              </div>
              <button
                onClick={() => setSelectedAsset(null)}
                className="text-[#869397] hover:text-white font-mono text-sm"
              >
                ✕
              </button>
            </div>

            <div className="mt-4 space-y-4 font-mono text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-[#151b2d] rounded-lg">
                  <span className="text-[#869397] block text-[10px]">Spec ID:</span>
                  <span className="text-[#4cd7f6] font-bold text-sm">{selectedAsset.specNumber}</span>
                </div>
                <div className="p-3 bg-[#151b2d] rounded-lg">
                  <span className="text-[#869397] block text-[10px]">Firmware Revision:</span>
                  <span className="text-[#dce1fb] font-bold text-sm">{selectedAsset.revision}</span>
                </div>
                <div className="p-3 bg-[#151b2d] rounded-lg">
                  <span className="text-[#869397] block text-[10px]">Operating Temperature:</span>
                  <span className="text-[#4edea3] font-bold text-sm">{selectedAsset.temperature}</span>
                </div>
                <div className="p-3 bg-[#151b2d] rounded-lg">
                  <span className="text-[#869397] block text-[10px]">Last Telemetry Ping:</span>
                  <span className="text-[#bcc9cd] font-bold text-sm">{selectedAsset.lastPing}</span>
                </div>
              </div>

              <div className="p-3 bg-[#070d1f] rounded-lg border border-white/5">
                <span className="text-[#869397] block text-[10px] mb-1">Raw Telemetry Packet (JSON):</span>
                <pre className="text-[11px] text-[#4cd7f6] overflow-x-auto">
{JSON.stringify({
  assetId: selectedAsset.id,
  spec: selectedAsset.specNumber,
  carrierHz: 40000,
  coherenceIndex: selectedAsset.health / 100,
  thermalVariance: '+0.12 C/min',
  crcCheck: '0x88F1A2C9'
}, null, 2)}
                </pre>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setSelectedAsset(null)}
                className="px-4 py-2 bg-white/10 hover:bg-white/20 text-[#dce1fb] rounded-lg font-mono text-xs"
              >
                Close Spec
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
