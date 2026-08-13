import os
import sys
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai

from pipeline.extractor import get_full_text_with_citations, PDFExtractionError

# Load environment variables from .env file
load_dotenv()


class LLMExtractionError(Exception):
    """Custom exception raised when LLM structured field extraction or parsing fails."""
    def __init__(self, message: str, raw_response: Optional[str] = None):
        super().__init__(message)
        self.raw_response = raw_response


def _init_gemini_client():
    """Initializes the Gemini API client using GEMINI_API_KEY from environment."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise LLMExtractionError(
            "GEMINI_API_KEY is missing or invalid in your .env file. "
            "Please add a valid Google AI Studio Gemini API key to your .env file."
        )
    genai.configure(api_key=api_key)


def extract_structured_fields(cited_text: str, source_filename: str = "") -> Dict[str, Any]:
    """
    Sends citation-tagged text to Gemini 1.5 Flash to extract core product fields 
    and category-specific additional attributes with line citation tags.

    Args:
        cited_text: Aggregated PDF text string with [P{page}L{line}] citation tags.
        source_filename: Optional name of the source PDF document.

    Returns:
        Dict containing structured fields and citations in the exact shape:
        {
          "name": {"value": ..., "citation": "[P1L1]"},
          "category": {"value": ..., "citation": "[P1L2]"},
          ...
          "additional_attributes": [
             {"name": "power_rating", "value": "450 W max output", "citation": "[P1L9]"}
          ]
        }

    Raises:
        LLMExtractionError: If API call fails or response cannot be parsed as valid JSON.
    """
    _init_gemini_client()

    prompt_template = """You are an expert product intelligence AI parsing technical product spec sheets.
Analyze the following spec sheet text where each line is prefixed with a citation tag like [P1L3] (Page 1, Line 3).

TARGET SPEC SHEET TEXT:
---
{cited_text}
---

INSTRUCTIONS:
1. Extract the following CORE PRODUCT FIELDS if present in the document:
   - name (Product Name)
   - category (Product Category)
   - dimensions (Dimensions/Size)
   - material (Material composition)
   - voltage (Operating Voltage/Electrical Specs)
   - certifications (Certifications, compliance, safety standards)
   - weight (Product Weight)
   - price (Price/Cost)

2. ALSO identify any ADDITIONAL ATTRIBUTES specified in the document that do NOT fit the 8 core fields above (e.g., power_rating, warranty, ip_rating, hazard_class, speed, torque, noise_level, chemical_composition, etc.). Extract them into an "additional_attributes" array.

3. FOR EVERY FIELD (both core fields and additional_attributes):
   - Include the extracted "value".
   - Include the exact "citation" tag where the value was found in the text (e.g. "[P1L5]").
   - If a core field is NOT present in the text, set its "value" to null and "citation" to null. DO NOT guess or infer missing values.
   - If a field appears with CONFLICTING or ambiguous values across different lines, return a list of all conflicting values with their respective citations (e.g. [{"value": "3.7V", "citation": "[P1L8]"}, {"value": "6V nominal", "citation": "[P1L9]"}]).
   - SAFETY & SCOPE NOTES: If a spec includes a clarifying note, scope limitation, or safety warning (e.g. "Note: Electrical rating refers to helmet shell only..."), preserve this critical context either inside the field's value or as a dedicated item in additional_attributes (e.g. name: "electrical_rating_scope" or "safety_note"). Never omit safety/scope disclaimers.

