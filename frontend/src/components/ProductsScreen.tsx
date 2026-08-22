import React, { useEffect, useState, useCallback } from 'react';
import { ProductSummary, ReviewStatus } from '../types';
import { api } from '../api';
import { Search, ChevronRight, PackageSearch, Loader2 } from 'lucide-react';
import { playCyberSound } from '../utils/audio';

interface ProductsScreenProps {
  onOpenProduct: (mpn: string) => void;
  refreshSignal: number;
}

const STATUS_STYLES: Record<ReviewStatus, string> = {
  approved: 'text-[#4edea3] bg-[#4edea3]/10 border-[#4edea3]/40',
  pending: 'text-[#f6c945] bg-[#f6c945]/10 border-[#f6c945]/40',
  flagged: 'text-[#ffb4ab] bg-[#ff6b6b]/10 border-[#ff6b6b]/40',
};

export const ProductsScreen: React.FC<ProductsScreenProps> = ({ onOpenProduct, refreshSignal }) => {
  const [products, setProducts] = useState<ProductSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'All' | ReviewStatus>('All');
  const [sortBy, setSortBy] = useState<'completeness_desc' | 'completeness_asc' | 'mpn_asc'>('completeness_desc');

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    api
      .getProducts({ query: query || undefined, status: statusFilter, sort_by: sortBy })
      .then((res) => setProducts(res.products))
      .catch((e) => setError(e.message || 'Failed to load products'))
      .finally(() => setLoading(false));
  }, [query, statusFilter, sortBy]);

  useEffect(() => {
    const t = setTimeout(load, 250); // debounce search typing
    return () => clearTimeout(t);
  }, [load, refreshSignal]);

  return (
    <div className="space-y-6">
      <header className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-2 border-b border-white/5">
        <div>
          <h2 className="text-3xl lg:text-4xl font-bold tracking-tight text-[#dce1fb]">
            Product Browser
          </h2>
          <p className="font-mono text-sm text-[#bcc9cd] mt-1">
            Search, review, and manage every product in your catalog.
          </p>
        </div>
        <div className="font-mono text-xs text-[#869397]">
          {loading ? 'Loading…' : `${products.length} result${products.length === 1 ? '' : 's'}`}
        </div>
      </header>

      {/* Filters */}
      <div className="glass-panel rounded-xl p-4 flex flex-col md:flex-row gap-3 md:items-center">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-[#869397] absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by MPN, manufacturer, or brand…"
            className="w-full bg-[#151b2d] border border-white/10 rounded-lg pl-9 pr-3 py-2 text-sm font-mono text-[#dce1fb] placeholder:text-[#869397] focus:outline-none focus:border-[#4cd7f6]/50"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as any)}
          className="bg-[#151b2d] border border-white/10 rounded-lg px-3 py-2 text-xs font-mono text-[#dce1fb] focus:outline-none focus:border-[#4cd7f6]/50"
        >
          <option value="All">All statuses</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="flagged">Flagged</option>
        </select>

        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as any)}
          className="bg-[#151b2d] border border-white/10 rounded-lg px-3 py-2 text-xs font-mono text-[#dce1fb] focus:outline-none focus:border-[#4cd7f6]/50"
        >
          <option value="completeness_desc">Completeness: high to low</option>
          <option value="completeness_asc">Completeness: low to high</option>
          <option value="mpn_asc">MPN: A → Z</option>
        </select>
      </div>

      {error && (
        <div className="glass-panel rounded-xl p-4 border border-[#ff6b6b]/40 text-[#ffb4ab] font-mono text-sm">
          {error}. Please try again in a moment.
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-24 text-[#4cd7f6]">
          <Loader2 className="w-6 h-6 animate-spin" />
        </div>
      ) : products.length === 0 ? (
        <div className="glass-panel rounded-xl p-12 flex flex-col items-center text-center gap-3">
          <PackageSearch className="w-10 h-10 text-[#869397]" />
          <p className="font-mono text-sm text-[#bcc9cd]">No products match this filter.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {products.map((p) => (
            <button
              key={p.mpn}
              onClick={() => {
                playCyberSound('click');
                onOpenProduct(p.mpn);
              }}
              className="glass-panel rounded-xl p-5 text-left group hover:border-[#4cd7f6]/40 hover:shadow-[0_0_25px_rgba(76,215,246,0.12)] transition-all"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-mono text-[11px] text-[#869397] uppercase tracking-widest">MPN</p>
                  <p className="font-mono text-sm text-[#4cd7f6] font-bold truncate">{p.mpn}</p>
                </div>
                <span className={`shrink-0 text-[10px] font-mono px-2 py-0.5 rounded border ${STATUS_STYLES[p.review_status]}`}>
                  {p.review_status}
                </span>
              </div>

              <p className="text-sm text-[#dce1fb] mt-3 line-clamp-2 min-h-[2.5rem]">
                {p.part_desc || 'No description on file'}
              </p>

              <div className="mt-3 flex items-center gap-2 font-mono text-xs text-[#bcc9cd]">
                <span className="truncate">{p.manufacturer || 'Unknown manufacturer'}</span>
                {p.brand && p.brand !== p.manufacturer && (
                  <>
                    <span className="text-[#4cd7f6]">·</span>
                    <span className="truncate">{p.brand}</span>
                  </>
                )}
              </div>

              <div className="mt-4">
                <div className="flex justify-between items-center font-mono text-[11px] mb-1">
                  <span className="text-[#869397]">Completeness</span>
                  <span className="text-[#4cd7f6] font-bold">
                    {p.completeness}% ({p.fields_found}/{p.fields_total})
                  </span>
                </div>
                <div className="w-full bg-[#191f31] h-1.5 rounded-full overflow-hidden border border-white/5">
                  <div
                    className="bg-[#4cd7f6] h-full shadow-[0_0_8px_#4cd7f6] rounded-full"
                    style={{ width: `${p.completeness}%` }}
                  ></div>
                </div>
              </div>

              <div className="mt-4 flex items-center justify-end text-[#869397] group-hover:text-[#4cd7f6] transition-colors">
                <span className="font-mono text-[11px]">View details</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
