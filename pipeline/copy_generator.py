import os
import sys
import json
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import google.generativeai as genai

from pipeline.schema import ProductRecord, CommerceCopyField, FAQItem, AttributeField
from pipeline.extractor import get_full_text_with_citations, PDFExtractionError
from pipeline.llm_extractor import extract_structured_fields, LLMExtractionError
from pipeline.record_builder import build_product_record, infer_missing_fields

load_dotenv()


class CopyGenerationError(Exception):
    """Custom exception raised when LLM copy generation or JSON parsing fails."""
    def __init__(self, message: str, raw_response: Optional[str] = None):
        super().__init__(message)
        self.raw_response = raw_response


def _init_gemini():
    """Ensures Gemini API key is configured."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise CopyGenerationError("GEMINI_API_KEY is missing or invalid in your .env file.")
    genai.configure(api_key=api_key)


def _prepare_verified_context(record: ProductRecord) -> Dict[str, Any]:
    """
    Filters ProductRecord to include ONLY verified (extracted or inferred) attributes.
    Excludes any fields with source_type == 'flagged' to prevent hallucinating unverified/disputed claims.
    """
    verified_context = {}
    core_keys = ["name", "category", "dimensions", "material", "voltage", "certifications", "weight", "price"]

    for k in core_keys:
        attr: AttributeField = getattr(record, k)
        if attr.source_type in ["extracted", "inferred"] and attr.value is not None:
            verified_context[k] = {
                "value": attr.value,
                "source_type": attr.source_type,
                "confidence": attr.confidence
            }

    # Include non-flagged additional attributes
    verified_additional = []
    for add_attr in record.additional_attributes:
        if add_attr.source_type in ["extracted", "inferred"] and add_attr.value:
            verified_additional.append({
                "value": add_attr.value,
                "source_type": add_attr.source_type,
                "confidence": add_attr.confidence
            })

    if verified_additional:
        verified_context["additional_attributes"] = verified_additional

    return verified_context


def generate_commerce_copy(record: ProductRecord) -> ProductRecord:
    """
    Generates grounded buyer-facing commerce copy (title, short description, feature bullets, FAQ)
    strictly using verified product specifications.

    Args:
        record: Fully built ProductRecord (post extraction, mapping, and inference).

    Returns:
        ProductRecord populated with grounded commerce copy fields.
    """
    _init_gemini()
    context = _prepare_verified_context(record)

    prompt = f"""You are an expert e-commerce product copywriter for an industrial product catalog.
Generate high-converting, buyer-facing commerce copy based STRICTLY on the provided verified product specs.

VERIFIED SPECIFICATIONS CONTEXT:
---
{json.dumps(context, indent=2)}
---

GROUNDING & SAFETY RULES:
1. ONLY make claims grounded in the provided specifications above. DO NOT invent specs, ratings, or features.
2. If a specific specification is missing or unverified (e.g., operating voltage, price, or material), DO NOT guess or state a specific numerical claim about it.
3. TITLE: Create a concise, clear product title (e.g. "ACME 18V Cordless Drill Driver Kit").
4. SHORT DESCRIPTION: Write a compelling 2-3 sentence overview highlighting the product's core purpose and key benefits.
5. FEATURE BULLETS: Provide 4 to 6 bullet points detailing specific features, materials, certifications, or performance specs.
6. FAQ: Provide 3 to 4 realistic buyer Q&A pairs (e.g., "What is included?", "What certifications does this have?"). FAQ answers MUST be strictly factual and based only on provided specs. Omit any question that cannot be answered directly from the data.
7. GROUNDING TRACKING: For each copy section (title, short_description, feature_bullets, faq), list the input attribute field names used to ground that section in a "grounded_by" array (e.g., ["name", "voltage", "material"]).