4. OUTPUT FORMAT:
   Return ONLY a valid JSON object. No markdown block markers (no ```json), no explanation, no extra text.

EXACT JSON SHAPE REQUIRED:
{
  "name": {"value": "Product Name", "citation": "[P1L1]"},
  "category": {"value": "Category", "citation": "[P1L2]"},
  "dimensions": {"value": "Dimensions", "citation": "[P1L3]"},
  "material": {"value": "Material", "citation": "[P1L4]"},
  "voltage": {"value": "Voltage", "citation": "[P1L5]"},
  "certifications": {"value": "Certifications", "citation": "[P1L6]"},
  "weight": {"value": "Weight", "citation": "[P1L7]"},
  "price": {"value": "Price", "citation": "[P1L8]"},
  "additional_attributes": [
    {"name": "attribute_name", "value": "attribute_value", "citation": "[P1L9]"}
  ]
}
"""
    prompt = prompt_template.replace("{cited_text}", cited_text)

    raw_response_text = ""
    try:
        # Use gemini-2.5-flash (or gemini-flash-latest fallback)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
        except Exception:
            model = genai.GenerativeModel("gemini-flash-latest")
            response = model.generate_content(prompt)
        raw_response_text = response.text or ""
    except Exception as err:
        raise LLMExtractionError(f"Gemini API call failed: {str(err)}") from err

    cleaned_text = raw_response_text.strip()
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:]
    elif cleaned_text.startswith("```"):
        cleaned_text = cleaned_text[3:]
    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3]
    cleaned_text = cleaned_text.strip()

    try:
        parsed_data = json.loads(cleaned_text)
    except json.JSONDecodeError as err:
        raise LLMExtractionError(
            f"Failed to parse Gemini response as JSON: {err}",
            raw_response=raw_response_text
        ) from err

    return parsed_data


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_files = [sys.argv[1]]
    else:
        test_files = [
            "data/samples/cordless_drill_spec.pdf",
            "data/samples/led_flashlight_spec.pdf",
            "data/samples/industrial_degreaser_spec.pdf",
            "data/samples/safety_helmet_spec.pdf"
        ]
    
    print("==========================================================")
    print("      SpecSense Gemini Multi-Sample Extractor Test       ")
    print("==========================================================")

    core_keys = ["name", "category", "dimensions", "material", "voltage", "certifications", "weight", "price"]

    for pdf_file in test_files:
        full_path = os.path.abspath(pdf_file)
        filename = os.path.basename(pdf_file)
        print(f"\n" + "=" * 60)
        print(f" TESTING FILE: {filename}")
        print(f" Path: {full_path}")
        print("=" * 60)

        if not os.path.exists(full_path):
            print(f" [SKIP] File not found: {full_path}")
            continue

        try:
            cited_text, line_offsets = get_full_text_with_citations(full_path)
            print(f" [1] Extracted {len(line_offsets)} line citation offsets.")
            print(f" [2] Extracting structured fields via Gemini...")

            structured_json = extract_structured_fields(cited_text, source_filename=filename)

            print("\n [3] Structured JSON Result:")
            print(json.dumps(structured_json, indent=2))

            # Compute summary stats
            filled_count = 0
            null_count = 0
            conflicting_count = 0

            for k in core_keys:
                field_val = structured_json.get(k)
                if field_val is None:
                    null_count += 1
                elif isinstance(field_val, list):
                    conflicting_count += 1
                elif isinstance(field_val, dict):
                    if field_val.get("value") is None:
                        null_count += 1
                    else:
                        filled_count += 1
                else:
                    filled_count += 1

            additional_attrs = structured_json.get("additional_attributes", [])
            add_count = len(additional_attrs) if isinstance(additional_attrs, list) else 0

            print("\n" + "-" * 60)
            print(f" SUMMARY FOR {filename}:")
            print(f"   Core Fields Filled:       {filled_count} / {len(core_keys)}")
            print(f"   Core Fields Null/Missing: {null_count} / {len(core_keys)}")
            if conflicting_count > 0:
                print(f"   Conflicting Core Fields:  {conflicting_count}")
            print(f"   Additional Attributes:    {add_count}")
            print("-" * 60)

        except PDFExtractionError as pe:
            print(f" [PDF ERROR] {pe}")
        except LLMExtractionError as le:
            print(f" [LLM ERROR] {le}")
            if le.raw_response:
                print(f" Raw response:\n{le.raw_response}")
        except Exception as e:
            print(f" [UNEXPECTED ERROR] {e}")
