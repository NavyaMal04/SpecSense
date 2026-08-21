from typing import Optional, List, Literal, Generic, TypeVar, Dict, Any
from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")


class FieldValue(BaseModel, Generic[T]):
    """
    Sub-model wrapping a field value with provenance and audit metadata.
    """
    value: Optional[Any] = None
    source_type: Literal["extracted", "inferred", "unavailable"] = "unavailable"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_url: Optional[str] = None
    source_snippet: Optional[str] = None

    @field_validator("value", mode="before")
    @classmethod
    def normalize_value(cls, v: Any) -> Any:
        if isinstance(v, bool):
            return "Yes" if v else "No"
        if isinstance(v, (list, tuple)):
            clean = [str(x).strip() for x in v if x is not None and str(x).strip()]
            return ", ".join(clean) if clean else None
        return v


class AttributeEntry(BaseModel):
    """
    Represents one of up to 50 product attribute slots (label, value, UOM).
    """
    label: FieldValue[str] = Field(default_factory=FieldValue)
    value: FieldValue[str] = Field(default_factory=FieldValue)
    uom: FieldValue[str] = Field(default_factory=FieldValue)


class FeatureEntry(BaseModel):
    """
    Represents a single item feature bullet point.
    """
    text: FieldValue[str] = Field(default_factory=FieldValue)


class AssetLink(BaseModel):
    """
    Represents a digital asset link (image, PDF spec sheet, manual, etc.).
    """
    asset_type: str = Field(description="e.g. 'product_image', 'specification_sheet', 'installation_manual'")
    url: FieldValue[str] = Field(default_factory=FieldValue)


class ProductRecord(BaseModel):
    """
    Enriched Product Record matching Unilog Delivery Format specifications.
    Includes provenance tracking for every enriched field.
    """
    # Identity / passthrough (raw given input fields, un-wrapped)
    id: Optional[str] = None
    source_row_index: Optional[int] = None
    part_number: Optional[str] = None
    dept: Optional[str] = None
    product_class: Optional[str] = None
    fine_class: Optional[str] = None
    sku: Optional[str] = None
    mfg_part_num: Optional[str] = None
    part_desc: Optional[str] = None
    e1_brand: Optional[str] = None
    unilog_brand: Optional[str] = None
    dib_brand: Optional[str] = None
    part_manuf: Optional[str] = None

    # Enriched identity
    manufacturer_name: FieldValue[str] = Field(default_factory=FieldValue)
    brand_name: FieldValue[str] = Field(default_factory=FieldValue)
    trade_name: FieldValue[str] = Field(default_factory=FieldValue)
    manufacturer_part_number: FieldValue[str] = Field(default_factory=FieldValue)
    alternate_part_number: FieldValue[str] = Field(default_factory=FieldValue)
    classpath: FieldValue[str] = Field(default_factory=FieldValue)
    mfr_url: FieldValue[str] = Field(default_factory=FieldValue)
    ref_urls: List[str] = Field(default_factory=list, description="Up to 5 supporting reference URLs")

    # Description formats
    mobile_desc: FieldValue[str] = Field(default_factory=FieldValue)
    invoice_desc: FieldValue[str] = Field(default_factory=FieldValue)
    short_desc: FieldValue[str] = Field(default_factory=FieldValue)
    long_desc1: FieldValue[str] = Field(default_factory=FieldValue)
    retail_desc: FieldValue[str] = Field(default_factory=FieldValue)
    marketing_description: FieldValue[str] = Field(default_factory=FieldValue)
    item_features: List[FeatureEntry] = Field(default_factory=list, description="Up to 20 feature entries")

    # Modifiers
    with_features: FieldValue[str] = Field(default_factory=FieldValue)
    standard_approvals: FieldValue[str] = Field(default_factory=FieldValue)
    prop_65: FieldValue[str] = Field(default_factory=FieldValue)
    application: FieldValue[str] = Field(default_factory=FieldValue)
    includes: FieldValue[str] = Field(default_factory=FieldValue)
    product_name: FieldValue[str] = Field(default_factory=FieldValue)

    # Attributes
    attributes: List[AttributeEntry] = Field(default_factory=list, description="Up to 50 attribute entries")

    # Identifiers
    upc: FieldValue[str] = Field(default_factory=FieldValue)
    ean: FieldValue[str] = Field(default_factory=FieldValue)
    gtin: FieldValue[str] = Field(default_factory=FieldValue)
    unspsc: FieldValue[str] = Field(default_factory=FieldValue)

    # Commercial
    warranty: FieldValue[str] = Field(default_factory=FieldValue)
    list_price: FieldValue[float] = Field(default_factory=FieldValue)
    selling_qty: FieldValue[str] = Field(default_factory=FieldValue)
    selling_uom: FieldValue[str] = Field(default_factory=FieldValue)
    standard_packaging_info: FieldValue[str] = Field(default_factory=FieldValue)

    # Dimensions
    length: FieldValue[float] = Field(default_factory=FieldValue)
    length_uom: FieldValue[str] = Field(default_factory=FieldValue)
    height: FieldValue[float] = Field(default_factory=FieldValue)
    height_uom: FieldValue[str] = Field(default_factory=FieldValue)
    width: FieldValue[float] = Field(default_factory=FieldValue)
    width_uom: FieldValue[str] = Field(default_factory=FieldValue)
    weight: FieldValue[float] = Field(default_factory=FieldValue)
    weight_uom: FieldValue[str] = Field(default_factory=FieldValue)
    volume: FieldValue[float] = Field(default_factory=FieldValue)
    volume_uom: FieldValue[str] = Field(default_factory=FieldValue)

    # Digital assets
    assets: List[AssetLink] = Field(default_factory=list)

    # Misc
    country_of_origin: FieldValue[str] = Field(default_factory=FieldValue)
    discontinued: FieldValue[str] = Field(default_factory=FieldValue)
    actual_image_yn: FieldValue[str] = Field(default_factory=FieldValue)

    # Pipeline metadata
    review_status: Literal["pending", "approved", "flagged"] = "pending"
    processed_at: Optional[str] = None
    fields_found_count: Optional[int] = None
    fields_total_count: Optional[int] = None

    # Diagnostic: per-URL direct HTTP fetch results and unresolved taxonomy tracking (not serialized to delivery format)
    content_diagnostics: Optional[List[dict]] = Field(default=None, exclude=True)
    unresolved_taxonomy_labels: Optional[List[str]] = Field(default=None, exclude=True)


