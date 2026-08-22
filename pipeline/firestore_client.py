"""
firestore_client.py
====================
Firestore persistence layer for the SpecSense 252-column UniHack pipeline.

Provides core operations on the "products" collection:
  - save_product_record()       — upsert a ProductRecord (auto-generate or use existing ID)
  - get_product_record()        — fetch by document ID and parse into ProductRecord
  - list_product_records()      — lightweight summary list (all or filtered by review_status)
  - get_dashboard_stats()       — compute aggregate metrics (total, completeness %, status counts)
  - update_review_status()      — patch review_status field ("pending" / "approved" / "flagged")

Credentials are loaded from FIREBASE_CREDENTIALS_PATH in .env.
"""

import os
import sys
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from pipeline.schema import ProductRecord

load_dotenv()

# ---------------------------------------------------------------------------
# Module-level Firebase app singleton — initialised once on first import
# ---------------------------------------------------------------------------
_db: Optional[firestore.Client] = None
COLLECTION = "products"


def _get_db() -> firestore.Client:
    """
    Returns a Firestore client, initialising Firebase Admin SDK on first call.

    Reads FIREBASE_CREDENTIALS_PATH from the environment. Raises a clear
    RuntimeError if the credentials file is absent or the SDK fails to start.
    """
    global _db
    if _db is not None:
        return _db

    creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if not creds_path:
        raise RuntimeError(
            "FIREBASE_CREDENTIALS_PATH is not set in your .env file. "
            "Add the path to your Firebase service-account JSON."
        )

    abs_creds = os.path.abspath(creds_path)
    if not os.path.isfile(abs_creds):
        raise RuntimeError(
            f"Firebase credentials file not found at: {abs_creds}\n"
            "Verify that FIREBASE_CREDENTIALS_PATH in your .env points to the "
            "correct service-account JSON file."
        )

    # Only initialise if no default app exists yet (guard against re-imports)
    if not firebase_admin._apps:
        cred = credentials.Certificate(abs_creds)
        firebase_admin.initialize_app(cred)

    _db = firestore.client()
    return _db


# ---------------------------------------------------------------------------
# Helper: Extract lightweight summary dict from a raw document dict
# ---------------------------------------------------------------------------

def _extract_summary(doc_id: str, data: dict) -> Dict[str, Any]:
    """
    Extracts a lightweight representation for fast list/table views in the UI.
    Avoids returning deep 50-attribute objects over the network.
    """
    def _val(field: str) -> Optional[str]:
        v = data.get(field)
        if isinstance(v, dict):
            return v.get("value")
        return v if isinstance(v, str) else None

    found = data.get("fields_found_count") or 0
    total = data.get("fields_total_count") or 0
    completeness = round((found / total * 100), 1) if total > 0 else 0.0

    mfg_part_num = data.get("mfg_part_num") or data.get("part_number") or ""
    part_desc = data.get("part_desc") or ""
    prod_name = _val("product_name") or part_desc
    mfr_name = _val("manufacturer_name") or data.get("part_manuf") or ""
    brand_name = _val("brand_name") or ""
    classpath = _val("classpath") or ""

    return {
        "id": doc_id,
        "mfg_part_num": mfg_part_num,
        "part_number": data.get("part_number") or mfg_part_num,
        "part_desc": part_desc,
        "product_name": prod_name,
        "name": prod_name,  # convenient alias for frontend
        "manufacturer_name": mfr_name,
        "brand_name": brand_name,
        "category": classpath,
        "classpath": classpath,
        "fields_found_count": found,
        "fields_total_count": total,
        "completeness_pct": completeness,
        "review_status": data.get("review_status", "pending"),
        "processed_at": data.get("processed_at"),
    }


# ---------------------------------------------------------------------------
# Public Operations
# ---------------------------------------------------------------------------

