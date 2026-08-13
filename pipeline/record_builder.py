import os
import sys
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from pipeline.schema import ProductRecord, AttributeField, SourceType
from pipeline.extractor import get_full_text_with_citations, PDFExtractionError
from pipeline.llm_extractor import extract_structured_fields, LLMExtractionError


def _clean_citation_tag(cit: Optional[str]) -> Optional[str]:
    """Helper to format citation tags cleanly without double-bracket wrapping."""
    if not cit:
        return None
    cit_str = str(cit).strip()
    if not cit_str or cit_str.lower() in ["none", "null"]:
        return None
    clean_inner = cit_str.strip("[]").strip()
    return f"[{clean_inner}]" if clean_inner else None


def build_product_record(raw_llm_output: Dict[str, Any], source_filename: str, raw_text: str) -> ProductRecord:
    """
    Maps raw structured output from LLM extraction into a validated ProductRecord schema instance.

    Args:
        raw_llm_output: Raw dict output from extract_structured_fields().
        source_filename: Name of the source PDF spec sheet file.
        raw_text: Full raw text extracted from the PDF before processing.

    Returns:
        ProductRecord instance with fields populated with value, source_type, confidence, and source_location.
    """
    record_dict: Dict[str, Any] = {
        "source_file": source_filename,
        "raw_extracted_text": raw_text,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "review_status": "pending",
    }

    has_flagged_field = False
    core_keys = ["name", "category", "dimensions", "material", "voltage", "certifications", "weight", "price"]

    for key in core_keys:
        field_data = raw_llm_output.get(key)

        # Case 1: Array of conflicting extracted values
        if isinstance(field_data, list):
            has_flagged_field = True
            conflict_descriptions = []
            first_val = None

            for idx, item in enumerate(field_data):
                if isinstance(item, dict):
                    v = item.get("value")
                    c = _clean_citation_tag(item.get("citation"))
                    if idx == 0:
                        first_val = v
                    conflict_descriptions.append(f"'{v}' {c}" if c else f"'{v}'")
                else:
                    if idx == 0:
                        first_val = str(item)
                    conflict_descriptions.append(f"'{item}'")

            conflict_loc_str = f"Conflict: {' vs '.join(conflict_descriptions)}"

            # Parse numeric price if key is price
            parsed_val = first_val
            if key == "price" and first_val is not None:
                try:
                    parsed_val = float(str(first_val).replace("$", "").replace(",", "").strip())
                except ValueError:
                    parsed_val = None

            # Certifications list parsing
            if key == "certifications" and isinstance(first_val, str):
                parsed_val = [c.strip() for c in first_val.split(",") if c.strip()]

            record_dict[key] = AttributeField(
                value=parsed_val,
                source_type="flagged",
                confidence=0.4,
                source_location=conflict_loc_str
            )

        # Case 2: Dict containing value & citation
        elif isinstance(field_data, dict):
            val = field_data.get("value")
            cit = _clean_citation_tag(field_data.get("citation"))

            if val is None or str(val).strip().lower() in ["null", "none", "n/a"]:
                record_dict[key] = AttributeField(
                    value=None,
                    source_type="extracted",
                    confidence=0.0,
                    source_location=None
                )
            else:
                parsed_val = val
                if key == "price" and val is not None:
                    try:
                        # Extract float number from price string if necessary
                        clean_price_str = "".join([char for char in str(val) if char.isdigit() or char == "."])
                        parsed_val = float(clean_price_str) if clean_price_str else None
                    except ValueError:
                        parsed_val = None

                if key == "certifications":
                    if isinstance(val, str):
                        parsed_val = [c.strip() for c in val.split(",") if c.strip()]
                    elif not isinstance(val, list):
                        parsed_val = [str(val)]

                record_dict[key] = AttributeField(
                    value=parsed_val,
                    source_type="extracted",
                    confidence=1.0,
                    source_location=cit
                )

        # Case 3: Missing or null field
        else:
            record_dict[key] = AttributeField(
                value=None,
                source_type="extracted",
                confidence=0.0,
                source_location=None
            )

    # Process additional attributes
    mapped_additional: List[AttributeField[str]] = []
    raw_additional = raw_llm_output.get("additional_attributes", [])

    if isinstance(raw_additional, list):
        for item in raw_additional:
            if isinstance(item, dict):
                attr_name = item.get("name", "attribute")
                attr_val = item.get("value")
                attr_cit = _clean_citation_tag(item.get("citation"))

                if attr_val is not None:
                    formatted_val = f"{attr_name}: {attr_val}"
                    mapped_additional.append(
                        AttributeField[str](
                            value=formatted_val,
                            source_type="extracted",
                            confidence=1.0,
                            source_location=attr_cit
                        )
                    )
            elif isinstance(item, list):
                # Conflicting additional attribute
                has_flagged_field = True
                conflict_descriptions = [f"'{x.get('value')}' {_clean_citation_tag(x.get('citation')) or ''}".strip() for x in item if isinstance(x, dict)]
                first_name = item[0].get("name", "attribute") if isinstance(item[0], dict) else "attribute"
                first_val = item[0].get("value", "") if isinstance(item[0], dict) else ""
                conflict_loc_str = f"Conflict: {' vs '.join(conflict_descriptions)}"
                
                mapped_additional.append(
                    AttributeField[str](
                        value=f"{first_name}: {first_val}",
                        source_type="flagged",
                        confidence=0.4,
                        source_location=conflict_loc_str
                    )
                )

    record_dict["additional_attributes"] = mapped_additional
    record_dict["review_status"] = "flagged" if has_flagged_field else "pending"

    return ProductRecord(**record_dict)


