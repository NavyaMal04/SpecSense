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
    body: 'Shows aggregate provenance (extracted vs. inferred vs. unavailable) and per-section fill rates across every product record on disk.',
  },
  {
    icon: PackageSearch,
    title: 'Products',
    body: 'Search and filter the catalog by MPN, manufacturer, or brand. Click any card to open the full record with field-level provenance, confidence, and source citations.',
  },
  {
    icon: Sparkles,
    title: 'Run Enrichment',
    body: 'Enrich a single new part by MPN. The pipeline extracts from datasheets, infers missing fields from similar reference products, and saves the result to the catalog as "pending".',
  },
  {
    icon: ClipboardList,
    title: 'Review Queue',
    body: 'Triage pending and flagged products in bulk — approve, flag, or reset a record\'s review status before it goes into an export.',
  },
  {
    icon: Download,
    title: 'Export',
    body: 'Download the catalog as a 252-column Unilog delivery-format CSV, or the full JSON with all provenance metadata. Optionally restrict to approved records only.',
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
              AI-powered product intelligence pipeline — datasheets in, commerce-ready catalog data out.
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
            <p className="font-mono text-sm text-[#dce1fb] font-semibold mb-2">Field provenance badges</p>
            <ul className="text-sm text-[#bcc9cd] space-y-1">
              <li><span className="text-[#4cd7f6] font-mono">extracted</span> — pulled directly from a source document or page, with a citation.</li>
              <li><span className="text-[#4edea3] font-mono">inferred</span> — predicted from similar historical products via vector similarity.</li>
              <li><span className="text-[#869397] font-mono">unavailable</span> — no confident value found; flagged for human review.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
