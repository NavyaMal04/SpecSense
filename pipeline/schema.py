from typing import Optional, List, Literal, Generic, TypeVar
from pydantic import BaseModel, Field

# Source provenance type definition
SourceType = Literal["extracted", "inferred", "flagged"]

T = TypeVar("T")


class AttributeField(BaseModel, Generic[T]):
    """
    Sub-model representing a product attribute field with provenance metadata.
    """
    value: Optional[T] = Field(
        default=None,
        description="The actual data value (None if unknown)"
    )
    source_type: SourceType = Field(
        default="extracted",
        description="Data provenance type: 'extracted', 'inferred', or 'flagged'"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score ranging from 0.0 (low) to 1.0 (high)"
    )
    source_location: Optional[str] = Field(
        default=None,
        description="Citation reference (e.g. 'Page 1, Line 12'). Used primarily when source_type is 'extracted'."
    )


class CommerceCopyField(BaseModel, Generic[T]):
    """
    Sub-model for generated buyer-facing commerce content.
    Does not require a source_location citation.
    """
    value: Optional[T] = Field(
        default=None,
        description="Generated content value"
    )
    source_type: SourceType = Field(
        default="extracted",
        description="Data provenance type: 'extracted', 'inferred', or 'flagged'"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score ranging from 0.0 to 1.0"
    )


class FAQItem(BaseModel):
    """
    Represents a single Question & Answer pair for commerce FAQ content.
    """
    question: str = Field(description="Buyer question")
    answer: str = Field(description="Grounded answer based on product specs")


class ProductRecord(BaseModel):
    """
    Structured Product Record model for SpecSense intelligence pipeline.
    Combines extracted spec sheet attributes and generated commerce copy.
    """
    # Metadata & Tracking
    id: Optional[str] = Field(default=None, description="Firestore document ID or unique identifier")
    source_file: Optional[str] = Field(default=None, description="Source PDF filename")
    review_status: Literal["pending", "approved", "flagged"] = Field(
        default="pending",
        description="Human-in-the-loop review status"
    )
    raw_extracted_text: Optional[str] = Field(
        default=None,
        description="Full raw text extracted from PDF before LLM processing"
    )
    processed_at: Optional[str] = Field(
        default=None,
        description="Timestamp string for when this record was processed"
    )

    # Core Specification Attributes
    name: AttributeField[str] = Field(default_factory=AttributeField, description="Product Name")
    category: AttributeField[str] = Field(default_factory=AttributeField, description="Product Category")
    dimensions: AttributeField[str] = Field(default_factory=AttributeField, description="Dimensions (L x W x H)")
    material: AttributeField[str] = Field(default_factory=AttributeField, description="Material Composition")
    voltage: AttributeField[str] = Field(default_factory=AttributeField, description="Voltage / Electrical Specs")
    certifications: AttributeField[List[str]] = Field(default_factory=AttributeField, description="Certifications & Safety Standards")
    weight: AttributeField[str] = Field(default_factory=AttributeField, description="Product Weight")
    price: AttributeField[float] = Field(default_factory=AttributeField, description="Product Price")

    # Category-Specific / Flexible Additional Attributes
    additional_attributes: List[AttributeField[str]] = Field(
        default_factory=list,
        description="Category-specific attributes that don't fit the fixed schema fields (e.g. hazard_class for chemicals, size_range for safety equipment). Each entry's 'value' field should be a string in the format 'attribute_name: attribute_value' so it's self-describing."
    )

    # Generated Commerce Copy (Grounded in verified attributes)
    title: CommerceCopyField[str] = Field(default_factory=CommerceCopyField, description="Commerce Title")
    short_description: CommerceCopyField[str] = Field(default_factory=CommerceCopyField, description="Short Description")
    feature_bullets: CommerceCopyField[List[str]] = Field(default_factory=CommerceCopyField, description="Feature Bullet Points")
    faq: CommerceCopyField[List[FAQItem]] = Field(default_factory=CommerceCopyField, description="FAQ List of Q&A Pairs")
