import React, { useState, useRef, useEffect } from 'react';
import { api } from '../api';
import { EnrichResponse } from '../types';
import { Play, Terminal as TerminalIcon, CheckCircle2, XCircle } from 'lucide-react';
import { playCyberSound } from '../utils/audio';

export const EnrichScreen: React.FC<{ onEnriched: () => void; onOpenProduct: (mpn: string) => void }> = ({
  onEnriched,
  onOpenProduct,
}) => {
  const [mfgPartNum, setMfgPartNum] = useState('');
  const [partDesc, setPartDesc] = useState('');
  const [partManuf, setPartManuf] = useState('');
  const [brand, setBrand] = useState('-- Unbranded --');
  const [running, setRunning] = useState(false);
  const [log, setLog] = useState<string[]>([
    '$ specsense pipeline ready',
    '  waiting for input…',
  ]);
  const [result, setResult] = useState<EnrichResponse | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [log]);

  const appendLog = (line: string) => setLog((l) => [...l, line]);

  const runEnrichment = async () => {
    if (!mfgPartNum.trim()) return;
    setRunning(true);
    setResult(null);
    playCyberSound('scan');
    setLog([`$ specsense enrich --mpn "${mfgPartNum.trim()}"`, '  loading reference catalog…', '  fetching datasheet & web sources…', '  running Gemini extraction + inference…']);

    try {
      const res = await api.enrich({
        mfg_part_num: mfgPartNum.trim(),
        part_desc: partDesc,
        part_manuf: partManuf,
        e1_brand: brand,
      });
      appendLog(`  ✓ enrichment complete — ${res.completeness}% fields populated`);
      appendLog(`  saved record to data/batch_output/${res.mpn}.json`);
      setResult(res);
      onEnriched();
      playCyberSound('success');
    } catch (e: any) {
      appendLog(`  ✗ error: ${e.message || 'enrichment pipeline failed'}`);
      playCyberSound('alert');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      <header className="pb-2 border-b border-white/5">
        <h2 className="text-3xl lg:text-4xl font-bold tracking-tight text-[#dce1fb]">Run Enrichment</h2>
        <p className="font-mono text-sm text-[#bcc9cd] mt-1">
          Enrich a single product via the live extraction &amp; inference pipeline.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input form */}
        <div className="glass-panel rounded-xl p-6 space-y-4">
          <div>
            <label className="font-mono text-[11px] text-[#869397] uppercase tracking-widest">
              Mfg Part Number *
            </label>
            <input
              value={mfgPartNum}
              onChange={(e) => setMfgPartNum(e.target.value)}
              placeholder="e.g. D519127"
              className="w-full mt-1 bg-[#151b2d] border border-white/10 rounded-lg px-3 py-2 text-sm font-mono text-[#dce1fb] placeholder:text-[#5b6572] focus:outline-none focus:border-[#4cd7f6]/50"
            />
          </div>
          <div>
            <label className="font-mono text-[11px] text-[#869397] uppercase tracking-widest">
              Part Description
            </label>
            <input
              value={partDesc}
              onChange={(e) => setPartDesc(e.target.value)}
              placeholder="e.g. Heater Kit"
              className="w-full mt-1 bg-[#151b2d] border border-white/10 rounded-lg px-3 py-2 text-sm font-mono text-[#dce1fb] placeholder:text-[#5b6572] focus:outline-none focus:border-[#4cd7f6]/50"
            />
          </div>
          <div>
            <label className="font-mono text-[11px] text-[#869397] uppercase tracking-widest">
              Part Manufacturer / Distributor
            </label>
            <input
              value={partManuf}
              onChange={(e) => setPartManuf(e.target.value)}
              placeholder="e.g. V & V Appliance Parts Inc"
              className="w-full mt-1 bg-[#151b2d] border border-white/10 rounded-lg px-3 py-2 text-sm font-mono text-[#dce1fb] placeholder:text-[#5b6572] focus:outline-none focus:border-[#4cd7f6]/50"
            />
          </div>
          <div>
            <label className="font-mono text-[11px] text-[#869397] uppercase tracking-widest">
              E1 Brand
            </label>
            <input
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              className="w-full mt-1 bg-[#151b2d] border border-white/10 rounded-lg px-3 py-2 text-sm font-mono text-[#dce1fb] focus:outline-none focus:border-[#4cd7f6]/50"
            />
          </div>

          <button
            disabled={running || !mfgPartNum.trim()}
            onClick={runEnrichment}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-[#4cd7f6]/10 hover:bg-[#4cd7f6]/20 border border-[#4cd7f6]/40 text-[#4cd7f6] font-mono text-sm font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Play className="w-4 h-4" />
            {running ? 'Running…' : 'Run Enrichment'}
          </button>
        </div>

        {/* Terminal log */}
        <div className="glass-panel rounded-xl p-0 flex flex-col overflow-hidden min-h-[340px]">
          <div className="px-4 py-3 border-b border-white/10 bg-[#070d1f]/80 flex items-center gap-2">
            <TerminalIcon className="w-4 h-4 text-[#4cd7f6]" />
            <span className="font-mono text-xs text-[#bcc9cd]">pipeline output</span>
          </div>
          <div className="flex-1 p-4 font-mono text-xs text-[#4edea3] space-y-1 overflow-y-auto max-h-[340px] bg-[#070d1f]/40">
            {log.map((line, i) => (
              <div key={i} className={line.startsWith('$') ? 'text-[#4cd7f6]' : line.includes('✗') ? 'text-[#ffb4ab]' : ''}>
                {line}
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </div>
      </div>

      {result && (
        <div className="glass-panel rounded-xl p-6 border border-[#4edea3]/30 flex items-center justify-between gap-4 animate-fadeIn">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-6 h-6 text-[#4edea3]" />
            <div>
              <p className="font-mono text-sm text-[#dce1fb] font-semibold">
                {result.mpn} enriched at {result.completeness}% completeness
              </p>
              <p className="font-mono text-xs text-[#869397]">Saved to the catalog with review status: pending</p>
            </div>
          </div>
          <button
            onClick={() => onOpenProduct(result.mpn)}
            className="px-3.5 py-2 rounded-lg text-xs font-mono border border-[#4cd7f6]/40 text-[#4cd7f6] hover:bg-[#4cd7f6]/10 transition-colors"
          >
            View Record
          </button>
        </div>
      )}
    </div>
  );
};
