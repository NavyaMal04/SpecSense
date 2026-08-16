# SpecSense

**AI-Powered Product Intelligence Pipeline**
*Built for UniHack — Unilog's AI Innovation Challenge*

SpecSense transforms unstructured, messy product sources (PDF spec sheets, datasheets) into structured, commerce-ready product data — with every field traceable back to its source and labeled by how confident the system actually is.

## Key Features

- **Field Provenance & Traceability** — every extracted field is labeled `extracted`, `inferred`, or `flagged`, with a confidence score
- **Citation Tracking** — extracted fields carry the exact page/line location they came from in the source PDF
- **Reference Inference** — missing fields are predicted from similar historical products using TF-IDF + cosine similarity (scikit-learn)
- **Conflict Detection** — contradictory specs in the same document (e.g. two different voltage values) are flagged rather than silently picked
- **Human-in-the-Loop Review** — flagged or inferred fields can be approved as-is or corrected, one field at a time, with the source citation shown alongside
- **Grounded Commerce Copy** — title, short description, feature bullets, and FAQ are generated strictly from verified (non-flagged) fields, never invented
- **Batch Processing** — process a whole folder of spec sheets in one run, with catalog-scale stats (processed count, flagged count, estimated time saved)

## Architecture

```
PDF → pipeline/extractor.py        (page/line-tagged text extraction)
    → pipeline/llm_extractor.py    (Gemini: structured field extraction + citations)
    → pipeline/record_builder.py   (provenance tagging, conflict detection, TF-IDF inference)
    → pipeline/copy_generator.py   (Gemini: grounded commerce copy)
    → pipeline/firestore_client.py (persistence)
    → backend/main.py              (FastAPI endpoints)
    → frontend/                    (Streamlit UI)
```

- `pipeline/` — core extraction, LLM logic (Gemini API), schema, inference. Pipeline-agnostic; both `backend/main.py` and each pipeline module's own `__main__` test harness call into it the same way.
- `backend/` — FastAPI app wiring the pipeline together for the frontend (and any other client) to call over HTTP.
- `frontend/` — Streamlit multi-page UI: Catalog Dashboard, Data Ingestion, Batch Processing, Anomaly Review.
- `data/samples/` — sample PDF spec sheets, including ones deliberately built to test each confidence path (clean, missing fields, contradictory fields).
- `data/reference/` — reference product catalog used for similarity-based inference.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and add your **Gemini API key** (free tier available at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)).
3. *(Optional, for persistence)* Set `FIREBASE_CREDENTIALS_PATH` in `.env` to a Firebase service-account JSON. Without it, extraction/inference/copy generation still work end-to-end — only saving, listing, and reviewing *previously processed* products needs Firestore.

## Running it

**Backend** (from the project root):
```bash
uvicorn backend.main:app --reload
```
Confirm it's up at `http://127.0.0.1:8000/health` — it reports whether your Gemini key and Firebase credentials are actually loaded.

**Frontend** (separate terminal, from the project root):
```bash
streamlit run frontend/app.py
```
Set the `SPECSENSE_API_URL` environment variable if the backend isn't at `http://localhost:8000`.

## UI

Dark "precision operations" telemetry aesthetic — deep navy background, cyan accent, monospace data labels, card-based metrics, status badges. Shared styling and components live in `frontend/theme.py` (`inject_css()`, `metric_card()`, `badge()`, `donut_ring()`, `progress_row()`, `flag_item()`) — reuse these in new pages rather than writing raw HTML, to keep the look consistent.

Pages:
- `app.py` — **Catalog Dashboard**: live totals, accuracy rate, pending anomalies, category breakdown, data-integrity ring, efficiency delta
- `pages/1_Data_Ingestion.py` — single-document upload with per-field traceability cards and generated commerce copy
- `pages/2_Batch_Processing.py` — batch upload with catalog-scale stats and a per-product activity table
- `pages/3_Anomaly_Review.py` — flagged-item queue with source citations and one-click approve/correct

## Backend endpoints

- `POST /upload` — process a single PDF through the full pipeline
- `POST /batch` — process multiple PDFs, returns aggregate stats
- `GET /products` (optional `?review_status=pending|approved|flagged`) — list products
- `GET /products/{id}` — fetch one product
- `POST /products/{id}/review/{field_name}` — approve or correct a field:
  `{"accept_as_is": true}` or `{"accept_as_is": false, "corrected_value": "..."}`
  (pass `"additional_attribute_index"` instead of a real `field_name` to review an `additional_attributes[i]` entry)
- `GET /health` — confirms whether the Gemini key and Firebase credentials are actually configured

## Known limitations

- `pipeline/llm_extractor.py` and `pipeline/copy_generator.py` use the `google.generativeai` SDK, which Google has deprecated in favor of `google.genai`. Still functional, but worth migrating post-hackathon.
- No OCR fallback — `pdfplumber` only reads embedded text layers, so fully scanned/image-only PDFs won't extract.
- No auth on the review endpoints yet; anyone with API access can approve/correct records.