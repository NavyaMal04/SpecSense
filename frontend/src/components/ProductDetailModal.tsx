import React, { useEffect, useState } from 'react';
import { ProductRecord, FieldValue, ReviewStatus } from '../types';
import { api } from '../api';
import { X, Loader2, CheckCircle2, Flag, RotateCcw, ExternalLink, Pencil, Save, XCircle } from 'lucide-react';
import { playCyberSound } from '../utils/audio';

interface ProductDetailModalProps {
  mpn: string;
  onClose: () => void;
  onStatusChanged: () => void;
}

const SCALAR_SECTIONS: Record<string, [string, string][]> = {
  'Enriched Identity': [
    ['manufacturer_name', 'Manufacturer Name'],
    ['brand_name', 'Brand Name'],
    ['trade_name', 'Trade Name'],
    ['manufacturer_part_number', 'Manufacturer Part Number'],
    ['alternate_part_number', 'Alternate Part Number'],
    ['classpath', 'Classpath'],
    ['mfr_url', 'Manufacturer URL'],
  ],
  Descriptions: [
    ['mobile_desc', 'Mobile Description'],
    ['invoice_desc', 'Invoice Description'],
    ['short_desc', 'Short Description'],
    ['long_desc1', 'Long Description'],
    ['retail_desc', 'Retail Description'],
    ['marketing_description', 'Marketing Description'],
  ],
  Modifiers: [
    ['with_features', 'With'],
    ['standard_approvals', 'Standard / Approvals'],
    ['prop_65', 'Prop 65'],
    ['application', 'Application'],
    ['includes', 'Includes'],
    ['product_name', 'Product Name'],
  ],
  Identifiers: [
    ['upc', 'UPC'],
    ['ean', 'EAN'],
    ['gtin', 'GTIN'],
    ['unspsc', 'UNSPSC'],
  ],
  Commercial: [
    ['warranty', 'Warranty'],
    ['list_price', 'List Price'],
    ['selling_qty', 'Selling Qty'],
    ['selling_uom', 'Selling UOM'],
    ['standard_packaging_info', 'Standard Packaging Info'],
  ],
  Dimensions: [
    ['length', 'Length'], ['length_uom', 'Length UOM'],
    ['height', 'Height'], ['height_uom', 'Height UOM'],
    ['width', 'Width'], ['width_uom', 'Width UOM'],
    ['weight', 'Weight'], ['weight_uom', 'Weight UOM'],
    ['volume', 'Volume'], ['volume_uom', 'Volume UOM'],
  ],
  Misc: [
    ['country_of_origin', 'Country of Origin'],
    ['discontinued', 'Discontinued'],
    ['actual_image_yn', 'Actual Image (Y/N)'],
  ],
};

const SOURCE_STYLES: Record<string, string> = {
  extracted: 'text-[#4cd7f6] bg-[#4cd7f6]/10 border-[#4cd7f6]/40',
  verified: 'text-[#4cd7f6] bg-[#4cd7f6]/10 border-[#4cd7f6]/40',
  inferred: 'text-[#4edea3] bg-[#4edea3]/10 border-[#4edea3]/40',
  unavailable: 'text-[#869397] bg-white/5 border-white/10',
};

const STATUS_STYLES: Record<ReviewStatus, string> = {
  approved: 'text-[#4edea3] bg-[#4edea3]/10 border-[#4edea3]/40',
  pending: 'text-[#f6c945] bg-[#f6c945]/10 border-[#f6c945]/40',
  flagged: 'text-[#ffb4ab] bg-[#ff6b6b]/10 border-[#ff6b6b]/40',
};

// Deep-ish clone sufficient for this record shape (plain JSON data).
const cloneRecord = (r: ProductRecord): ProductRecord => JSON.parse(JSON.stringify(r));

