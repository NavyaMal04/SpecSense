import React from 'react';
import { ScreenType } from '../types';
import {
  LayoutDashboard,
  PackageSearch,
  Sparkles,
  Download,
  HelpCircle,
  Volume2,
  VolumeX,
  CheckCircle2,
  XCircle,
  ClipboardList,
} from 'lucide-react';
import { playCyberSound } from '../utils/audio';

interface SidebarProps {
  currentScreen: ScreenType;
  onSelectScreen: (screen: ScreenType) => void;
  reviewQueueCount: number;
  apiConnected: boolean;
  isMuted: boolean;
  onToggleMute: () => void;
  onOpenStatusModal: () => void;
  onOpenSupportModal: () => void;
  onOpenReviewQueue: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentScreen,
  onSelectScreen,
  reviewQueueCount,
  apiConnected,
  isMuted,
  onToggleMute,
  onOpenStatusModal,
  onOpenSupportModal,
  onOpenReviewQueue,
}) => {
  const navItems = [
    {
      id: 'dashboard' as ScreenType,
      label: 'Dashboard',
      icon: LayoutDashboard,
      badge: null as string | null,
      badgeColor: '',
    },
    {
      id: 'products' as ScreenType,
      label: 'Products',
      icon: PackageSearch,
      badge: null as string | null,
      badgeColor: '',
    },
    {
      id: 'enrich' as ScreenType,
      label: 'Add Product',
      icon: Sparkles,
      badge: null as string | null,
      badgeColor: '',
    },
    {
      id: 'export' as ScreenType,
      label: 'Export',
      icon: Download,
      badge: null as string | null,
      badgeColor: '',
    },
  ];

  return (
    <nav className="w-64 bg-[#070d1f]/80 backdrop-blur-md border-r border-[#4cd7f6]/20 flex flex-col h-screen fixed left-0 top-0 z-40 select-none shadow-2xl shadow-[#4cd7f6]/5">
      {/* Brand Header */}
      <div className="px-6 pt-7 pb-6 border-b border-white/5">
        <div className="flex items-center justify-between">
          <div>
            <h1
              className="text-2xl font-bold tracking-tight text-[#4cd7f6] glow-text cursor-pointer flex items-center gap-2"
              onClick={() => {
                playCyberSound('tab');
                onSelectScreen('dashboard');
              }}
            >
              <span>SpecSense</span>
              <span
                className={`w-2 h-2 rounded-full ${apiConnected ? 'bg-[#4cd7f6] animate-ping' : 'bg-[#ff6b6b]'} opacity-75`}
              ></span>
            </h1>
            <p className="font-mono text-xs text-[#4cd7f6]/70 mt-1 tracking-wider uppercase font-semibold">
              Product Intelligence
            </p>
          </div>
        </div>
      </div>

      {/* Navigation Items */}
      <div className="flex-1 py-6 px-3 space-y-1.5 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-mono uppercase tracking-widest text-[#869397]">
          Navigation
        </div>
        {navItems.map((item) => {
          const isActive = currentScreen === item.id;
          const Icon = item.icon;

          return (
            <button
              key={item.id}
              onClick={() => {
                playCyberSound('tab');
                onSelectScreen(item.id);
              }}
              className={`w-full flex items-center justify-between px-3.5 py-3 rounded-md transition-all duration-200 group text-left ${
                isActive
                  ? 'bg-[#4cd7f6]/10 text-[#4cd7f6] border-l-4 border-[#4cd7f6] shadow-[inset_0_0_15px_rgba(76,215,246,0.15)] font-semibold'
                  : 'text-[#bcc9cd] hover:bg-white/5 hover:text-[#4cd7f6] border-l-4 border-transparent'
              }`}
            >
              <div className="flex items-center gap-3.5">
                <Icon className={`w-5 h-5 transition-transform duration-200 group-hover:scale-110 ${isActive ? 'text-[#4cd7f6]' : 'text-[#869397]'}`} />
                <span className="font-mono text-sm tracking-wide">{item.label}</span>
              </div>
            </button>
          );
        })}

        {/* Review Queue quick-access */}
        <button
          onClick={() => {
            playCyberSound('alert');
            onOpenReviewQueue();
          }}
          className="w-full flex items-center justify-between px-3.5 py-3 rounded-md transition-all duration-200 group text-left text-[#bcc9cd] hover:bg-white/5 hover:text-[#4cd7f6] border-l-4 border-transparent"
        >
          <div className="flex items-center gap-3.5">
            <ClipboardList className="w-5 h-5 text-[#869397] group-hover:scale-110 transition-transform" />
            <span className="font-mono text-sm tracking-wide">Review Queue</span>
          </div>
          {reviewQueueCount > 0 && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#ff6b6b]/20 text-[#ffb4ab] border border-[#ff6b6b]/40 animate-pulse">
              {reviewQueueCount}
            </span>
          )}
        </button>
      </div>

      {/* Footer Section */}
      <div className="p-4 border-t border-white/5 space-y-3 bg-[#070d1f]/90">
        {/* API connectivity pill */}
        <div
          onClick={() => {
            playCyberSound('click');
            onOpenStatusModal();
          }}
          className={`glass-panel p-2.5 rounded-md border cursor-pointer transition-all flex items-center justify-between group ${
            apiConnected ? 'border-[#4edea3]/20 hover:border-[#4edea3]/50' : 'border-[#ff6b6b]/30 hover:border-[#ff6b6b]/60'
          }`}
        >
          <div className="flex items-center gap-2">
            <div className="relative flex h-2 w-2">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${apiConnected ? 'bg-[#4edea3]' : 'bg-[#ff6b6b]'} opacity-75`}></span>
              <span className={`relative inline-flex rounded-full h-2 w-2 ${apiConnected ? 'bg-[#4edea3]' : 'bg-[#ff6b6b]'}`}></span>
            </div>
            <p className={`font-mono text-xs font-semibold tracking-wide ${apiConnected ? 'text-[#4edea3]' : 'text-[#ffb4ab]'}`}>
              System: {apiConnected ? 'Connected' : 'Unreachable'}
            </p>
          </div>
          {apiConnected ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-[#4edea3] opacity-60 group-hover:opacity-100 transition-opacity" />
          ) : (
            <XCircle className="w-3.5 h-3.5 text-[#ff6b6b] opacity-70 group-hover:opacity-100 transition-opacity" />
          )}
        </div>

        {/* Support & Sound */}
        <div className="space-y-1 pt-1">
          <button
            onClick={() => {
              playCyberSound('click');
              onOpenSupportModal();
            }}
            className="w-full flex items-center gap-3 text-[#bcc9cd] hover:text-[#4cd7f6] px-2 py-1.5 rounded transition-colors text-left"
          >
            <HelpCircle className="w-4 h-4 text-[#869397]" />
            <span className="font-mono text-xs">Support & Docs</span>
          </button>

          <div className="flex items-center justify-between px-2 py-1 text-[#bcc9cd]">
            <button
              onClick={() => {
                onToggleMute();
                playCyberSound('click');
              }}
              className="flex items-center gap-2 hover:text-[#4cd7f6] transition-colors"
              title={isMuted ? 'Unmute audio cues' : 'Mute audio cues'}
            >
              {isMuted ? <VolumeX className="w-4 h-4 text-[#869397]" /> : <Volume2 className="w-4 h-4 text-[#4cd7f6]" />}
              <span className="font-mono text-xs">{isMuted ? 'Audio Off' : 'Audio On'}</span>
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};
