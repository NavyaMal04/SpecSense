export type ScreenType = 'dashboard' | 'products' | 'enrich' | 'export';

export type ReviewStatus = 'pending' | 'approved' | 'flagged';
export type SourceType = 'extracted' | 'inferred' | 'unavailable' | 'verified';

export interface FieldValue {
  value: string | number | null;
  source_type: SourceType;
  confidence: number;
  source_url: string | null;
  source_snippet: string | null;
}

export interface ProductSummary {
  mpn: string;
  part_desc: string;
  manufacturer: string;
  brand: string;
  completeness: number;
  fields_found: number;
  fields_total: number;
  review_status: ReviewStatus;
}

export interface ProductsResponse {
  total: number;
  products: ProductSummary[];
}

// Loosely typed full ProductRecord — most fields are FieldValue-shaped,
// a handful of identity fields are raw passthrough strings.
export interface ProductRecord {
  id: string | null;
  source_row_index: number | null;
  part_number: string | null;
  dept: string | null;
  product_class: string | null;
  fine_class: string | null;
  sku: string | null;
  mfg_part_num: string | null;
  part_desc: string | null;
  e1_brand: string | null;
  unilog_brand: string | null;
  dib_brand: string | null;
  part_manuf: string | null;
  review_status: ReviewStatus;
  processed_at: string | null;
  fields_found_count: number | null;
  fields_total_count: number | null;
  ref_urls: string[];
  item_features: { text: FieldValue }[];
  attributes: { label: FieldValue; value: FieldValue; uom: FieldValue }[];
  assets: { asset_type: string; url: FieldValue }[];
  [key: string]: any; // remaining FieldValue-shaped scalar fields (manufacturer_name, brand_name, ...)
}

export interface ProvenanceStats {
  extracted_pct: number;
  inferred_pct: number;
  unavailable_pct: number;
  counts: {
    extracted: number;
    inferred: number;
    unavailable: number;
    total_fields: number;
  };
}

export interface ProductDetailResponse {
  mpn: string;
  record: ProductRecord;
  provenance: ProvenanceStats;
}

export interface TelemetryResponse {
  total_records: number;
  provenance: ProvenanceStats;
  section_fill_rates: Record<string, number>;
  batch_summary: {
    timestamp?: string;
    total_attempted?: number;
    total_processed?: number;
    total_errored?: number;
    total_skipped?: number;
    avg_found_pct?: number;
    total_wall_clock_formatted?: string;
    review_status_counts?: Record<string, number>;
    retry_statistics?: {
      total_calls?: number;
      total_retries?: number;
      rows_requiring_retries_count?: number;
    };
  } | null;
}

export interface EnrichRequest {
  mfg_part_num: string;
  part_desc?: string;
  part_manuf?: string;
  e1_brand?: string;
}

export interface EnrichResponse {
  status: string;
  source?: 'cached' | 'live' | string;
  mpn: string;
  completeness: number;
  record: ProductRecord;
  message?: string;
}
