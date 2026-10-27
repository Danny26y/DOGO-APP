from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ShipmentCreate(BaseModel):
    organization_id: str
    quote_id: str
    origin_zone: str = Field(min_length=1, max_length=120)
    destination_zone: str = Field(min_length=1, max_length=120)
    delivery_tier: str = Field(min_length=1, max_length=40)
    package_weight_kg: Decimal = Field(gt=0, le=250, max_digits=8, decimal_places=3)
    pickup_address: str = Field(min_length=5, max_length=500)
    destination_address: str = Field(min_length=5, max_length=500)
    recipient_name: str = Field(min_length=1, max_length=160)
    recipient_phone: str = Field(min_length=7, max_length=32)
    package_category: str = Field(pattern="^(documents|food|parcel|electronics)$")


class ShipmentEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: str
    note: str | None
    created_at: datetime


class ShipmentResponse(BaseModel):
    id: str
    tracking_number: str
    waybill_number: str
    qr_verification_code: str
    status: str
    amount_minor: int
    currency: str
    created_at: datetime
    events: list[ShipmentEventResponse] = Field(default_factory=list)


class ShipmentStatusUpdate(BaseModel):
    status: str = Field(pattern="^(pickup_scheduled|picked_up|in_transit|out_for_delivery|delivered|exception|cancelled)$")
    note: str | None = Field(default=None, max_length=500)
    proof_method: str | None = Field(default=None, pattern="^(otp|photo|signature)$")
    proof_reference: str | None = Field(default=None, max_length=500)


class PublicTrackingResponse(BaseModel):
    tracking_number: str
    status: str
    timeline: list[ShipmentEventResponse]
