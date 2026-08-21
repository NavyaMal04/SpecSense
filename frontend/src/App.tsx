import React, { useState, useEffect } from 'react';
import { ScreenType, CategoryData, AnomalyItem } from './types';
import { INITIAL_CATEGORIES, INITIAL_ANOMALIES } from './data/mockData';
import { Sidebar } from './components/Sidebar';
import { TelemetryScreen } from './components/TelemetryScreen';
import { DiagnosticsScreen } from './components/DiagnosticsScreen';
import { NetworkScreen } from './components/NetworkScreen';
import { ArchivesScreen } from './components/ArchivesScreen';
import { TerminalScreen } from './components/TerminalScreen';
import { AnomalyTriageModal } from './components/AnomalyTriageModal';
import { CategoryDetailModal } from './components/CategoryDetailModal';
import { SystemStatusModal } from './components/SystemStatusModal';
import { SupportModal } from './components/SupportModal';
import { setSoundMuted, getSoundMuted, playCyberSound } from './utils/audio';
import { Menu, X, Radio, Activity, CheckCircle, Sparkles, Bell } from 'lucide-react';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<ScreenType>('telemetry');
  const [categories, setCategories] = useState<CategoryData[]>(INITIAL_CATEGORIES);
  const [anomalies, setAnomalies] = useState<AnomalyItem[]>(INITIAL_ANOMALIES);
  
  // Real-time state metrics matching screenshot defaults
  const [totalAssets, setTotalAssets] = useState(14293);
  const [accuracyRate, setAccuracyRate] = useState(99.8);
  const [efficiencyHours, setEfficiencyHours] = useState(840);
  const [integrityPercent, setIntegrityPercent] = useState(94);
  const [extractedPercent, setExtractedPercent] = useState(82);
  const [inferredPercent, setInferredPercent] = useState(12);
  const [flaggedPercent, setFlaggedPercent] = useState(6);

  // Controls & Modals
  const [isSimulating, setIsSimulating] = useState(true);
  const [isMuted, setIsMuted] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  
  const [showAnomalyModal, setShowAnomalyModal] = useState(false);
  const [selectedCategoryModal, setSelectedCategoryModal] = useState<CategoryData | null>(null);
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [showSupportModal, setShowSupportModal] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Real-time live telemetry background pulse simulator
  useEffect(() => {
    if (!isSimulating) return;

    const interval = setInterval(() => {
      // Subtle fluctuations in numbers
      setTotalAssets((prev) => {
        const delta = (Math.random() > 0.6 ? 1 : 0) - (Math.random() > 0.8 ? 1 : 0);
        return Math.max(14200, prev + delta);
      });

      setAccuracyRate((prev) => {
        const jitter = (Math.random() - 0.5) * 0.04;
        const nextVal = Math.min(99.9, Math.max(99.4, prev + jitter));
        return parseFloat(nextVal.toFixed(1));
      });
    }, 4000);

    return () => clearInterval(interval);
  }, [isSimulating]);

  const handleToggleMute = () => {
    const nextState = !isMuted;
    setIsMuted(nextState);
    setSoundMuted(nextState);
  };

  const handleResolveAnomaly = (id: string) => {
    setAnomalies(prev => prev.map(a => a.id === id ? { ...a, status: 'resolved' } : a));
    showToast(`Anomaly ${id} recalibrated and resolved.`);
  };

  const handleQuarantineAnomaly = (id: string) => {
    setAnomalies(prev => prev.map(a => a.id === id ? { ...a, status: 'quarantined' } : a));
    showToast(`Node ${id} isolated and quarantined.`);
  };

  const handleResolveAllAnomalies = () => {
    setAnomalies(prev => prev.map(a => ({ ...a, status: 'resolved' })));
    setFlaggedPercent(0);
    setExtractedPercent(88);
    setAccuracyRate(99.9);
    showToast(`All 42 anomalies successfully auto-calibrated!`);
  };

  const handleTriggerCalibration = () => {
    playCyberSound('scan');
    showToast('Executing high-precision optical and PWM auto-tuning cycle...');
    setTimeout(() => {
      setAccuracyRate(99.9);
      setIntegrityPercent(98);
      setExtractedPercent(86);
      playCyberSound('success');
      showToast('System recalibration complete. Accuracy: 99.9% Optimal.');
    }, 1200);
  };

  const handleExportData = () => {
    playCyberSound('click');
    const snapshot = {
      timestamp: new Date().toISOString(),
      system: 'SpecSense Precision Operations',
      totalAssets,
      accuracyRate: `${accuracyRate}%`,
      dataIntegrity: {
        processed: `${integrityPercent}%`,
        extracted: `${extractedPercent}%`,
        inferred: `${inferredPercent}%`,
        flagged: `${flaggedPercent}%`
      },
      categories,
      pendingAnomalies: anomalies.filter(a => a.status === 'pending')
    };

    const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `specsense-telemetry-snapshot-${Date.now()}.json`;
    a.click();
    showToast('Telemetry JSON snapshot downloaded.');
  };

  return (
    <div className="min-h-screen bg-[#0c1324] text-[#dce1fb] font-sans relative overflow-x-hidden">
      {/* Background Matrix Gradients */}
      <div className="hex-bg fixed inset-0 z-0 pointer-events-none"></div>
      <div className="ambient-glow-tl"></div>
      <div className="ambient-glow-br"></div>
      <div className="ambient-glow-center"></div>

      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-6 right-6 z-50 glass-panel-glow px-4 py-3 rounded-xl border border-[#4cd7f6] text-xs font-mono text-[#dce1fb] shadow-2xl flex items-center gap-3 animate-fadeIn">
          <Sparkles className="w-4 h-4 text-[#4cd7f6] animate-pulse" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Mobile Top Navigation Header */}
      <div className="md:hidden flex items-center justify-between p-4 bg-[#070d1f]/90 backdrop-blur-md border-b border-white/10 relative z-30">
        <div>
          <h1 className="text-xl font-bold text-[#4cd7f6] glow-text">SpecSense</h1>
          <p className="font-mono text-[10px] text-[#4cd7f6]/70">Precision Operations</p>
        </div>
        <button
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          className="p-2 rounded-lg bg-[#191f31] text-[#4cd7f6] border border-white/10"
        >
          {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Main Layout */}
      <div className="flex h-screen relative z-10">
        {/* Desktop Sidebar */}
        <div className="hidden md:block">
          <Sidebar
            currentScreen={currentScreen}
            onSelectScreen={setCurrentScreen}
            anomaliesCount={anomalies.filter(a => a.status === 'pending').length}
            isSimulating={isSimulating}
            onToggleSimulation={() => setIsSimulating(!isSimulating)}
            isMuted={isMuted}
            onToggleMute={handleToggleMute}
            onOpenStatusModal={() => setShowStatusModal(true)}
            onOpenSupportModal={() => setShowSupportModal(true)}
          />
        </div>

        {/* Mobile Sidebar Overlay */}
        {isMobileMenuOpen && (
          <div className="fixed inset-0 z-50 bg-black/80 md:hidden animate-fadeIn">
            <div className="w-64 h-full">
              <Sidebar
                currentScreen={currentScreen}
                onSelectScreen={(screen) => {
                  setCurrentScreen(screen);
                  setIsMobileMenuOpen(false);
                }}
                anomaliesCount={anomalies.filter(a => a.status === 'pending').length}
                isSimulating={isSimulating}
                onToggleSimulation={() => setIsSimulating(!isSimulating)}
                isMuted={isMuted}
                onToggleMute={handleToggleMute}
                onOpenStatusModal={() => {
                  setShowStatusModal(true);
                  setIsMobileMenuOpen(false);
                }}
                onOpenSupportModal={() => {
                  setShowSupportModal(true);
                  setIsMobileMenuOpen(false);
                }}
              />
            </div>
          </div>
        )}

        {/* Main Content Area */}
        <main className="flex-1 md:ml-64 p-4 md:p-8 lg:p-10 overflow-y-auto min-h-screen">
          <div className="max-w-7xl mx-auto pb-12">
            {currentScreen === 'telemetry' && (
              <TelemetryScreen
                categories={categories}
                anomalies={anomalies}
                totalAssets={totalAssets}
                accuracyRate={accuracyRate}
                efficiencyHours={efficiencyHours}
                integrityPercent={integrityPercent}
                extractedPercent={extractedPercent}
                inferredPercent={inferredPercent}
                flaggedPercent={flaggedPercent}
                onOpenAnomalyTriage={() => setShowAnomalyModal(true)}
                onOpenCategoryDetail={(cat) => setSelectedCategoryModal(cat)}
                onTriggerCalibration={handleTriggerCalibration}
                onExportData={handleExportData}
              />
            )}

            {currentScreen === 'diagnostics' && <DiagnosticsScreen />}
            {currentScreen === 'network' && <NetworkScreen />}
            {currentScreen === 'archives' && <ArchivesScreen />}
            {currentScreen === 'terminal' && <TerminalScreen />}
          </div>
        </main>
      </div>

      {/* Anomaly Triage Drawer/Modal */}
      {showAnomalyModal && (
        <AnomalyTriageModal
          anomalies={anomalies}
          onClose={() => setShowAnomalyModal(false)}
          onResolveAnomaly={handleResolveAnomaly}
          onQuarantineAnomaly={handleQuarantineAnomaly}
          onResolveAll={handleResolveAllAnomalies}
        />
      )}

      {/* Category Detail Modal */}
      {selectedCategoryModal && (
        <CategoryDetailModal
          category={selectedCategoryModal}
          onClose={() => setSelectedCategoryModal(null)}
        />
      )}

      {/* System Status Modal */}
      {showStatusModal && (
        <SystemStatusModal onClose={() => setShowStatusModal(false)} />
      )}

      {/* Support & Docs Modal */}
      {showSupportModal && (
        <SupportModal onClose={() => setShowSupportModal(false)} />
      )}
    </div>
  );
}
