import {
  ProductsResponse,
  ProductDetailResponse,
  TelemetryResponse,
  EnrichRequest,
  EnrichResponse,
  ReviewStatus,
} from './types';

const API_BASE: string = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  ping: () => request<{ status: string; service: string; version: string }>('/'),

  getProducts: (params?: { query?: string; status?: string; sort_by?: string }) => {
    const qs = new URLSearchParams();
    if (params?.query) qs.set('query', params.query);
    if (params?.status) qs.set('status', params.status);
    if (params?.sort_by) qs.set('sort_by', params.sort_by);
    const suffix = qs.toString() ? `?${qs.toString()}` : '';
    return request<ProductsResponse>(`/api/products${suffix}`);
  },

  getProduct: (mpn: string) =>
    request<ProductDetailResponse>(`/api/products/${encodeURIComponent(mpn)}`),

  updateProductStatus: (mpn: string, status: ReviewStatus) =>
    request<{ status: string; mpn: string; review_status: string }>(
      `/api/products/${encodeURIComponent(mpn)}/status`,
      { method: 'PATCH', body: JSON.stringify({ status }) }
    ),

  saveProduct: (mpn: string, record: Record<string, any>) =>
    request<{ status: string; mpn: string; message: string }>(
      `/api/products/${encodeURIComponent(mpn)}`,
      { method: 'PUT', body: JSON.stringify(record) }
    ),

  bulkUpdateStatus: (mpns: string[], status: ReviewStatus) =>
    request<{ status: string; updated_count: number; new_status: string }>(
      `/api/bulk-status`,
      { method: 'POST', body: JSON.stringify({ mpns, status }) }
    ),

  enrich: (payload: EnrichRequest) =>
    request<EnrichResponse>(`/api/enrich`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getTelemetry: () => request<TelemetryResponse>('/api/telemetry'),

  exportUrl: (kind: 'csv' | 'json', onlyApproved: boolean) =>
    `${API_BASE}/api/export/${kind}${onlyApproved ? '?only_approved=true' : ''}`,
};

export { API_BASE };
