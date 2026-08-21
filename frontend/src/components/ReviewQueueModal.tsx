import React, { useEffect, useState } from 'react';
import { ProductSummary, ReviewStatus } from '../types';
import { api } from '../api';
import { X, CheckCircle2, Flag, Loader2, ClipboardList } from 'lucide-react';
import { playCyberSound } from '../utils/audio';

interface ReviewQueueModalProps {
  onClose: () => void;
  onChanged: () => void;
  onOpenProduct: (mpn: string) => void;
}

export const ReviewQueueModal: React.FC<ReviewQueueModalProps> = ({ onClose, onChanged, onOpenProduct }) => {
  const [items, setItems] = useState<ProductSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pending' | 'flagged'>('all');
  const [busyMpn, setBusyMpn] = useState<string | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([api.getProducts({ status: 'pending' }), api.getProducts({ status: 'flagged' })])
      .then(([pending, flagged]) => setItems([...pending.products, ...flagged.products]))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const filtered = items.filter((i) => filter === 'all' || i.review_status === filter);

  const setStatus = async (mpn: string, status: ReviewStatus) => {
    setBusyMpn(mpn);
    try {
      await api.updateProductStatus(mpn, status);
      setItems((prev) => prev.filter((i) => i.mpn !== mpn));
      onChanged();
      playCyberSound('success');
    } catch {
      playCyberSound('alert');
    } finally {
      setBusyMpn(null);
    }
  };

  const approveAll = async () => {
    if (filtered.length === 0) return;
    setBulkBusy(true);
    try {
      await api.bulkUpdateStatus(filtered.map((i) => i.mpn), 'approved');
      setItems((prev) => prev.filter((i) => !filtered.some((f) => f.mpn === i.mpn)));
      onChanged();
      playCyberSound('success');
    } catch {
      playCyberSound('alert');
    } finally {
      setBulkBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="glass-panel-glow max-w-4xl w-full max-h-[85vh] rounded-2xl flex flex-col overflow-hidden border border-[#ff6b6b]/40 shadow-2xl shadow-[#ff6b6b]/10">
        {/* Header */}
        <div className="p-6 border-b border-white/10 bg-[#070d1f]/90 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#ff6b6b]/20 flex items-center justify-center border border-[#ff6b6b]/40 text-[#ffb4ab]">
              <ClipboardList className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-[#dce1fb]">Review Queue</h3>
              <p className="font-mono text-xs text-[#869397]">{items.length} products pending or flagged</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-[#bcc9cd] hover:text-white transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Filters + bulk action */}
        <div className="px-6 py-3 border-b border-white/5 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center bg-[#151b2d] p-1 rounded-lg border border-white/5 text-[11px] font-mono">
            {(['all', 'pending', 'flagged'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2.5 py-1 rounded transition-colors capitalize ${
                  filter === f ? 'bg-[#ff6b6b]/20 text-[#ffb4ab] font-bold' : 'text-[#869397]'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
          <button
            disabled={bulkBusy || filtered.length === 0}
            onClick={approveAll}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono border border-[#4edea3]/40 text-[#4edea3] hover:bg-[#4edea3]/10 transition-colors disabled:opacity-40"
          >
            <CheckCircle2 className="w-3.5 h-3.5" /> Approve all shown ({filtered.length})
          </button>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {loading && (
            <div className="flex items-center justify-center py-12 text-[#4cd7f6]">
              <Loader2 className="w-5 h-5 animate-spin" />
            </div>
          )}
          {!loading && filtered.length === 0 && (
            <p className="text-center py-12 font-mono text-sm text-[#869397]">Nothing to review 🎉</p>
          )}
          {filtered.map((item) => (
            <div
              key={item.mpn}
              className="p-3.5 rounded-lg bg-[#151b2d]/70 border border-white/5 flex items-center justify-between gap-3 hover:border-[#4cd7f6]/20 transition-colors"
            >
              <button className="min-w-0 text-left flex-1" onClick={() => onOpenProduct(item.mpn)}>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm text-[#4cd7f6] font-bold">{item.mpn}</span>
                  <span
                    className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${
                      item.review_status === 'flagged'
                        ? 'text-[#ffb4ab] bg-[#ff6b6b]/10 border-[#ff6b6b]/40'
                        : 'text-[#f6c945] bg-[#f6c945]/10 border-[#f6c945]/40'
                    }`}
                  >
                    {item.review_status}
                  </span>
                </div>
                <p className="text-xs text-[#bcc9cd] truncate mt-0.5">
                  {item.part_desc || 'No description'} · {item.manufacturer || 'Unknown mfr'} · {item.completeness}% complete
                </p>
              </button>

              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  disabled={busyMpn === item.mpn}
                  onClick={() => setStatus(item.mpn, 'flagged')}
                  className="p-2 rounded-lg border border-[#ff6b6b]/30 text-[#ffb4ab] hover:bg-[#ff6b6b]/10 transition-colors disabled:opacity-40"
                  title="Flag"
                >
                  <Flag className="w-3.5 h-3.5" />
                </button>
                <button
                  disabled={busyMpn === item.mpn}
                  onClick={() => setStatus(item.mpn, 'approved')}
                  className="p-2 rounded-lg border border-[#4edea3]/30 text-[#4edea3] hover:bg-[#4edea3]/10 transition-colors disabled:opacity-40"
                  title="Approve"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