def save_product_record(record: ProductRecord) -> str:
    """
    Saves or updates a ProductRecord in Firestore (collection: 'products').

    - If record.id is set   → updates/overwrites document at that ID.
    - If record.id is None  → auto-generates document ID and sets it on record.id.

    Returns:
        The Firestore document ID (str).
    """
    try:
        db = _get_db()
        collection_ref = db.collection(COLLECTION)
        payload = record.model_dump()

        if record.id:
            doc_ref = collection_ref.document(record.id)
            payload["id"] = record.id
            doc_ref.set(payload)
        else:
            _, doc_ref = collection_ref.add(payload)
            record.id = doc_ref.id
            doc_ref.update({"id": record.id})

        return record.id

    except RuntimeError:
        raise
    except Exception as err:
        raise Exception(f"[Firestore] Failed to save product record: {err}") from err


def get_product_record(doc_id: str) -> ProductRecord:
    """
    Fetches a single ProductRecord from Firestore by document ID.

    Raises:
        KeyError: If no document exists with doc_id.
        Exception: On network or parsing errors.
    """
    try:
        db = _get_db()
        doc_ref = db.collection(COLLECTION).document(doc_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise KeyError(
                f"[Firestore] No product found with document ID '{doc_id}'. "
                f"Verify the ID or check the '{COLLECTION}' collection."
            )

        data = doc.to_dict()
        return ProductRecord.model_validate(data)

    except (KeyError, RuntimeError):
        raise
    except Exception as err:
        raise Exception(f"[Firestore] Failed to fetch product record '{doc_id}': {err}") from err


def find_product_by_mpn(mpn: str) -> Optional[ProductRecord]:
    """
    Finds a ProductRecord in Firestore by MPN or document ID.
    Checks document ID directly first, then queries by 'mfg_part_num' and 'part_number'.
    Returns None if not found or if Firestore is unavailable.
    """
    if not mpn or not str(mpn).strip():
        return None
    cleaned_mpn = str(mpn).strip()
    safe_mpn = "".join(c if c.isalnum() or c in "-_" else "_" for c in cleaned_mpn)

    try:
        db = _get_db()
    except Exception as e:
        print(f"[Firestore] DB connection unavailable during find_product_by_mpn: {e}")
        return None

    # 1. Try direct document lookup by exact MPN
    try:
        doc = db.collection(COLLECTION).document(cleaned_mpn).get()
        if doc.exists:
            return ProductRecord.model_validate(doc.to_dict())
    except Exception:
        pass

    # 2. Try direct document lookup by safe MPN if different
    if safe_mpn != cleaned_mpn:
        try:
            doc = db.collection(COLLECTION).document(safe_mpn).get()
            if doc.exists:
                return ProductRecord.model_validate(doc.to_dict())
        except Exception:
            pass

    # 3. Query collection by mfg_part_num
    try:
        query = db.collection(COLLECTION).where(filter=FieldFilter("mfg_part_num", "==", cleaned_mpn)).limit(1)
        docs = list(query.stream())
        if docs:
            return ProductRecord.model_validate(docs[0].to_dict())
    except Exception:
        pass

    # 4. Query collection by part_number
    try:
        query = db.collection(COLLECTION).where(filter=FieldFilter("part_number", "==", cleaned_mpn)).limit(1)
        docs = list(query.stream())
        if docs:
            return ProductRecord.model_validate(docs[0].to_dict())
    except Exception:
        pass

    return None


def list_product_records(review_status: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Returns a lightweight summary list of product records for fast UI display.

    Args:
        review_status: Optional filter ("pending", "approved", "flagged").
                       If None, returns all records.

    Returns:
        List of dicts with keys: id, mfg_part_num, part_desc, product_name, name,
        manufacturer_name, brand_name, category, classpath, fields_found_count,
        fields_total_count, completeness_pct, review_status, processed_at.
    """
    valid_statuses = {"pending", "approved", "flagged"}
    if review_status is not None and review_status not in valid_statuses:
        raise ValueError(
            f"[Firestore] Invalid review_status '{review_status}'. "
            f"Must be one of: {', '.join(sorted(valid_statuses))}."
        )

    try:
        db = _get_db()
        query = db.collection(COLLECTION)

        if review_status is not None:
            query = query.where(filter=FieldFilter("review_status", "==", review_status))

        docs = query.stream()
        summaries = []
        for doc in docs:
            try:
                data = doc.to_dict()
                summaries.append(_extract_summary(doc.id, data))
            except Exception as parse_err:
                print(f"[Firestore] Warning: Could not summarize doc '{doc.id}': {parse_err}")

        return summaries

    except (ValueError, RuntimeError):
        raise
    except Exception as err:
        raise Exception(f"[Firestore] Failed to list product records: {err}") from err


def get_dashboard_stats() -> Dict[str, Any]:
    """
    Computes aggregate metrics across all product records in the collection:
      - total_products: count of all documents
      - avg_completeness_pct: average completeness % across all documents
      - pending_count: count of records in 'pending' review status
      - flagged_count: count of records in 'flagged' review status
      - approved_count: count of records in 'approved' review status
    """
    try:
        db = _get_db()
        docs = db.collection(COLLECTION).stream()

        total = 0
        completeness_sum = 0.0
        pending = 0
        flagged = 0
        approved = 0

        for doc in docs:
            data = doc.to_dict()
            total += 1
            status = data.get("review_status", "pending")
            if status == "flagged":
                flagged += 1
            elif status == "approved":
                approved += 1
            else:
                pending += 1

            found = data.get("fields_found_count") or 0
            total_fields = data.get("fields_total_count") or 0
            if total_fields > 0:
                completeness_sum += (found / total_fields * 100)

        avg_completeness = round(completeness_sum / total, 1) if total > 0 else 0.0

        return {
            "total_products": total,
            "avg_completeness_pct": avg_completeness,
            "pending_count": pending,
            "flagged_count": flagged,
            "approved_count": approved,
        }

    except RuntimeError:
        raise
    except Exception as err:
        raise Exception(f"[Firestore] Failed to compute dashboard stats: {err}") from err


def update_review_status(doc_id: str, new_status: str) -> None:
    """
    Patches the review_status field on an existing Firestore document.

    Args:
        doc_id: The document ID to update.
        new_status: "pending", "approved", or "flagged".
    """
    valid_statuses = {"pending", "approved", "flagged"}
    if new_status not in valid_statuses:
        raise ValueError(
            f"[Firestore] Invalid review_status '{new_status}'. "
            f"Must be one of: {', '.join(sorted(valid_statuses))}."
        )

    try:
        db = _get_db()
        doc_ref = db.collection(COLLECTION).document(doc_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise KeyError(f"[Firestore] Cannot update — no document found with ID '{doc_id}'.")

        doc_ref.update({"review_status": new_status})

    except (ValueError, KeyError, RuntimeError):
        raise
    except Exception as err:
        raise Exception(f"[Firestore] Failed to update review_status for '{doc_id}': {err}") from err


def delete_product_record(doc_id: str) -> None:
    """
    Deletes a product document from the Firestore "products" collection.

    Args:
        doc_id: The document ID to delete.

    Raises:
        KeyError: If the document does not exist.
        Exception: On Firestore network or permission errors.
    """
    try:
        db = _get_db()
        doc_ref = db.collection(COLLECTION).document(doc_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise KeyError(f"[Firestore] Cannot delete — no document found with ID '{doc_id}'.")

        doc_ref.delete()

    except (KeyError, RuntimeError):
        raise
    except Exception as err:
        raise Exception(f"[Firestore] Failed to delete product record '{doc_id}': {err}") from err


def audit_products_collection(delete_invalid: bool = False) -> Dict[str, Any]:
    """
    Diagnostic tool: scans all documents in the "products" collection and validates
    each against the current ProductRecord schema.

    Identifies valid 252-column UniHack records vs leftover/legacy records from
    the old PDF-based schema.

    Args:
        delete_invalid: If True, automatically deletes invalid/legacy documents.

    Returns:
        Dict with keys: 'total_scanned', 'valid_count', 'invalid_count', 'valid_docs', 'invalid_docs'.
    """
    try:
        db = _get_db()
        docs = list(db.collection(COLLECTION).stream())

        valid_docs: List[Dict[str, Any]] = []
        invalid_docs: List[Dict[str, Any]] = []

        print("=" * 75)
        print(f"  FIRESTORE SCHEMA AUDIT — Auditing {len(docs)} Documents in '{COLLECTION}'")
        print("=" * 75)

        for doc in docs:
            doc_id = doc.id
            data = doc.to_dict()

            # Check for legacy PDF-pipeline fields
            is_legacy_pdf = (
                ("raw_extracted_text" in data or "faq" in data or "source_file" in data)
                and not data.get("mfg_part_num")
            )

            if is_legacy_pdf:
                invalid_docs.append({
                    "id": doc_id,
                    "error": "Legacy PDF-pipeline test record (contains raw_extracted_text / faq, missing mfg_part_num)",
                    "keys_present": list(data.keys()),
                    "name": data.get("name", {}).get("value") if isinstance(data.get("name"), dict) else data.get("name"),
                    "raw_data_preview": {k: str(data[k])[:40] for k in list(data.keys())[:8]},
                })
                continue

            try:
                # Attempt full schema validation
                record = ProductRecord.model_validate(data)
                mfr_val = record.manufacturer_name.value if record.manufacturer_name else ""
                valid_docs.append({
                    "id": doc_id,
                    "mfg_part_num": record.mfg_part_num or record.part_number,
                    "manufacturer": mfr_val,
                    "review_status": record.review_status,
                })
            except Exception as val_err:
                sample_keys = list(data.keys())[:8]
                invalid_docs.append({
                    "id": doc_id,
                    "error": str(val_err),
                    "keys_present": sample_keys,
                    "raw_data_preview": {k: str(data[k])[:40] for k in sample_keys},
                })

        print(f"\n  ✅ Valid Current Schema Documents : {len(valid_docs)} / {len(docs)}")
        print(f"  ❌ Invalid / Legacy Documents      : {len(invalid_docs)} / {len(docs)}")

        if invalid_docs:
            print("\n  " + "-" * 70)
            print("  LEFTOVER / INVALID DOCUMENTS FOUND:")
            print("  " + "-" * 70)
            for inv in invalid_docs:
                print(f"  • Doc ID : {inv['id']}")
                print(f"    Keys   : {inv['keys_present']}")
                print(f"    Preview: {inv['raw_data_preview']}")
                print(f"    Reason : {inv['error'][:120]}...")
                if delete_invalid:
                    delete_product_record(inv['id'])
                    print(f"    🗑️  DELETED from Firestore.")
                print()

        return {
            "total_scanned": len(docs),
            "valid_count": len(valid_docs),
            "invalid_count": len(invalid_docs),
            "valid_docs": valid_docs,
            "invalid_docs": invalid_docs,
        }

    except Exception as err:
        raise Exception(f"[Firestore] Schema audit failed: {err}") from err


# ---------------------------------------------------------------------------
# Test / Diagnostic Harness
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Force UTF-8 output on Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    import argparse
    parser = argparse.ArgumentParser(description="Firestore Client Diagnostic & Test")
    parser.add_argument("--audit", action="store_true", help="Run schema audit on collection")
    parser.add_argument("--delete-invalid", action="store_true", help="Delete invalid legacy records found during audit")
    args = parser.parse_args()

    # Run audit
    audit_res = audit_products_collection(delete_invalid=args.delete_invalid)

    print("\n" + "=" * 75)
    print("  CURRENT DASHBOARD STATS")
    print("=" * 75)
    stats = get_dashboard_stats()
    print(f"  Total Products In Firestore : {stats['total_products']}")
    print(f"  Avg Completeness            : {stats['avg_completeness_pct']}%")
    print(f"  Status Breakdown            : {stats['pending_count']} pending, {stats['flagged_count']} flagged, {stats['approved_count']} approved")