def infer_missing_fields(record: ProductRecord, reference_dataset: List[Dict[str, Any]]) -> ProductRecord:
    """
    Infers missing fields (where value is None) using TF-IDF cosine similarity against reference product dataset.

    Args:
        record: ProductRecord with extracted fields.
        reference_dataset: List of reference product dicts with known attributes.

    Returns:
        Updated ProductRecord with inferred fields labeled source_type="inferred" and confidence 0.6-0.85.
    """
    if not reference_dataset:
        return record

    # Product query string from name and category
    prod_name = record.name.value or ""
    prod_cat = record.category.value or ""
    query_str = f"{prod_name} {prod_cat}".strip()

    if not query_str:
        return record

    # Build reference document corpus
    corpus = [
        f"{item.get('name', '')} {item.get('category', '')}"
        for item in reference_dataset
    ]

    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(corpus + [query_str])
        query_vec = tfidf_matrix[-1]
        ref_vecs = tfidf_matrix[:-1]

        sim_scores = cosine_similarity(query_vec, ref_vecs)[0]
    except Exception:
        return record

    # Find matching indices with similarity > 0.15 or category exact match
    matching_indices = []
    for idx, ref in enumerate(reference_dataset):
        score = sim_scores[idx]
        ref_cat = str(ref.get("category", "")).lower()
        query_cat_lower = prod_cat.lower()

        # Category overlap boost
        is_category_match = (
            query_cat_lower and ref_cat and
            (query_cat_lower in ref_cat or ref_cat in query_cat_lower)
        )

        if score >= 0.15 or is_category_match:
            effective_score = score + (0.25 if is_category_match else 0.0)
            matching_indices.append((idx, effective_score))

    matching_indices.sort(key=lambda x: x[1], reverse=True)

    if not matching_indices:
        return record

    # Core fields to consider for inference if None
    fields_to_check = ["price", "weight", "material", "voltage"]

    for field in fields_to_check:
        field_obj: Optional[AttributeField] = getattr(record, field, None)
        if field_obj is not None and field_obj.value is None:

            # Check if this field applies to the category (e.g. voltage doesn't apply to chemicals)
            if field == "voltage" and "chemical" in prod_cat.lower():
                continue

            # Gather candidate values from top reference matches
            candidate_vals = []
            top_sim = matching_indices[0][1]

            for idx, score in matching_indices[:5]:
                ref_item = reference_dataset[idx]
                ref_val = ref_item.get(field)
                if ref_val is not None:
                    candidate_vals.append(ref_val)

            if candidate_vals:
                inferred_value = None
                
                # Numeric calculation for price
                if field == "price":
                    numeric_prices = []
                    for v in candidate_vals:
                        try:
                            numeric_prices.append(float(v))
                        except (ValueError, TypeError):
                            pass
                    if numeric_prices:
                        inferred_value = round(sum(numeric_prices) / len(numeric_prices), 2)
                else:
                    # Categorical mode pick
                    inferred_value = candidate_vals[0]

                if inferred_value is not None:
                    confidence_score = round(min(0.85, max(0.60, float(top_sim))), 2)
                    setattr(
                        record,
                        field,
                        AttributeField(
                            value=inferred_value,
                            source_type="inferred",
                            confidence=confidence_score,
                            source_location=None
                        )
                    )

    return record


