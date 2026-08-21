import React, { useState } from 'react';
import { api } from '../api';
import { Download, FileJson, FileSpreadsheet, ShieldCheck } from 'lucide-react';
import { playCyberSound } from '../utils/audio';

export const ExportScreen: React.FC = () => {
  const [onlyApproved, setOnlyApproved] = useState(false);

  const download = (kind: 'csv' | 'json') => {
    playCyberSound('click');
    const url = api.exportUrl(kind, onlyApproved);
    const a = document.createElement('a');
    a.href = url;
    a.click();
  };

  return (
    <div className="space-y-6">
      <header className="pb-2 border-b border-white/5">
        <h2 className="text-3xl lg:text-4xl font-bold tracking-tight text-[#dce1fb]">Export Catalog</h2>
        <p className="font-mono text-sm text-[#bcc9cd] mt-1">
          Download the enriched catalog in Unilog delivery format or raw JSON.
        </p>
      </header>

      <div className="glass-panel rounded-xl p-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ShieldCheck className="w-5 h-5 text-[#4edea3]" />
          <div>
            <p className="font-mono text-sm text-[#dce1fb] font-semibold">Only include approved records</p>
            <p className="font-mono text-xs text-[#869397]">Exclude pending and flagged products from the export</p>
          </div>
        </div>
        <button
          onClick={() => setOnlyApproved((v) => !v)}
          className={`w-12 h-6 rounded-full transition-colors relative ${onlyApproved ? 'bg-[#4edea3]/40' : 'bg-white/10'}`}
        >
          <span
            className={`absolute top-0.5 w-5 h-5 rounded-full transition-transform ${
              onlyApproved ? 'translate-x-6 bg-[#4edea3]' : 'translate-x-0.5 bg-[#bcc9cd]'
            }`}
          ></span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-panel rounded-xl p-6 flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#4cd7f6]/10 border border-[#4cd7f6]/30 flex items-center justify-center">
              <FileSpreadsheet className="w-5 h-5 text-[#4cd7f6]" />
            </div>
            <div>
              <p className="font-mono text-sm text-[#dce1fb] font-semibold">Delivery Format CSV</p>
              <p className="font-mono text-xs text-[#869397]">Full 252-column Unilog delivery format</p>
            </div>
          </div>
          <button
            onClick={() => download('csv')}
            className="mt-auto flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-[#4cd7f6]/10 hover:bg-[#4cd7f6]/20 border border-[#4cd7f6]/40 text-[#4cd7f6] font-mono text-sm font-semibold transition-all"
          >
            <Download className="w-4 h-4" /> delivery_format.csv
          </button>
        </div>

        <div className="glass-panel rounded-xl p-6 flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#4edea3]/10 border border-[#4edea3]/30 flex items-center justify-center">
              <FileJson className="w-5 h-5 text-[#4edea3]" />
            </div>
            <div>
              <p className="font-mono text-sm text-[#dce1fb] font-semibold">Full Catalog JSON</p>
              <p className="font-mono text-xs text-[#869397]">Every field, including provenance and citations</p>
            </div>
          </div>
          <button
            onClick={() => download('json')}
            className="mt-auto flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-[#4edea3]/10 hover:bg-[#4edea3]/20 border border-[#4edea3]/40 text-[#4edea3] font-mono text-sm font-semibold transition-all"
          >
            <Download className="w-4 h-4" /> spec_sense_catalog.json
          </button>
        </div>
      </div>
    </div>
  );
};
