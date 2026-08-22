import React from 'react';
import { X, LayoutDashboard, PackageSearch, Sparkles, Download, ClipboardList } from 'lucide-react';
import { playCyberSound } from '../utils/audio';

interface SupportModalProps {
  onClose: () => void;
}

const sections = [
  {
    icon: LayoutDashboard,
    title: 'Dashboard',
    body: 'A quick overview of your catalog — how many products you have, how complete their details are, and which sections need the most attention.',
  },
  {
    icon: PackageSearch,
    title: 'Products',
    body: 'Search and filter your catalog by part number, manufacturer, or brand. Click any product to see its full details and edit them if needed.',
  },
  {
    icon: Sparkles,
    title: 'Add Product',
    body: 'Add a brand-new product by part number. We automatically look up and fill in as many details as we can find — it\'s saved as "pending" so you can review it before it goes live.',
  },
  {
    icon: ClipboardList,
    title: 'Review Queue',
    body: 'A checklist of products waiting on your review. Approve them individually or in bulk, or flag anything that needs a closer look.',
  },
  {
    icon: Download,
    title: 'Export',
    body: 'Download your catalog as a spreadsheet-ready CSV or a full JSON file, whenever you need it elsewhere. You can choose to include only approved products.',
  },
];

export const SupportModal: React.FC<SupportModalProps> = ({ onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="glass-panel-glow max-w-2xl w-full max-h-[85vh] rounded-2xl flex flex-col overflow-hidden border border-[#4cd7f6]/30 shadow-2xl">
        <div className="p-6 border-b border-white/10 bg-[#070d1f]/90 flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold text-[#dce1fb]">Support &amp; Docs</h3>
            <p className="font-mono text-xs text-[#869397] mt-1">
              A quick guide to what each part of SpecSense does.
            </p>
          </div>
          <button
            onClick={() => {
              playCyberSound('click');
              onClose();
            }}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-[#bcc9cd] hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {sections.map(({ icon: Icon, title, body }) => (
            <div key={title} className="p-4 rounded-lg bg-[#151b2d]/60 border border-white/5 flex gap-3">
              <div className="w-9 h-9 shrink-0 rounded-lg bg-[#4cd7f6]/10 border border-[#4cd7f6]/30 flex items-center justify-center text-[#4cd7f6]">
                <Icon className="w-4.5 h-4.5" />
              </div>
              <div>
                <p className="font-mono text-sm text-[#dce1fb] font-semibold">{title}</p>
                <p className="text-sm text-[#bcc9cd] mt-1">{body}</p>
              </div>
            </div>
          ))}

          <div className="p-4 rounded-lg bg-[#151b2d]/60 border border-white/5">
            <p className="font-mono text-sm text-[#dce1fb] font-semibold mb-2">What the field tags mean</p>
            <ul className="text-sm text-[#bcc9cd] space-y-1">
              <li><span className="text-[#4cd7f6] font-mono">extracted</span> — found directly in a manufacturer source.</li>
              <li><span className="text-[#4edea3] font-mono">inferred</span> — predicted based on similar products.</li>
              <li><span className="text-[#4cd7f6] font-mono">verified</span> — entered or confirmed by hand.</li>
              <li><span className="text-[#869397] font-mono">unavailable</span> — no value found yet; worth a look.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
