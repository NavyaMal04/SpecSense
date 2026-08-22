import React, { useState, useEffect, useCallback } from 'react';
import { ScreenType, TelemetryResponse } from './types';
import { api } from './api';
import { Sidebar } from './components/Sidebar';
import { DashboardScreen } from './components/DashboardScreen';
import { ProductsScreen } from './components/ProductsScreen';
import { EnrichScreen } from './components/EnrichScreen';
import { ExportScreen } from './components/ExportScreen';
import { ProductDetailModal } from './components/ProductDetailModal';
import { ReviewQueueModal } from './components/ReviewQueueModal';
import { SystemStatusModal } from './components/SystemStatusModal';
import { SupportModal } from './components/SupportModal';
import { setSoundMuted, getSoundMuted, playCyberSound } from './utils/audio';
import { Menu, X, Sparkles } from 'lucide-react';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<ScreenType>('dashboard');
  const [telemetry, setTelemetry] = useState<TelemetryResponse | null>(null);
  const [telemetryLoading, setTelemetryLoading] = useState(true);
  const [apiConnected, setApiConnected] = useState(true);
  const [reviewQueueCount, setReviewQueueCount] = useState(0);
  const [refreshSignal, setRefreshSignal] = useState(0);

  const [isMuted, setIsMuted] = useState(getSoundMuted());
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const [showReviewQueue, setShowReviewQueue] = useState(false);
  const [selectedMpn, setSelectedMpn] = useState<string | null>(null);
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [showSupportModal, setShowSupportModal] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const loadTelemetry = useCallback(() => {
    setTelemetryLoading(true);
    api
      .getTelemetry()
      .then((res) => {
        setTelemetry(res);
        setApiConnected(true);
        const counts = res.batch_summary?.review_status_counts;
        // Fall back to fetching counts directly if batch summary is stale/missing.
        if (counts) {
          setReviewQueueCount((counts.pending || 0) + (counts.flagged || 0));
        }
      })
      .catch(() => setApiConnected(false))
      .finally(() => setTelemetryLoading(false));

    Promise.all([api.getProducts({ status: 'pending' }), api.getProducts({ status: 'flagged' })])
      .then(([pending, flagged]) => setReviewQueueCount(pending.total + flagged.total))
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadTelemetry();
  }, [loadTelemetry, refreshSignal]);

  const handleToggleMute = () => {
    const nextState = !isMuted;
    setIsMuted(nextState);
    setSoundMuted(nextState);
  };

  const refreshAll = () => setRefreshSignal((s) => s + 1);

  return (
    <div className="min-h-screen bg-[#0c1324] text-[#dce1fb] font-sans relative overflow-x-hidden">
      <div className="hex-bg fixed inset-0 z-0 pointer-events-none"></div>
      <div className="ambient-glow-tl"></div>
      <div className="ambient-glow-br"></div>
      <div className="ambient-glow-center"></div>

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
          <p className="font-mono text-[10px] text-[#4cd7f6]/70">Product Intelligence</p>
        </div>
        <button
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          className="p-2 rounded-lg bg-[#191f31] text-[#4cd7f6] border border-white/10"
        >
          {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      <div className="flex h-screen relative z-10">
        <div className="hidden md:block">
          <Sidebar
            currentScreen={currentScreen}
            onSelectScreen={setCurrentScreen}
            reviewQueueCount={reviewQueueCount}
            apiConnected={apiConnected}
            isMuted={isMuted}
            onToggleMute={handleToggleMute}
            onOpenStatusModal={() => setShowStatusModal(true)}
            onOpenSupportModal={() => setShowSupportModal(true)}
            onOpenReviewQueue={() => setShowReviewQueue(true)}
          />
        </div>

        {isMobileMenuOpen && (
          <div className="fixed inset-0 z-50 bg-black/80 md:hidden animate-fadeIn">
            <div className="w-64 h-full">
              <Sidebar
                currentScreen={currentScreen}
                onSelectScreen={(screen) => {
                  setCurrentScreen(screen);
                  setIsMobileMenuOpen(false);
                }}
                reviewQueueCount={reviewQueueCount}
                apiConnected={apiConnected}
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
                onOpenReviewQueue={() => {
                  setShowReviewQueue(true);
                  setIsMobileMenuOpen(false);
                }}
              />
            </div>
          </div>
        )}

        <main className="flex-1 md:ml-64 p-4 md:p-8 lg:p-10 overflow-y-auto min-h-screen">
          <div className="max-w-7xl mx-auto pb-12">
            {currentScreen === 'dashboard' && (
              <DashboardScreen
                telemetry={telemetry}
                loading={telemetryLoading}
                reviewQueueCount={reviewQueueCount}
                onOpenReviewQueue={() => setShowReviewQueue(true)}
                onRefresh={refreshAll}
                onGoToProducts={() => setCurrentScreen('products')}
              />
            )}

            {currentScreen === 'products' && (
              <ProductsScreen onOpenProduct={(mpn) => setSelectedMpn(mpn)} refreshSignal={refreshSignal} />
            )}

            {currentScreen === 'enrich' && (
              <EnrichScreen
                onEnriched={() => {
                  refreshAll();
                  showToast('Enrichment complete — record saved to the catalog.');
                }}
                onOpenProduct={(mpn) => setSelectedMpn(mpn)}
              />
            )}

            {currentScreen === 'export' && <ExportScreen />}
          </div>
        </main>
      </div>

      {selectedMpn && (
        <ProductDetailModal
          mpn={selectedMpn}
          onClose={() => setSelectedMpn(null)}
          onStatusChanged={refreshAll}
        />
      )}

      {showReviewQueue && (
        <ReviewQueueModal
          onClose={() => setShowReviewQueue(false)}
          onChanged={refreshAll}
          onOpenProduct={(mpn) => setSelectedMpn(mpn)}
        />
      )}

      {showStatusModal && <SystemStatusModal onClose={() => setShowStatusModal(false)} />}
      {showSupportModal && <SupportModal onClose={() => setShowSupportModal(false)} />}
    </div>
  );
}