DELIVERY_FORMAT_HEADERS: List[str] = [
    "MFR URL", "Ref URL 1", "Ref URL 2", "Ref URL 3", "Ref URL 4", "Ref URL 5",
    "PART_NUMBER", "Dept", "Class", "Fine", "SKU - MY_PART_NUMBER", "Mfg_Part_Num",
    "Part_Desc", "E1_Brand", "Unilog_Brand", "DIB_Brand", "Part_Manuf",
    "MANUFACTURER_NAME", "BRAND_NAME", "TRADE_NAME", "MANUFACTURER_PART_NUMBER",
    "ALTERNATE_PART_NUMBER", "Classpath", "MOBILE_DESC", "INVOICE_DESC",
    "SHORT_DESC", "LONG_DESC1", "RETAIL_DESC", "MARKETING_DESCRIPTION",
] + [f"ITEM_FEATURES_{i}" for i in range(1, 21)] + [
    "With", "Standard/Approvals", "Prop 65", "Application", "Includes", "Product Name",
]

for _i in range(1, 51):
    DELIVERY_FORMAT_HEADERS.extend([
        f"ATTRIBUTE_LABEL {_i}",
        f"ATTRIBUTE_VALUE {_i}",
        f"ATTRIBUTE_UOM {_i}"
    ])

DELIVERY_FORMAT_HEADERS.extend([
    "UPC", "EAN", "GTIN", "UNSPSC", "Warranty", "List Price", "Selling Qty",
    "Selling UOM", "Standard Packaging Information", "LENGTH", "LENGTH_UOM",
    "HEIGHT", "HEIGHT_UOM", "WIDTH", "WIDTH_UOM", "WEIGHT", "WEIGHT_UOM",
    "VOLUME", "VOLUME_UOM", "Product Image", "Alternate Image 1", "Alternate Image 2",
    "Alternate Image 3", "Alternate Image 4", "SDS", "SDS_1", "Warranty Information",
    "Catalog", "Specification Sheet", "Instruction/Installation Manual",
    "Service Manual", "Owners/User Manual", "Line Drawing", "MTR", "RoHS",
    "Full Engineering Drawing", "Energy Star Guide", "Technical Bulletin",
    "Submittal", "Compatibility Chart", "Size Chart", "Product Label/Insert",
    "Video Link", "Video Link 1", "Country Of Origin", "Discontinued",
    "Actual Image (Yes/No)"
])


def _get_val(field: Any) -> Any:
    if isinstance(field, FieldValue):
        return field.value if field.value is not None else ""
    return field if field is not None else ""