if __name__ == "__main__":
    test_pdf = sys.argv[1] if len(sys.argv) > 1 else "data/samples/cordless_drill_spec.pdf"
    ref_path = "data/reference/sample_products.json"

    print("==========================================================")
    print("      SpecSense Record Builder & Inference Layer Test     ")
    print("==========================================================")
    print(f"Target PDF: {os.path.abspath(test_pdf)}")

    # 1. Load reference dataset
    ref_dataset = []
    if os.path.exists(ref_path):
        with open(ref_path, "r", encoding="utf-8") as f:
            ref_dataset = json.load(f)
        print(f"Loaded {len(ref_dataset)} reference products from '{ref_path}'.")

    # 2. Run PDF Extraction
    print("\n[Step 1] Extracting text and citation offsets...")
    cited_text, offsets = get_full_text_with_citations(test_pdf)

    # 3. Run LLM Structured Field Extraction
    print("[Step 2] Running Gemini structured field extraction...")
    raw_llm_json = extract_structured_fields(cited_text, source_filename=os.path.basename(test_pdf))

    # 4. Build Product Record (Extracted & Flagged Mapping)
    print("[Step 3] Building ProductRecord (Mapping extracted & flagged fields)...")
    initial_record = build_product_record(raw_llm_json, os.path.basename(test_pdf), cited_text)

    # 5. Run Missing Field Inference
    print("[Step 4] Running missing field inference against reference catalog...")
    final_record = infer_missing_fields(initial_record, ref_dataset)

    # 6. Output Final ProductRecord
    print("\n[Step 5] Final Processed Product Record:")
    print(json.dumps(final_record.model_dump(), indent=2))

    print("\n" + "=" * 60)
    print(" FIELD PROVENANCE & EXPLAINABILITY SUMMARY:")
    print("=" * 60)
    
    core_keys = ["name", "category", "dimensions", "material", "voltage", "certifications", "weight", "price"]
    for k in core_keys:
        field_attr: AttributeField = getattr(final_record, k)
        val_str = f"'{field_attr.value}'" if field_attr.value is not None else "None"
        loc_str = f" (Citation: {field_attr.source_location})" if field_attr.source_location else ""
        print(f"  - {k:<15}: {val_str:<45} | Type: {field_attr.source_type:<10} | Confidence: {field_attr.confidence:.2f}{loc_str}")

    print("\n  Additional Attributes:")
    for add_attr in final_record.additional_attributes:
        print(f"  - {add_attr.value:<58} | Type: {add_attr.source_type:<10} | Confidence: {add_attr.confidence:.2f} (Citation: {add_attr.source_location})")
    print("=" * 60)