export const ProductDetailModal: React.FC<ProductDetailModalProps> = ({ mpn, onClose, onStatusChanged }) => {
  const [record, setRecord] = useState<ProductRecord | null>(null);
  const [draft, setDraft] = useState<ProductRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .getProduct(mpn)
      .then((res) => setRecord(res.record))
      .catch((e) => setError(e.message || 'Failed to load product'))
      .finally(() => setLoading(false));
  }, [mpn]);

  const setStatus = async (status: ReviewStatus) => {
    setUpdating(true);
    try {
      await api.updateProductStatus(mpn, status);
      setRecord((r) => (r ? { ...r, review_status: status } : r));
      onStatusChanged();
      playCyberSound('success');
    } catch (e) {
      playCyberSound('alert');
    } finally {
      setUpdating(false);
    }
  };

  const startEditing = () => {
    if (!record) return;
    setDraft(cloneRecord(record));
    setSaveError(null);
    setIsEditing(true);
    playCyberSound('click');
  };

  const cancelEditing = () => {
    setDraft(null);
    setIsEditing(false);
    setSaveError(null);
  };

  const updateField = (key: string, value: string) => {
    setDraft((d) => {
      if (!d) return d;
      const existing: FieldValue | undefined = d[key];
      const next: FieldValue = {
        value: value === '' ? null : value,
        source_type: value === '' ? 'unavailable' : 'verified',
        confidence: value === '' ? 0 : 1,
        source_url: existing?.source_url ?? null,
        source_snippet: existing?.source_snippet ?? null,
      };
      return { ...d, [key]: next };
    });
  };

  const saveChanges = async () => {
    if (!draft) return;
    setSaving(true);
    setSaveError(null);
    try {
      await api.saveProduct(mpn, draft);
      setRecord(draft);
      setIsEditing(false);
      setDraft(null);
      onStatusChanged();
      playCyberSound('success');
    } catch (e: any) {
      setSaveError(e.message || 'Failed to save changes');
      playCyberSound('alert');
    } finally {
      setSaving(false);
    }
  };

  const active = isEditing ? draft : record;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="glass-panel-glow max-w-4xl w-full max-h-[88vh] rounded-2xl flex flex-col overflow-hidden border border-[#4cd7f6]/40 shadow-2xl shadow-[#4cd7f6]/10">
        {/* Header */}
        <div className="p-6 border-b border-white/10 bg-[#070d1f]/90 flex items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="font-mono text-[11px] text-[#869397] uppercase tracking-widest">MPN</p>
            <h3 className="text-xl font-bold text-[#4cd7f6] font-mono truncate">{mpn}</h3>
            {record?.part_desc && (
              <p className="text-sm text-[#bcc9cd] mt-1 truncate">{record.part_desc}</p>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {record && (
              <span className={`text-[11px] font-mono px-2.5 py-1 rounded border ${STATUS_STYLES[record.review_status]}`}>
                {record.review_status}
              </span>
            )}
            {record && !isEditing && (
              <button
                onClick={startEditing}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono border border-[#4cd7f6]/40 text-[#4cd7f6] hover:bg-[#4cd7f6]/10 transition-colors"
              >
                <Pencil className="w-3.5 h-3.5" /> Edit
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-[#bcc9cd] hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {isEditing && (
          <div className="px-6 py-2.5 bg-[#4cd7f6]/5 border-b border-[#4cd7f6]/20 flex items-center justify-between">
            <p className="font-mono text-[11px] text-[#4cd7f6]">
              Editing — manually entered values are marked <span className="font-bold">verified</span>.
            </p>
          </div>
        )}

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading && (
            <div className="flex items-center justify-center py-16 text-[#4cd7f6]">
              <Loader2 className="w-6 h-6 animate-spin" />
            </div>
          )}

          {error && (
            <div className="glass-panel rounded-xl p-4 border border-[#ff6b6b]/40 text-[#ffb4ab] font-mono text-sm">
              {error}
            </div>
          )}

          {active &&
            Object.entries(SCALAR_SECTIONS).map(([section, fields]) => (
              <div key={section}>
                <h4 className="font-mono text-xs uppercase tracking-widest text-[#4cd7f6] font-bold mb-3">
                  {section}
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {fields.map(([key, label]) => {
                    const fv: FieldValue | undefined = active[key];
                    const hasValue = fv && fv.value !== null && fv.value !== '';
                    return (
                      <div key={key} className="p-3 rounded-lg bg-[#151b2d]/60 border border-white/5">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-mono text-[11px] text-[#869397]">{label}</span>
                          {fv && (
                            <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${SOURCE_STYLES[fv.source_type] || SOURCE_STYLES.unavailable}`}>
                              {fv.source_type}
                              {hasValue && fv.confidence ? ` · ${Math.round(fv.confidence * 100)}%` : ''}
                            </span>
                          )}
                        </div>

                        {isEditing ? (
                          <input
                            value={fv?.value !== null && fv?.value !== undefined ? String(fv.value) : ''}
                            onChange={(e) => updateField(key, e.target.value)}
                            placeholder="no value"
                            className="w-full bg-[#0c1120] border border-white/10 rounded px-2 py-1.5 text-sm text-[#dce1fb] placeholder:text-[#5b6572] focus:outline-none focus:border-[#4cd7f6]/60"
                          />
                        ) : (
                          <p className={`text-sm ${hasValue ? 'text-[#dce1fb]' : 'text-[#5b6572] italic'}`}>
                            {hasValue ? String(fv!.value) : 'no value'}
                          </p>
                        )}

                        {!isEditing && fv?.source_url && (
                          <a
                            href={fv.source_url}
                            target="_blank"
                            rel="noreferrer"
                            className="mt-1.5 inline-flex items-center gap-1 text-[10px] font-mono text-[#4cd7f6]/80 hover:text-[#4cd7f6]"
                          >
                            <ExternalLink className="w-3 h-3" /> source
                          </a>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}

          {!isEditing && record && record.item_features?.length > 0 && (
            <div>
              <h4 className="font-mono text-xs uppercase tracking-widest text-[#4cd7f6] font-bold mb-3">
                Feature Bullets
              </h4>
              <ul className="space-y-1.5">
                {record.item_features.map((f, i) => (
                  f.text?.value ? (
                    <li key={i} className="text-sm text-[#dce1fb] flex gap-2">
                      <span className="text-[#4cd7f6]">•</span>
                      <span>{f.text.value}</span>
                    </li>
                  ) : null
                ))}
              </ul>
            </div>
          )}

          {!isEditing && record && record.attributes?.filter((a) => a.value?.value).length > 0 && (
            <div>
              <h4 className="font-mono text-xs uppercase tracking-widest text-[#4cd7f6] font-bold mb-3">
                Attributes
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {record.attributes
                  .filter((a) => a.value?.value)
                  .map((a, i) => (
                    <div key={i} className="p-2.5 rounded-lg bg-[#151b2d]/60 border border-white/5 flex justify-between text-sm">
                      <span className="text-[#bcc9cd]">{a.label?.value || '—'}</span>
                      <span className="text-[#dce1fb] font-medium">
                        {a.value?.value} {a.uom?.value || ''}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {isEditing && (
            <p className="font-mono text-[11px] text-[#869397]">
              Feature bullets and attributes aren't editable here yet.
            </p>
          )}

          {saveError && (
            <div className="glass-panel rounded-xl p-3 border border-[#ff6b6b]/40 text-[#ffb4ab] font-mono text-xs">
              {saveError}
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="p-4 border-t border-white/10 bg-[#070d1f]/90 flex flex-wrap items-center justify-end gap-2">
          {isEditing ? (
            <>
              <button
                disabled={saving}
                onClick={cancelEditing}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-mono border border-white/10 text-[#bcc9cd] hover:bg-white/5 transition-colors disabled:opacity-50"
              >
                <XCircle className="w-3.5 h-3.5" /> Cancel
              </button>
              <button
                disabled={saving}
                onClick={saveChanges}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-mono border border-[#4cd7f6]/40 text-[#4cd7f6] hover:bg-[#4cd7f6]/10 transition-colors disabled:opacity-50"
              >
                {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                Save Changes
              </button>
            </>
          ) : (
            <>
              <button
                disabled={updating}
                onClick={() => setStatus('flagged')}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-mono border border-[#ff6b6b]/40 text-[#ffb4ab] hover:bg-[#ff6b6b]/10 transition-colors disabled:opacity-50"
              >
                <Flag className="w-3.5 h-3.5" /> Flag
              </button>
              <button
                disabled={updating}
                onClick={() => setStatus('pending')}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-mono border border-white/10 text-[#bcc9cd] hover:bg-white/5 transition-colors disabled:opacity-50"
              >
                <RotateCcw className="w-3.5 h-3.5" /> Reset to Pending
              </button>
              <button
                disabled={updating}
                onClick={() => setStatus('approved')}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-mono border border-[#4edea3]/40 text-[#4edea3] hover:bg-[#4edea3]/10 transition-colors disabled:opacity-50"
              >
                <CheckCircle2 className="w-3.5 h-3.5" /> Approve
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
