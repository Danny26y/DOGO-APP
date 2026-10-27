from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PricingRuleCreate(BaseModel):
    origin_zone: str = Field(min_length=1, max_length=120)
    destination_zone: str = Field(min_length=1, max_length=120)
    delivery_tier: str = Field(min_length=1, max_length=40)
    currency: str = Field(default="NGN", pattern="^[A-Z]{3}$")
    base_fare_minor: int = Field(ge=0)
    per_kg_minor: int = Field(default=0, ge=0)


class PricingRuleResponse(PricingRuleCreate):
    id: str
    enabled: bool


class QuoteRequest(BaseModel):
    origin_zone: str = Field(min_length=1, max_length=120)
    destination_zone: str = Field(min_length=1, max_length=120)
    delivery_tier: str = Field(min_length=1, max_length=40)
    package_weight_kg: Decimal = Field(gt=0, le=250, max_digits=8, decimal_places=3)


class QuoteResponse(BaseModel):
    quote_id: str
    origin_zone: str
    destination_zone: str
    delivery_tier: str
    package_weight_kg: Decimal
    amount_minor: int
    currency: str
    expires_at: datetime
