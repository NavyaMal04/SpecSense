import os
import sys
from typing import List, Dict, Tuple, Any
import pdfplumber


class PDFExtractionError(Exception):
    """Custom exception raised when PDF text extraction fails or yields no extractable text."""
    pass


def extract_text_with_offsets(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Opens a PDF document using pdfplumber and extracts line-by-line text with offset citations.

    Args:
        pdf_path: Absolute or relative path to the PDF file.

    Returns:
        List of dicts, each containing:
        {
            "text": str,       # Cleaned line text
            "page": int,       # 1-indexed page number
            "line": int        # 1-indexed line number on that page
        }

    Raises:
        PDFExtractionError: If file is missing, corrupted, unreadable, or contains no text.
    """
    if not os.path.exists(pdf_path):
        raise PDFExtractionError(f"PDF file not found at path: {pdf_path}")

    line_records: List[Dict[str, Any]] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                raise PDFExtractionError(f"PDF file '{pdf_path}' contains no pages.")

            for page_idx, page in enumerate(pdf.pages, start=1):
                try:
                    page_text = page.extract_text()
                except Exception as page_err:
                    # Log page error but attempt to continue if possible
                    continue

                if not page_text:
                    continue

                line_num = 1
                for raw_line in page_text.splitlines():
                    cleaned_line = raw_line.strip()
                    if not cleaned_line:
                        continue

                    line_records.append({
                        "text": cleaned_line,
                        "page": page_idx,
                        "line": line_num
                    })
                    line_num += 1

    except PDFExtractionError:
        raise
    except Exception as err:
        raise PDFExtractionError(f"Failed to process PDF file '{pdf_path}': {str(err)}") from err

    if not line_records:
        raise PDFExtractionError(f"No extractable text found in PDF file '{pdf_path}'.")

    return line_records


def get_full_text_with_citations(pdf_path: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Extracts text line-by-line and formats a single aggregated string with citation tags.

    Args:
        pdf_path: Path to the target PDF file.

    Returns:
        Tuple of:
        - full_text: Aggregated string with citation tags like [P1L3] preceding each line.
        - offsets: The original list of line offset dictionaries for lookup.
    """
    offsets = extract_text_with_offsets(pdf_path)

    formatted_lines = [
        f"[P{item['page']}L{item['line']}] {item['text']}"
        for item in offsets
    ]
    full_text = "\n".join(formatted_lines)

    return full_text, offsets


if __name__ == "__main__":
    # Small test script to verify extraction on sample PDF
    target_path = sys.argv[1] if len(sys.argv) > 1 else "data/samples/sample_spec.pdf"
    
    print(f"--- SpecSense PDF Extractor Test ---")
    print(f"Target PDF Path: {os.path.abspath(target_path)}")

    if not os.path.exists(target_path):
        print(f"\n[NOTE] No sample PDF found at '{target_path}'.")
        print("To test extraction, place a sample spec sheet PDF into 'data/samples/' and run:")
        print("    python -m pipeline.extractor data/samples/your_spec.pdf")
    else:
        try:
            full_text, line_offsets = get_full_text_with_citations(target_path)
            print(f"\nSuccessfully extracted {len(line_offsets)} lines of text.")
            print("\n--- First 10 Lines with Citations ---")
            
            lines_to_show = formatted_lines = full_text.splitlines()[:10]
            for line in lines_to_show:
                print(line)
                
            print("\n--- End of Preview ---")

        except PDFExtractionError as e:
            print(f"\n[ERROR] PDFExtractionError caught: {e}")
        except Exception as e:
            print(f"\n[UNEXPECTED ERROR] {e}")