def to_delivery_format_row(record: ProductRecord) -> Dict[str, Any]:
    """
    Flattens a ProductRecord back into the exact 252-column flat dict shape
    matching the Unilog Delivery Format CSV headers.
    """
    row: Dict[str, Any] = {}

    # MFR URL & Ref URLs (up to 5)
    row["MFR URL"] = _get_val(record.mfr_url)
    ref_urls = record.ref_urls or []
    for i in range(1, 6):
        row[f"Ref URL {i}"] = ref_urls[i - 1] if (i - 1) < len(ref_urls) else ""

    # Identity passthrough (given raw input fields)
    row["PART_NUMBER"] = record.part_number or ""
    row["Dept"] = record.dept or ""
    row["Class"] = record.product_class or ""
    row["Fine"] = record.fine_class or ""
    row["SKU - MY_PART_NUMBER"] = record.sku or ""
    row["Mfg_Part_Num"] = record.mfg_part_num or ""
    row["Part_Desc"] = record.part_desc or ""
    row["E1_Brand"] = record.e1_brand or ""
    row["Unilog_Brand"] = record.unilog_brand or ""
    row["DIB_Brand"] = record.dib_brand or ""
    row["Part_Manuf"] = record.part_manuf or ""

    # Identity enriched
    row["MANUFACTURER_NAME"] = _get_val(record.manufacturer_name)
    row["BRAND_NAME"] = _get_val(record.brand_name)
    row["TRADE_NAME"] = _get_val(record.trade_name)
    row["MANUFACTURER_PART_NUMBER"] = _get_val(record.manufacturer_part_number)
    row["ALTERNATE_PART_NUMBER"] = _get_val(record.alternate_part_number)
    row["Classpath"] = _get_val(record.classpath)

    # Description formats
    row["MOBILE_DESC"] = _get_val(record.mobile_desc)
    row["INVOICE_DESC"] = _get_val(record.invoice_desc)
    row["SHORT_DESC"] = _get_val(record.short_desc)
    row["LONG_DESC1"] = _get_val(record.long_desc1)
    row["RETAIL_DESC"] = _get_val(record.retail_desc)
    row["MARKETING_DESCRIPTION"] = _get_val(record.marketing_description)

    # Item features (up to 20)
    features = record.item_features or []
    for i in range(1, 21):
        if (i - 1) < len(features):
            row[f"ITEM_FEATURES_{i}"] = _get_val(features[i - 1].text)
        else:
            row[f"ITEM_FEATURES_{i}"] = ""

    # Modifiers
    row["With"] = _get_val(record.with_features)
    row["Standard/Approvals"] = _get_val(record.standard_approvals)
    row["Prop 65"] = _get_val(record.prop_65)
    row["Application"] = _get_val(record.application)
    row["Includes"] = _get_val(record.includes)
    row["Product Name"] = _get_val(record.product_name)

    # Attributes (up to 50 slots)
    attrs = record.attributes or []
    for i in range(1, 51):
        if (i - 1) < len(attrs):
            entry = attrs[i - 1]
            row[f"ATTRIBUTE_LABEL {i}"] = _get_val(entry.label)
            row[f"ATTRIBUTE_VALUE {i}"] = _get_val(entry.value)
            row[f"ATTRIBUTE_UOM {i}"] = _get_val(entry.uom)
        else:
            row[f"ATTRIBUTE_LABEL {i}"] = ""
            row[f"ATTRIBUTE_VALUE {i}"] = ""
            row[f"ATTRIBUTE_UOM {i}"] = ""

    # Identifiers
    row["UPC"] = _get_val(record.upc)
    row["EAN"] = _get_val(record.ean)
    row["GTIN"] = _get_val(record.gtin)
    row["UNSPSC"] = _get_val(record.unspsc)

    # Commercial
    row["Warranty"] = _get_val(record.warranty)
    row["List Price"] = _get_val(record.list_price)
    row["Selling Qty"] = _get_val(record.selling_qty)
    row["Selling UOM"] = _get_val(record.selling_uom)
    row["Standard Packaging Information"] = _get_val(record.standard_packaging_info)

    # Dimensions
    row["LENGTH"] = _get_val(record.length)
    row["LENGTH_UOM"] = _get_val(record.length_uom)
    row["HEIGHT"] = _get_val(record.height)
    row["HEIGHT_UOM"] = _get_val(record.height_uom)
    row["WIDTH"] = _get_val(record.width)
    row["WIDTH_UOM"] = _get_val(record.width_uom)
    row["WEIGHT"] = _get_val(record.weight)
    row["WEIGHT_UOM"] = _get_val(record.weight_uom)
    row["VOLUME"] = _get_val(record.volume)
    row["VOLUME_UOM"] = _get_val(record.volume_uom)

    # Assets (25 specific columns)
    asset_cols = [
        "Product Image", "Alternate Image 1", "Alternate Image 2", "Alternate Image 3",
        "Alternate Image 4", "SDS", "SDS_1", "Warranty Information", "Catalog",
        "Specification Sheet", "Instruction/Installation Manual", "Service Manual",
        "Owners/User Manual", "Line Drawing", "MTR", "RoHS", "Full Engineering Drawing",
        "Energy Star Guide", "Technical Bulletin", "Submittal", "Compatibility Chart",
        "Size Chart", "Product Label/Insert", "Video Link", "Video Link 1"
    ]
    
    asset_map: Dict[str, str] = {}
    for asset in (record.assets or []):
        if asset.asset_type:
            raw_type = asset.asset_type.strip()
            val = _get_val(asset.url)
            asset_map[raw_type] = val
            asset_map[raw_type.lower()] = val
            asset_map[raw_type.lower().replace("_", " ")] = val
            asset_map[raw_type.lower().replace(" ", "_")] = val

    for col in asset_cols:
        col_norm = col.lower()
        col_space = col_norm.replace("_", " ")
        col_under = col_norm.replace(" ", "_")
        row[col] = (
            asset_map.get(col) or
            asset_map.get(col_norm) or
            asset_map.get(col_space) or
            asset_map.get(col_under) or
            ""
        )

    # Misc
    row["Country Of Origin"] = _get_val(record.country_of_origin)
    row["Discontinued"] = _get_val(record.discontinued)
    row["Actual Image (Yes/No)"] = _get_val(record.actual_image_yn)

    return row
