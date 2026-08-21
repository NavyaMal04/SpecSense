import React from 'react';
import { ScreenType } from '../types';
import { 
  BarChart3, 
  Network as NetworkIcon, 
  Radio, 
  FolderGit2, 
  Terminal, 
  HelpCircle, 
  LogOut, 
  Volume2, 
  VolumeX, 
  Activity,
  Zap,
  CheckCircle2
} from 'lucide-react';
import { playCyberSound } from '../utils/audio';

interface SidebarProps {
  currentScreen: ScreenType;
  onSelectScreen: (screen: ScreenType) => void;
  anomaliesCount: number;
  isSimulating: boolean;
  onToggleSimulation: () => void;
  isMuted: boolean;
  onToggleMute: () => void;
  onOpenStatusModal: () => void;
  onOpenSupportModal: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentScreen,
  onSelectScreen,
  anomaliesCount,
  isSimulating,
  onToggleSimulation,
  isMuted,
  onToggleMute,
  onOpenStatusModal,
  onOpenSupportModal,
}) => {
  const navItems = [
    {
      id: 'diagnostics' as ScreenType,
      label: 'Diagnostics',
      icon: Activity,
      badge: 'STABLE',
      badgeColor: 'text-[#4edea3] bg-[#4edea3]/10',
    },
    {
      id: 'network' as ScreenType,
      label: 'Network',
      icon: NetworkIcon,
      badge: '10 NODES',
      badgeColor: 'text-[#4cd7f6] bg-[#4cd7f6]/10',
    },
    {
      id: 'telemetry' as ScreenType,
      label: 'Telemetry',
      icon: Radio,
      badge: null,
      badgeColor: '',
    },
    {
      id: 'archives' as ScreenType,
      label: 'Archives',
      icon: FolderGit2,
      badge: '14.2k',
      badgeColor: 'text-[#bcc9cd] bg-[#bcc9cd]/10',
    },
    {
      id: 'terminal' as ScreenType,
      label: 'Terminal',
      icon: Terminal,
      badge: 'CLI',
      badgeColor: 'text-[#d0bcff] bg-[#d0bcff]/10',
    },
  ];

  return (
    <nav className="w-64 bg-[#070d1f]/80 backdrop-blur-md border-r border-[#4cd7f6]/20 flex flex-col h-screen fixed left-0 top-0 z-40 select-none shadow-2xl shadow-[#4cd7f6]/5">
      {/* Brand Header */}
      <div className="px-6 pt-7 pb-6 border-b border-white/5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-[#4cd7f6] glow-text cursor-pointer flex items-center gap-2"
                onClick={() => {
                  playCyberSound('tab');
                  onSelectScreen('telemetry');
                }}>
              <span>SpecSense</span>
              <span className="w-2 h-2 rounded-full bg-[#4cd7f6] animate-ping opacity-75"></span>
            </h1>
            <p className="font-mono text-xs text-[#4cd7f6]/70 mt-1 tracking-wider uppercase font-semibold">
              Precision Operations
            </p>
          </div>
        </div>
      </div>

      {/* Navigation Items */}
      <div className="flex-1 py-6 px-3 space-y-1.5 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-mono uppercase tracking-widest text-[#869397]">
          Navigation Core
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

              {item.badge && (
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded border border-current/20 ${item.badgeColor}`}>
                  {item.badge}
                </span>
              )}
              {item.id === 'telemetry' && anomaliesCount > 0 && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#ff6b6b]/20 text-[#ffb4ab] border border-[#ff6b6b]/40 animate-pulse">
                  {anomaliesCount} ANOM
                </span>
              )}
            </button>
          );
        })}

        {/* Live Simulation Controls */}
        <div className="pt-6 px-3">
          <div className="p-3 rounded-lg bg-[#151b2d]/80 border border-white/5 space-y-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-[#869397]">Telemetry Stream</span>
              <span className={`flex items-center gap-1 font-semibold ${isSimulating ? 'text-[#4edea3]' : 'text-[#869397]'}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${isSimulating ? 'bg-[#4edea3] animate-pulse' : 'bg-gray-500'}`}></span>
                {isSimulating ? 'ACTIVE' : 'PAUSED'}
              </span>
            </div>
            <button
              onClick={() => {
                playCyberSound('click');
                onToggleSimulation();
              }}
              className={`w-full py-1.5 px-2 rounded text-xs font-mono transition-colors flex items-center justify-center gap-1.5 ${
                isSimulating 
                  ? 'bg-[#4cd7f6]/10 text-[#4cd7f6] hover:bg-[#4cd7f6]/20 border border-[#4cd7f6]/30' 
                  : 'bg-white/5 text-[#bcc9cd] hover:bg-white/10'
              }`}
            >
              <Zap className="w-3.5 h-3.5" />
              {isSimulating ? 'Pause Stream' : 'Resume Stream'}
            </button>
          </div>
        </div>
      </div>

      {/* Footer Section */}
      <div className="p-4 border-t border-white/5 space-y-3 bg-[#070d1f]/90">
        {/* System Status optimal pill */}
        <div 
          onClick={() => {
            playCyberSound('click');
            onOpenStatusModal();
          }}
          className="glass-panel p-2.5 rounded-md border border-[#4edea3]/20 hover:border-[#4edea3]/50 cursor-pointer transition-all flex items-center justify-between group"
        >
          <div className="flex items-center gap-2">
            <div className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#4edea3] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#4edea3]"></span>
            </div>
            <p className="font-mono text-xs text-[#4edea3] font-semibold tracking-wide">
              System Status: Optimal
            </p>
          </div>
          <CheckCircle2 className="w-3.5 h-3.5 text-[#4edea3] opacity-60 group-hover:opacity-100 transition-opacity" />
        </div>

        {/* Support & Logout & Sound */}
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

            <button
              onClick={() => {
                playCyberSound('click');
                onOpenStatusModal();
              }}
              className="flex items-center gap-1.5 hover:text-[#ff6b6b] transition-colors text-xs font-mono"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Operator</span>
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};
