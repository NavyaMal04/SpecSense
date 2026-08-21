import React, { useState } from 'react';
import { CategoryData, AnomalyItem, CatalogAsset } from '../types';
import { 
  TrendingUp, 
  CheckCircle, 
  AlertTriangle, 
  BarChart2, 
  Zap, 
  Download, 
  SlidersHorizontal, 
  Sparkles, 
  Layers,
  ArrowUpRight,
  Info,
  RefreshCw
} from 'lucide-react';
import { playCyberSound } from '../utils/audio';

interface TelemetryScreenProps {
  categories: CategoryData[];
  anomalies: AnomalyItem[];
  totalAssets: number;
  accuracyRate: number;
  efficiencyHours: number;
  integrityPercent: number;
  extractedPercent: number;
  inferredPercent: number;
  flaggedPercent: number;
  onOpenAnomalyTriage: () => void;
  onOpenCategoryDetail: (category: CategoryData) => void;
  onTriggerCalibration: () => void;
  onExportData: () => void;
}

export const TelemetryScreen: React.FC<TelemetryScreenProps> = ({
  categories,
  anomalies,
  totalAssets,
  accuracyRate,
  efficiencyHours,
  integrityPercent,
  extractedPercent,
  inferredPercent,
  flaggedPercent,
  onOpenAnomalyTriage,
  onOpenCategoryDetail,
  onTriggerCalibration,
  onExportData,
}) => {
  const [activeMetricView, setActiveMetricView] = useState<'count' | 'bandwidth' | 'errors'>('count');
  const [timeRange, setTimeRange] = useState<'1h' | '6h' | '24h' | '7d'>('24h');
  const [selectedCategory, setSelectedCategory] = useState<CategoryData | null>(null);
  const [showEfficiencyBreakdown, setShowEfficiencyBreakdown] = useState(false);

  // Compute circumferences for SVG circular progress
  const radius = 45;
  const circumference = 2 * Math.PI * radius; // approx 282.74
  const strokeDashoffset = circumference - (integrityPercent / 100) * circumference;

  const pendingAnomaliesCount = anomalies.filter(a => a.status === 'pending').length;

  return (
    <div className="space-y-6">
      {/* Top Header Row with Title and Action Toolbar */}
      <header className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 pb-2 border-b border-white/5">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-4xl lg:text-5xl font-bold tracking-tight text-[#dce1fb] font-sans">
              Catalog Dashboard
            </h2>
            <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#4cd7f6]/10 text-[#4cd7f6] text-xs font-mono border border-[#4cd7f6]/30">
              <span className="w-1.5 h-1.5 rounded-full bg-[#4cd7f6] animate-pulse"></span>
              LIVE TELEMETRY
            </span>
          </div>
          <p className="font-mono text-sm text-[#bcc9cd] mt-2">
            Real-time system telemetry and asset tracking.
          </p>
        </div>

        {/* Action Toolbar */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Time Range Pills */}
          <div className="bg-[#191f31]/90 border border-white/10 rounded-lg p-1 flex items-center gap-1">
            {(['1h', '6h', '24h', '7d'] as const).map((t) => (
              <button
                key={t}
                onClick={() => {
                  playCyberSound('click');
                  setTimeRange(t);
                }}
                className={`px-2.5 py-1 text-xs font-mono uppercase rounded transition-colors ${
                  timeRange === t
                    ? 'bg-[#4cd7f6] text-[#003640] font-bold shadow-[0_0_10px_rgba(76,215,246,0.5)]'
                    : 'text-[#bcc9cd] hover:text-[#dce1fb] hover:bg-white/5'
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {/* Quick Calibrate Button */}
          <button
            onClick={() => {
              playCyberSound('scan');
              onTriggerCalibration();
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#191f31] hover:bg-[#23293c] border border-[#4cd7f6]/30 hover:border-[#4cd7f6] text-[#4cd7f6] rounded-lg text-xs font-mono transition-all shadow-[0_0_10px_rgba(76,215,246,0.1)]"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Calibrate</span>
          </button>

          {/* Export Report */}
          <button
            onClick={() => {
              playCyberSound('click');
              onExportData();
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#4cd7f6]/10 hover:bg-[#4cd7f6]/20 border border-[#4cd7f6]/40 text-[#4cd7f6] rounded-lg text-xs font-mono transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Snapshot</span>
          </button>
        </div>
      </header>

      {/* Row 1: Summary Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1: Total Assets */}
        <div 
          onClick={() => {
            playCyberSound('click');
            onOpenCategoryDetail(categories[0]);
          }}
          className="glass-panel rounded-xl p-6 relative overflow-hidden group cursor-pointer transition-all duration-300 hover:border-[#4cd7f6]/40 hover:shadow-[0_0_25px_rgba(76,215,246,0.15)]"
        >
          <div className="absolute -right-4 -top-4 w-24 h-24 bg-[#4cd7f6]/10 rounded-full blur-xl group-hover:bg-[#4cd7f6]/25 transition-all"></div>
          
          <div className="flex items-center justify-between">
            <h3 className="font-mono text-xs uppercase tracking-widest text-[#bcc9cd] font-bold">
              Total Assets
            </h3>
            <ArrowUpRight className="w-4 h-4 text-[#869397] group-hover:text-[#4cd7f6] transition-colors" />
          </div>

          <div className="text-4xl lg:text-5xl font-bold tracking-tight text-[#4cd7f6] glow-text my-2 font-sans">
            {totalAssets.toLocaleString()}
          </div>

          <div className="mt-4 flex items-center gap-2 text-[#4edea3] font-mono text-sm font-medium">
            <TrendingUp className="w-4 h-4 text-sm" />
            <span>+2.4% vs last cycle</span>
          </div>
        </div>

        {/* Card 2: Accuracy Rate */}
        <div 
          onClick={() => {
            playCyberSound('scan');
            onTriggerCalibration();
          }}
          className="glass-panel rounded-xl p-6 relative overflow-hidden group cursor-pointer transition-all duration-300 hover:border-[#4edea3]/40 hover:shadow-[0_0_25px_rgba(78,222,163,0.15)]"
        >
          <div className="absolute -right-4 -top-4 w-24 h-24 bg-[#4edea3]/10 rounded-full blur-xl group-hover:bg-[#4edea3]/25 transition-all"></div>

          <div className="flex items-center justify-between">
            <h3 className="font-mono text-xs uppercase tracking-widest text-[#bcc9cd] font-bold">
              Accuracy Rate
            </h3>
            <CheckCircle className="w-4 h-4 text-[#4edea3] opacity-70" />
          </div>

          <div className="text-4xl lg:text-5xl font-bold tracking-tight text-[#4edea3] glow-text-emerald my-2 font-sans">
            {accuracyRate.toFixed(1)}%
          </div>

          <div className="mt-4 flex items-center gap-2 text-[#4edea3] font-mono text-sm font-medium">
            <CheckCircle className="w-4 h-4 text-sm" />
            <span>Threshold Optimal</span>
          </div>
        </div>

        {/* Card 3: Pending Anomalies */}
        <div 
          onClick={() => {
            playCyberSound('alert');
            onOpenAnomalyTriage();
          }}
          className={`glass-panel rounded-xl p-6 relative overflow-hidden group cursor-pointer transition-all duration-300 border ${
            pendingAnomaliesCount > 0 
              ? 'border-[#ff6b6b]/40 hover:border-[#ff6b6b] hover:shadow-[0_0_30px_rgba(255,107,107,0.25)]' 
              : 'border-[#4edea3]/30'
          }`}
        >
          <div className="absolute -right-4 -top-4 w-24 h-24 bg-[#ff6b6b]/15 rounded-full blur-xl group-hover:bg-[#ff6b6b]/30 transition-all"></div>

          <div className="flex items-center justify-between">
            <h3 className="font-mono text-xs uppercase tracking-widest text-[#bcc9cd] font-bold">
              Pending Anomalies
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#ff6b6b]/20 text-[#ffb4ab] border border-[#ff6b6b]/40 animate-pulse">
              Triage (42)
            </span>
          </div>

          <div className="text-4xl lg:text-5xl font-bold tracking-tight text-[#ffb4ab] glow-text-error my-2 font-sans">
            {pendingAnomaliesCount}
          </div>

          <div className="mt-4 flex items-center gap-2 text-[#ffb4ab] font-mono text-sm font-medium">
            <AlertTriangle className="w-4 h-4 text-sm animate-bounce" />
            <span>Action Required</span>
          </div>
        </div>
      </div>

      {/* Row 2: Charts & Breakdown Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Main Chart: Products by Category (8 Cols) */}
        <div className="lg:col-span-8 glass-panel rounded-xl p-6 flex flex-col min-h-[460px] relative">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
            <h3 className="font-mono text-xs uppercase tracking-widest text-[#bcc9cd] font-bold flex items-center gap-2">
              <span>Products by Category</span>
              <span className="text-[11px] font-normal text-[#869397] font-mono">(Click bar to inspect)</span>
            </h3>

            <div className="flex items-center gap-3">
              <div className="flex items-center bg-[#151b2d] p-1 rounded-lg border border-white/5 text-[11px] font-mono">
                <button
                  onClick={() => {
                    playCyberSound('click');
                    setActiveMetricView('count');
                  }}
                  className={`px-2 py-0.5 rounded transition-colors ${
                    activeMetricView === 'count' ? 'bg-[#4cd7f6]/20 text-[#4cd7f6] font-bold' : 'text-[#869397]'
                  }`}
                >
                  Units
                </button>
                <button
                  onClick={() => {
                    playCyberSound('click');
                    setActiveMetricView('bandwidth');
                  }}
                  className={`px-2 py-0.5 rounded transition-colors ${
                    activeMetricView === 'bandwidth' ? 'bg-[#4cd7f6]/20 text-[#4cd7f6] font-bold' : 'text-[#869397]'
                  }`}
                >
                  Throughput
                </button>
                <button
                  onClick={() => {
                    playCyberSound('click');
                    setActiveMetricView('errors');
                  }}
                  className={`px-2 py-0.5 rounded transition-colors ${
                    activeMetricView === 'errors' ? 'bg-[#4cd7f6]/20 text-[#4cd7f6] font-bold' : 'text-[#869397]'
                  }`}
                >
                  Error %
                </button>
              </div>
              <BarChart2 className="text-[#4cd7f6] w-4 h-4" />
            </div>
          </div>

          {/* Chart Content Area with Simulated Grid Lines */}
          <div className="flex-1 flex items-end gap-4 md:gap-8 mt-auto relative min-h-[280px] pb-3">
            {/* Simulated Grid Lines */}
            <div className="absolute inset-0 flex flex-col justify-between pointer-events-none opacity-15">
              <div className="border-b border-[#4cd7f6] w-full flex justify-between text-[10px] font-mono text-[#4cd7f6] pt-1">
                <span>5,500</span>
                <span>MAX THRESHOLD</span>
              </div>
              <div className="border-b border-[#4cd7f6] w-full flex justify-between text-[10px] font-mono text-[#4cd7f6] pt-1">
                <span>3,750</span>
              </div>
              <div className="border-b border-[#4cd7f6] w-full flex justify-between text-[10px] font-mono text-[#4cd7f6] pt-1">
                <span>2,000</span>
              </div>
              <div className="border-b border-[#4cd7f6] w-full"></div>
            </div>

            {/* 4 Interactive Category Bars Matching Screenshot */}
            {categories.map((cat) => {
              // Calculate height percentage based on metric
              let heightPercent = cat.percentage;
              let displayVal = cat.count.toLocaleString();
              let subLabel = `${cat.activeNodes} Active`;

              if (activeMetricView === 'bandwidth') {
                if (cat.id === 'sensors') { heightPercent = 65; displayVal = '1.4 Gbps'; }
                if (cat.id === 'optics') { heightPercent = 88; displayVal = '4.2 Gbps'; }
                if (cat.id === 'actuators') { heightPercent = 50; displayVal = '0.9 Gbps'; }
                if (cat.id === 'logic') { heightPercent = 94; displayVal = '12.8 Gbps'; }
              } else if (activeMetricView === 'errors') {
                if (cat.id === 'sensors') { heightPercent = 25; displayVal = '0.04%'; }
                if (cat.id === 'optics') { heightPercent = 18; displayVal = '0.02%'; }
                if (cat.id === 'actuators') { heightPercent = 45; displayVal = '0.12%'; }
                if (cat.id === 'logic') { heightPercent = 12; displayVal = '0.01%'; }
              }

              return (
                <div 
                  key={cat.id} 
                  className="flex-1 flex flex-col items-center gap-3 z-10 h-full justify-end group cursor-pointer"
                  onClick={() => {
                    playCyberSound('tab');
                    onOpenCategoryDetail(cat);
                  }}
                >
                  {/* The Bar */}
                  <div className="w-full relative flex items-end justify-center h-[260px]">
                    <div 
                      style={{ height: `${heightPercent}%` }}
                      className={`w-full bg-gradient-to-t ${cat.gradient} rounded-t-sm relative transition-all duration-500 group-hover:brightness-125 group-hover:shadow-[0_0_20px_rgba(76,215,246,0.3)]`}
                    >
                      {/* Floating Tooltip matching screenshot style */}
                      <div className="absolute -top-10 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-[#0c1324] px-2.5 py-1 rounded text-xs font-mono text-[#4cd7f6] border border-[#4cd7f6]/40 shadow-xl whitespace-nowrap z-20 pointer-events-none">
                        <span className="font-bold">{displayVal}</span>
                      </div>

                      {/* Top neon edge strip */}
                      <div className="w-full h-1 bg-white/40 absolute top-0 left-0 rounded-t-sm shadow-[0_0_8px_#ffffff]"></div>
                    </div>
                  </div>

                  {/* Category Label */}
                  <div className="text-center">
                    <span className="font-mono text-xs text-[#bcc9cd] group-hover:text-[#4cd7f6] transition-colors font-medium">
                      {cat.name}
                    </span>
                    <span className="block text-[10px] font-mono text-[#869397] group-hover:text-[#dce1fb]">
                      {cat.count.toLocaleString()}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Chart Sub-footer with category quick chips */}
          <div className="pt-4 border-t border-white/5 grid grid-cols-2 sm:grid-cols-4 gap-3 mt-2">
            {categories.map((cat) => (
              <div 
                key={cat.id} 
                className="p-2 rounded bg-[#151b2d]/60 border border-white/5 hover:border-[#4cd7f6]/30 transition-colors cursor-pointer"
                onClick={() => onOpenCategoryDetail(cat)}
              >
                <div className="flex items-center justify-between text-[11px] font-mono text-[#869397]">
                  <span>{cat.name}</span>
                  <span className="text-[#4cd7f6]">{cat.errorRate} err</span>
                </div>
                <div className="text-xs font-mono text-[#dce1fb] font-semibold mt-0.5">
                  {cat.count.toLocaleString()} assets
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Data Integrity & Efficiency Delta (4 Cols) */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          {/* Data Integrity Card */}
          <div className="glass-panel rounded-xl p-6 flex-1 flex flex-col items-center justify-center relative min-h-[320px]">
            <h3 className="font-mono text-xs uppercase tracking-widest text-[#bcc9cd] font-bold absolute top-6 left-6 flex items-center gap-1.5">
              <span>Data Integrity</span>
            </h3>

            {/* Circular Progress Gauge with exact styling */}
            <div className="relative w-48 h-48 mt-8 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90 absolute inset-0" viewBox="0 0 100 100">
                {/* Background Ring */}
                <circle 
                  cx="50" 
                  cy="50" 
                  r={radius} 
                  fill="none" 
                  stroke="rgba(255,255,255,0.06)" 
                  strokeWidth="6"
                />
                {/* Glowing Progress Arc */}
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

              {/* Center percentage label */}
              <div className="flex flex-col items-center z-10 text-center">
                <div className="text-5xl font-bold tracking-tight text-[#4cd7f6] glow-text leading-none font-sans">
                  {integrityPercent}<span className="text-2xl font-light">%</span>
                </div>
                <span className="font-mono text-[10px] text-[#4cd7f6] tracking-widest uppercase mt-2 font-bold">
                  Processed
                </span>
              </div>
            </div>

            {/* Progress Breakdown Bars */}
            <div className="w-full mt-6 space-y-3">
              {/* Extracted */}
              <div>
                <div className="flex justify-between items-center font-mono text-xs mb-1">
                  <span className="text-[#bcc9cd]">Extracted</span>
                  <span className="text-[#4cd7f6] font-bold">{extractedPercent}%</span>
                </div>
                <div className="w-full bg-[#191f31] h-1.5 rounded-full overflow-hidden border border-white/5">
                  <div 
                    className="bg-[#4cd7f6] h-full shadow-[0_0_8px_#4cd7f6] transition-all duration-700 rounded-full" 
                    style={{ width: `${extractedPercent}%` }}
                  ></div>
                </div>
              </div>

              {/* Inferred */}
              <div>
                <div className="flex justify-between items-center font-mono text-xs mb-1">
                  <span className="text-[#bcc9cd]">Inferred</span>
                  <span className="text-[#4edea3] font-bold">{inferredPercent}%</span>
                </div>
                <div className="w-full bg-[#191f31] h-1.5 rounded-full overflow-hidden border border-white/5">
                  <div 
                    className="bg-[#4edea3] h-full shadow-[0_0_8px_#4edea3] transition-all duration-700 rounded-full" 
                    style={{ width: `${inferredPercent}%` }}
                  ></div>
                </div>
              </div>

              {/* Flagged */}
              <div>
                <div className="flex justify-between items-center font-mono text-xs mb-1">
                  <span className="text-[#bcc9cd]">Flagged</span>
                  <span className="text-[#ffb4ab] font-bold">{flaggedPercent}%</span>
                </div>
                <div className="w-full bg-[#191f31] h-1.5 rounded-full overflow-hidden border border-white/5">
                  <div 
                    className="bg-[#ffb4ab] h-full shadow-[0_0_8px_#ffb4ab] transition-all duration-700 rounded-full" 
                    style={{ width: `${flaggedPercent}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>

          {/* Efficiency Report Card */}
          <div 
            onClick={() => {
              playCyberSound('click');
              setShowEfficiencyBreakdown(!showEfficiencyBreakdown);
            }}
            className="glass-panel rounded-xl p-6 relative overflow-hidden flex items-center justify-between group cursor-pointer hover:border-[#4cd7f6]/40 transition-all shadow-[0_0_20px_rgba(76,215,246,0.05)]"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-[#4cd7f6]/10 to-transparent opacity-40"></div>

            <div className="relative z-10">
              <h3 className="font-mono text-xs uppercase tracking-widest text-[#bcc9cd] font-bold mb-1">
                Efficiency Delta
              </h3>
              <div className="text-3xl lg:text-4xl font-bold tracking-tight text-[#4cd7f6] glow-text font-sans">
                {efficiencyHours} <span className="text-lg text-[#4cd7f6]/70 font-normal">hrs</span>
              </div>
              <div className="font-mono text-xs text-[#4edea3] mt-1 font-medium flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                <span>Saved this quarter</span>
              </div>
            </div>

            {/* Glowing Bolt Icon Circle */}
            <div className="relative z-10 w-16 h-16 bg-[#191f31]/90 rounded-full flex items-center justify-center border border-[#4cd7f6]/40 shadow-[0_0_20px_rgba(76,215,246,0.3)] animate-pulse group-hover:scale-105 transition-transform">
              <Zap className="text-[#4cd7f6] w-7 h-7" />
            </div>
          </div>
        </div>
      </div>

      {/* Efficiency Breakdown Expandable Drawer (if toggled) */}
      {showEfficiencyBreakdown && (
        <div className="glass-panel rounded-xl p-5 border border-[#4cd7f6]/30 animate-fadeIn space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="font-mono text-sm font-bold text-[#4cd7f6] flex items-center gap-2">
              <Zap className="w-4 h-4 text-[#4cd7f6]" />
              Quarterly Telemetry Automation ROI
            </h4>
            <span className="text-xs font-mono text-[#869397]">Calculated from 14,293 active telemetry nodes</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-xs">
            <div className="p-3 bg-[#151b2d] rounded-lg border border-white/5">
              <span className="text-[#869397]">Automated Diagnostics:</span>
              <p className="text-lg text-[#dce1fb] font-bold mt-1">420 hrs saved</p>
              <span className="text-[10px] text-[#4edea3]">98.2% auto-remediated</span>
            </div>
            <div className="p-3 bg-[#151b2d] rounded-lg border border-white/5">
              <span className="text-[#869397]">Anomaly Pre-emption:</span>
              <p className="text-lg text-[#dce1fb] font-bold mt-1">290 hrs saved</p>
              <span className="text-[10px] text-[#4cd7f6]">Zero line stops</span>
            </div>
            <div className="p-3 bg-[#151b2d] rounded-lg border border-white/5">
              <span className="text-[#869397]">Dynamic Recalibration:</span>
              <p className="text-lg text-[#dce1fb] font-bold mt-1">130 hrs saved</p>
              <span className="text-[10px] text-[#d0bcff]">Continuous uptime</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
