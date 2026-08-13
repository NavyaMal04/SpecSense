# SpecSense

**AI-Powered Product Intelligence Pipeline**  
*Built for UniHack — Unilog's AI Innovation Challenge*

SpecSense transforms unstructured, messy product sources (like PDF specification sheets and datasheets) into structured, commerce-ready product data records.

## Key Features

- **Field Provenance & Traceability**: Every extracted field is labeled with its source type (`extracted`, `inferred`, or `flagged`) and confidence score.
- **Citation Tracking**: Extracted fields maintain source locations (page and line references) pointing directly to the original document.
- **Reference Inference**: Missing fields are predicted from similar historical products using vector similarity (scikit-learn).
- **Human-in-the-Loop Flagging**: Ambiguous, conflicting, or low-confidence data points are flagged for review.
- **Ground Commerce Copy Generation**: AI generates title, short description, feature bullet points, and Q&A FAQs strictly grounded in verified product specifications.

## Architecture

- `backend/`: FastAPI application endpoints.
- `pipeline/`: Core PDF extraction, LLM logic (Gemini API), field schema, and inference logic.
- `frontend/`: Streamlit interactive dashboard.
- `data/samples/`: Sample PDF specification sheets.
- `data/reference/`: Reference product catalog for similarity inference.

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in your Gemini API Key.
