import React from 'react';
import { TelemetryResponse } from '../types';
import {
  TrendingUp,
  CheckCircle,
  AlertTriangle,
  BarChart2,
  Download,
  ArrowUpRight,
  RefreshCw,
  Clock,
} from 'lucide-react';
import { playCyberSound } from '../utils/audio';

interface DashboardScreenProps {
  telemetry: TelemetryResponse | null;
  loading: boolean;
  reviewQueueCount: number;
  onOpenReviewQueue: () => void;
  onRefresh: () => void;
  onGoToProducts: () => void;
  onExportSnapshot: () => void;
}

export const DashboardScreen: React.FC<DashboardScreenProps> = ({
  telemetry,
  loading,
  reviewQueueCount,
  onOpenReviewQueue,
  onRefresh,
  onGoToProducts,
  onExportSnapshot,
}) => {
  const provenance = telemetry?.provenance ?? {
    extracted_pct: 0,
    inferred_pct: 0,
    unavailable_pct: 0,
    counts: { extracted: 0, inferred: 0, unavailable: 0, total_fields: 0 },
  };
  const totalRecords = telemetry?.total_records ?? 0;
  const processedPct = Math.round(provenance.extracted_pct + provenance.inferred_pct);
  const sections = telemetry?.section_fill_rates ?? {};
  const sectionEntries = Object.entries(sections);
  const maxSectionVal = Math.max(1, ...sectionEntries.map(([, v]) => v));
  const summary = telemetry?.batch_summary;

  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (processedPct / 100) * circumference;

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 pb-2 border-b border-white/5">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-4xl lg:text-5xl font-bold tracking-tight text-[#dce1fb] font-sans">
              Catalog Dashboard
            </h2>
            <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#4cd7f6]/10 text-[#4cd7f6] text-xs font-mono border border-[#4cd7f6]/30">
              <span className="w-1.5 h-1.5 rounded-full bg-[#4cd7f6] animate-pulse"></span>
              LIVE
            </span>
          </div>
          <p className="font-mono text-sm text-[#bcc9cd] mt-2">
            Provenance and completeness across the enriched product catalog.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => {
              playCyberSound('scan');
              onRefresh();
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#191f31] hover:bg-[#23293c] border border-[#4cd7f6]/30 hover:border-[#4cd7f6] text-[#4cd7f6] rounded-lg text-xs font-mono transition-all shadow-[0_0_10px_rgba(76,215,246,0.1)]"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={() => {
              playCyberSound('click');
              onExportSnapshot();
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#4cd7f6]/10 hover:bg-[#4cd7f6]/20 border border-[#4cd7f6]/40 text-[#4cd7f6] rounded-lg text-xs font-mono transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Snapshot</span>
          </button>
        </div>
      </header>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div
          onClick={() => {
            playCyberSound('click');
            onGoToProducts();
          }}
          className="glass-panel rounded-xl p-6 relative overflow-hidden group cursor-pointer transition-all duration-300 hover:border-[#4cd7f6]/40 hover:shadow-[0_0_25px_rgba(76,215,246,0.15)]"
        >
          <div className="absolute -right-4 -top-4 w-24 h-24 bg-[#4cd7f6]/10 rounded-full blur-xl group-hover:bg-[#4cd7f6]/25 transition-all"></div>
          <div className="flex items-center justify-between">
            <h3 className="font-mono text-xs uppercase tracking-widest text-[#bcc9cd] font-bold">
              Total Products
            </h3>
            <ArrowUpRight className="w-4 h-4 text-[#869397] group-hover:text-[#4cd7f6] transition-colors" />
          </div>
          <div className="text-4xl lg:text-5xl font-bold tracking-tight text-[#4cd7f6] glow-text my-2 font-sans">
            {totalRecords.toLocaleString()}
          </div>
          <div className="mt-4 flex items-center gap-2 text-[#bcc9cd] font-mono text-sm font-medium">
            <TrendingUp className="w-4 h-4 text-sm" />
            <span>Records in batch_output/</span>
          </div>
        </div>

        <div className="glass-panel rounded-xl p-6 relative overflow-hidden group transition-all duration-300 hover:border-[#4edea3]/40 hover:shadow-[0_0_25px_rgba(78,222,163,0.15)]">
          <div className="absolute -right-4 -top-4 w-24 h-24 bg-[#4edea3]/10 rounded-full blur-xl group-hover:bg-[#4edea3]/25 transition-all"></div>
          <div className="flex items-center justify-between">
            <h3 className="font-mono text-xs uppercase tracking-widest text-[#bcc9cd] font-bold">
              Fields Processed
            </h3>
            <CheckCircle className="w-4 h-4 text-[#4edea3] opacity-70" />
          </div>
          <div className="text-4xl lg:text-5xl font-bold tracking-tight text-[#4edea3] glow-text-emerald my-2 font-sans">
            {processedPct}%
          </div>
          <div className="mt-4 flex items-center gap-2 text-[#4edea3] font-mono text-sm font-medium">
            <CheckCircle className="w-4 h-4 text-sm" />
            <span>{provenance.counts.total_fields.toLocaleString()} scalar fields tracked</span>
          </div>
        </div>

        <div
          onClick={() => {
            playCyberSound('alert');
            onOpenReviewQueue();
          }}
          className={`glass-panel rounded-xl p-6 relative overflow-hidden group cursor-pointer transition-all duration-300 border ${
            reviewQueueCount > 0
              ? 'border-[#ff6b6b]/40 hover:border-[#ff6b6b] hover:shadow-[0_0_30px_rgba(255,107,107,0.25)]'
              : 'border-[#4edea3]/30'
          }`}
        >
          <div className="absolute -right-4 -top-4 w-24 h-24 bg-[#ff6b6b]/15 rounded-full blur-xl group-hover:bg-[#ff6b6b]/30 transition-all"></div>
          <div className="flex items-center justify-between">
            <h3 className="font-mono text-xs uppercase tracking-widest text-[#bcc9cd] font-bold">
              Needs Review
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#ff6b6b]/20 text-[#ffb4ab] border border-[#ff6b6b]/40">
              Open Queue
            </span>
          </div>
          <div className="text-4xl lg:text-5xl font-bold tracking-tight text-[#ffb4ab] glow-text-error my-2 font-sans">
            {reviewQueueCount}
          </div>
          <div className="mt-4 flex items-center gap-2 text-[#ffb4ab] font-mono text-sm font-medium">
            <AlertTriangle className="w-4 h-4 text-sm" />
            <span>Pending or flagged products</span>
          </div>
        </div>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Section fill rates */}
        <div className="lg:col-span-8 glass-panel rounded-xl p-6 flex flex-col min-h-[420px] relative">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-mono text-xs uppercase tracking-widest text-[#bcc9cd] font-bold flex items-center gap-2">
              <span>Section Fill Rate</span>
              <span className="text-[11px] font-normal text-[#869397] font-mono">(% of fields with a value, per schema section)</span>
            </h3>
            <BarChart2 className="text-[#4cd7f6] w-4 h-4" />
          </div>

          {sectionEntries.length === 0 && (
            <p className="font-mono text-sm text-[#869397]">No records loaded yet.</p>
          )}

          <div className="space-y-4">
            {sectionEntries.map(([section, pct]) => (
              <div key={section}>
                <div className="flex justify-between items-center font-mono text-xs mb-1.5">
                  <span className="text-[#dce1fb]">{section}</span>
                  <span className="text-[#4cd7f6] font-bold">{pct}%</span>
                </div>
                <div className="w-full bg-[#191f31] h-2.5 rounded-full overflow-hidden border border-white/5">
                  <div
                    className="bg-gradient-to-r from-[#4cd7f6] to-[#4edea3] h-full shadow-[0_0_8px_#4cd7f6] transition-all duration-700 rounded-full"
                    style={{ width: `${(pct / maxSectionVal) * 100}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>

          {summary && (
            <div className="pt-5 mt-5 border-t border-white/5 flex flex-wrap gap-4 text-[11px] font-mono text-[#869397]">
              {summary.total_wall_clock_formatted && (
                <span className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5" /> Last batch run: {summary.total_wall_clock_formatted}
                </span>
              )}
              {typeof summary.total_processed === 'number' && (
                <span>Processed: {summary.total_processed}</span>
              )}
              {typeof summary.total_errored === 'number' && (
                <span>Errored: {summary.total_errored}</span>
              )}
              {typeof summary.total_skipped === 'number' && (
                <span>Skipped: {summary.total_skipped}</span>
              )}
            </div>
          )}
        </div>

        {/* Provenance gauge */}
        <div className="lg:col-span-4 glass-panel rounded-xl p-6 flex flex-col items-center justify-center relative min-h-[420px]">
          <h3 className="font-mono text-xs uppercase tracking-widest text-[#bcc9cd] font-bold absolute top-6 left-6">
            Field Provenance
          </h3>

          <div className="relative w-48 h-48 mt-8 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90 absolute inset-0" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
              <circle
                cx="50"
                cy="50"
                r={radius}
                fill="none"
                stroke="#4cd7f6"
                strokeWidth="6"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                className="drop-shadow-[0_0_10px_rgba(76,215,246,0.8)] transition-all duration-1000"
              />
            </svg>
            <div className="flex flex-col items-center z-10 text-center">
              <div className="text-5xl font-bold tracking-tight text-[#4cd7f6] glow-text leading-none font-sans">
                {processedPct}
                <span className="text-2xl font-light">%</span>
              </div>
              <span className="font-mono text-[10px] text-[#4cd7f6] tracking-widest uppercase mt-2 font-bold">
                Has a Value
              </span>
            </div>
          </div>

          <div className="w-full mt-6 space-y-3">
            <div>
              <div className="flex justify-between items-center font-mono text-xs mb-1">
                <span className="text-[#bcc9cd]">Extracted</span>
                <span className="text-[#4cd7f6] font-bold">{provenance.extracted_pct}%</span>
              </div>
              <div className="w-full bg-[#191f31] h-1.5 rounded-full overflow-hidden border border-white/5">
                <div className="bg-[#4cd7f6] h-full shadow-[0_0_8px_#4cd7f6] transition-all duration-700 rounded-full" style={{ width: `${provenance.extracted_pct}%` }}></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between items-center font-mono text-xs mb-1">
                <span className="text-[#bcc9cd]">Inferred</span>
                <span className="text-[#4edea3] font-bold">{provenance.inferred_pct}%</span>
              </div>
              <div className="w-full bg-[#191f31] h-1.5 rounded-full overflow-hidden border border-white/5">
                <div className="bg-[#4edea3] h-full shadow-[0_0_8px_#4edea3] transition-all duration-700 rounded-full" style={{ width: `${provenance.inferred_pct}%` }}></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between items-center font-mono text-xs mb-1">
                <span className="text-[#bcc9cd]">Unavailable</span>
                <span className="text-[#ffb4ab] font-bold">{provenance.unavailable_pct}%</span>
              </div>
              <div className="w-full bg-[#191f31] h-1.5 rounded-full overflow-hidden border border-white/5">
                <div className="bg-[#ffb4ab] h-full shadow-[0_0_8px_#ffb4ab] transition-all duration-700 rounded-full" style={{ width: `${provenance.unavailable_pct}%` }}></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
