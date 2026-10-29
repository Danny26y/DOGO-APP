from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CartItemInput(BaseModel):
    product_id: str
    quantity: int = Field(ge=1, le=1000)


class CartItemResponse(BaseModel):
    product_id: str
    product_title: str
    quantity: int
    unit_price_minor: int
    currency: str
    available_stock: int


class CartResponse(BaseModel):
    items: list[CartItemResponse]


class CreateOrderRequest(BaseModel):
    delivery_address_id: str


class DeliveryAddressSnapshot(BaseModel):
    label: str
    recipient_name: str
    recipient_phone: str
    address_line1: str
    address_line2: str | None
    city: str
    state: str
    postal_code: str | None
    country_code: str
    delivery_instructions: str | None


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: str
    merchant_organization_id: str
    product_title: str
    quantity: int
    unit_price_minor: int
    currency: str
    line_total_minor: int


class OrderResponse(BaseModel):
    id: str
    status: str
    payment_status: str
    currency: str
    subtotal_minor: int
    delivery_address_id: str | None
    delivery_address_snapshot: DeliveryAddressSnapshot | None
    created_at: datetime
    items: list[OrderItemResponse]


class MerchantOrderResponse(BaseModel):
    id: str
    status: str
    payment_status: str
    currency: str
    merchant_subtotal_minor: int
    created_at: datetime
    items: list[OrderItemResponse]