OUTPUT FORMAT:
Return ONLY a valid JSON object with NO markdown formatting, NO ```json blocks, NO preamble.

REQUIRED JSON SHAPE:
{{
  "title": {{
    "value": "Concise product title",
    "grounded_by": ["name", "category"]
  }},
  "short_description": {{
    "value": "2-3 sentence summary...",
    "grounded_by": ["name", "category", "voltage", "material"]
  }},
  "feature_bullets": {{
    "value": [
      "Bullet point 1...",
      "Bullet point 2...",
      "Bullet point 3...",
      "Bullet point 4..."
    ],
    "grounded_by": ["material", "voltage", "certifications", "dimensions"]
  }},
  "faq": {{
    "value": [
      {{"question": "Buyer question 1?", "answer": "Grounded answer 1."}},
      {{"question": "Buyer question 2?", "answer": "Grounded answer 2."}}
    ],
    "grounded_by": ["certifications", "additional_attributes"]
  }}
}}
"""

    raw_text = ""
    try:
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
        except Exception:
            model = genai.GenerativeModel("gemini-flash-latest")
            response = model.generate_content(prompt)

        raw_text = response.text or ""
    except Exception as err:
        raise CopyGenerationError(f"Gemini API call for copy generation failed: {err}") from err

    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as err:
        raise CopyGenerationError(
            f"Failed to parse generated copy as JSON: {err}",
            raw_response=raw_text
        ) from err

    # Helper function to compute source_type and confidence score from grounding fields
    def compute_field_provenance(grounded_by_list: List[str]) -> tuple[str, float]:
        if not grounded_by_list:
            return "extracted", 1.0

        source_types = []
        confidences = []

        for field_name in grounded_by_list:
            if hasattr(record, field_name):
                attr = getattr(record, field_name)
                if isinstance(attr, list):
                    for sub_item in attr:
                        if hasattr(sub_item, "source_type"):
                            source_types.append(sub_item.source_type)
                            confidences.append(sub_item.confidence)
                elif hasattr(attr, "source_type"):
                    source_types.append(attr.source_type)
                    confidences.append(attr.confidence)

        # If any grounding field is inferred, mark the generated copy as inferred
        final_type = "inferred" if "inferred" in source_types else "extracted"
        avg_conf = round(sum(confidences) / len(confidences), 2) if confidences else 1.0

        return final_type, avg_conf

    # Map Title
    title_raw = data.get("title", {})
    t_val = title_raw.get("value")
    t_ground = title_raw.get("grounded_by", ["name", "category"])
    t_type, t_conf = compute_field_provenance(t_ground)
    record.title = CommerceCopyField[str](value=t_val, source_type=t_type, confidence=t_conf)

    # Map Short Description
    desc_raw = data.get("short_description", {})
    d_val = desc_raw.get("value")
    d_ground = desc_raw.get("grounded_by", ["name", "category"])
    d_type, d_conf = compute_field_provenance(d_ground)
    record.short_description = CommerceCopyField[str](value=d_val, source_type=d_type, confidence=d_conf)

    # Map Feature Bullets
    bullets_raw = data.get("feature_bullets", {})
    b_val = bullets_raw.get("value", [])
    b_ground = bullets_raw.get("grounded_by", ["name", "category"])
    b_type, b_conf = compute_field_provenance(b_ground)
    record.feature_bullets = CommerceCopyField[List[str]](value=b_val, source_type=b_type, confidence=b_conf)

    # Map FAQ
    faq_raw = data.get("faq", {})
    f_items_raw = faq_raw.get("value", [])
    f_ground = faq_raw.get("grounded_by", ["name", "category"])
    f_type, f_conf = compute_field_provenance(f_ground)

    faq_list = []
    if isinstance(f_items_raw, list):
        for item in f_items_raw:
            if isinstance(item, dict) and "question" in item and "answer" in item:
                faq_list.append(FAQItem(question=item["question"], answer=item["answer"]))

    record.faq = CommerceCopyField[List[FAQItem]](value=faq_list, source_type=f_type, confidence=f_conf)

    return record


if __name__ == "__main__":
    ref_path = "data/reference/sample_products.json"
    ref_dataset = []
    if os.path.exists(ref_path):
        with open(ref_path, "r", encoding="utf-8") as f:
            ref_dataset = json.load(f)

    test_files = [
        "data/samples/cordless_drill_spec.pdf",
        "data/samples/led_flashlight_spec.pdf"
    ]

    print("==========================================================")
    print("      SpecSense E-Commerce Copy Generator Pipeline Test   ")
    print("==========================================================")

    for pdf_file in test_files:
        full_path = os.path.abspath(pdf_file)
        filename = os.path.basename(pdf_file)
        print(f"\n" + "=" * 60)
        print(f" PROCESSING FILE: {filename}")
        print("=" * 60)

        try:
            # Step 1: PDF Line Extraction
            cited_text, offsets = get_full_text_with_citations(full_path)
            
            # Step 2: LLM Field Extraction
            raw_llm_json = extract_structured_fields(cited_text, source_filename=filename)
            
            # Step 3: Build Product Record
            rec = build_product_record(raw_llm_json, filename, cited_text)
            
            # Step 4: Infer Missing Fields
            rec = infer_missing_fields(rec, ref_dataset)
            
            # Step 5: Generate Grounded E-Commerce Copy
            rec = generate_commerce_copy(rec)

            print("\n[Generated E-Commerce Copy Output]")
            print(f"\nTITLE ({rec.title.source_type}, conf: {rec.title.confidence}):")
            print(f"  {rec.title.value}")

            print(f"\nSHORT DESCRIPTION ({rec.short_description.source_type}, conf: {rec.short_description.confidence}):")
            print(f"  {rec.short_description.value}")

            print(f"\nFEATURE BULLETS ({rec.feature_bullets.source_type}, conf: {rec.feature_bullets.confidence}):")
            if rec.feature_bullets.value:
                for b in rec.feature_bullets.value:
                    print(f"  • {b}")

            print(f"\nFAQ ({rec.faq.source_type}, conf: {rec.faq.confidence}):")
            if rec.faq.value:
                for item in rec.faq.value:
                    print(f"  Q: {item.question}")
                    print(f"  A: {item.answer}\n")

            print("-" * 60)

        except Exception as err:
            print(f"[ERROR] Failed to process {filename}: {err}")
