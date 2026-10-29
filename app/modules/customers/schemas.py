from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CustomerAddressFields(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    recipient_name: str = Field(min_length=1, max_length=160)
    recipient_phone: str = Field(min_length=7, max_length=32)
    address_line1: str = Field(min_length=3, max_length=250)
    address_line2: str | None = Field(default=None, max_length=250)
    city: str = Field(min_length=1, max_length=120)
    state: str = Field(min_length=1, max_length=120)
    postal_code: str | None = Field(default=None, max_length=24)
    country_code: str = Field(default="NG", min_length=2, max_length=2, pattern="^[A-Z]{2}$")
    delivery_instructions: str | None = Field(default=None, max_length=1000)


class CustomerAddressCreate(CustomerAddressFields):
    is_default: bool = False


class CustomerAddressUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=60)
    recipient_name: str | None = Field(default=None, min_length=1, max_length=160)
    recipient_phone: str | None = Field(default=None, min_length=7, max_length=32)
    address_line1: str | None = Field(default=None, min_length=3, max_length=250)
    address_line2: str | None = Field(default=None, max_length=250)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    state: str | None = Field(default=None, min_length=1, max_length=120)
    postal_code: str | None = Field(default=None, max_length=24)
    country_code: str | None = Field(default=None, min_length=2, max_length=2, pattern="^[A-Z]{2}$")
    delivery_instructions: str | None = Field(default=None, max_length=1000)
    is_default: bool | None = None


class CustomerAddressResponse(CustomerAddressFields):
    model_config = ConfigDict(from_attributes=True)
    id: str
    is_default: bool
    created_at: datetime
    updated_at: datetime


class CustomerDashboardResponse(BaseModel):
    order_count: int
    orders_by_status: dict[str, int]
    saved_address_count: int
