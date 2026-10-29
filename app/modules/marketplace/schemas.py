from datetime import datetime
from decimal import Decimal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, EmailStr, Field, field_validator


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    slug: str
    name: str


class ProductCreate(BaseModel):
    organization_id: str
    category_id: str
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=5000)
    price_minor: int = Field(gt=0)
    currency: str = Field(default="NGN", pattern="^[A-Z]{3}$")
    weight_kg: Decimal | None = Field(default=None, gt=0, le=250, max_digits=8, decimal_places=3)
    length_cm: Decimal | None = Field(default=None, gt=0, le=1000, max_digits=8, decimal_places=2)
    width_cm: Decimal | None = Field(default=None, gt=0, le=1000, max_digits=8, decimal_places=2)
    height_cm: Decimal | None = Field(default=None, gt=0, le=1000, max_digits=8, decimal_places=2)
    initial_stock: int = Field(default=0, ge=0, le=1_000_000)


class ProductUpdate(BaseModel):
    category_id: str | None = None
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    price_minor: int | None = Field(default=None, gt=0)
    weight_kg: Decimal | None = Field(default=None, gt=0, le=250, max_digits=8, decimal_places=3)
    length_cm: Decimal | None = Field(default=None, gt=0, le=1000, max_digits=8, decimal_places=2)
    width_cm: Decimal | None = Field(default=None, gt=0, le=1000, max_digits=8, decimal_places=2)
    height_cm: Decimal | None = Field(default=None, gt=0, le=1000, max_digits=8, decimal_places=2)


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    category_id: str
    title: str
    description: str
    price_minor: int
    currency: str
    weight_kg: Decimal | None
    length_cm: Decimal | None
    width_cm: Decimal | None
    height_cm: Decimal | None
    stock_quantity: int
    published: bool
    created_at: datetime


class StoreProfileUpsert(BaseModel):
    storefront_slug: str = Field(min_length=3, max_length=80, pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str = Field(default="", max_length=3000)
    support_email: EmailStr | None = None
    support_phone: str | None = Field(default=None, min_length=7, max_length=32)
    website_url: AnyHttpUrl | None = None
    logo_url: AnyHttpUrl | None = None


class StoreProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    organization_id: str
    storefront_slug: str
    description: str
    support_email: EmailStr | None
    support_phone: str | None
    website_url: AnyHttpUrl | None
    logo_url: AnyHttpUrl | None
    updated_at: datetime


class PublicStorefrontResponse(BaseModel):
    organization_name: str
    storefront_slug: str
    description: str
    support_email: EmailStr | None
    support_phone: str | None
    website_url: AnyHttpUrl | None
    logo_url: AnyHttpUrl | None
    products: list[ProductResponse]


class MerchantDashboardResponse(BaseModel):
    product_count: int
    published_product_count: int
    out_of_stock_product_count: int
    order_count: int
    orders_by_status: dict[str, int]


class InventoryAdjustment(BaseModel):
    quantity_delta: int = Field(ge=-1_000_000, le=1_000_000)
    reason: str = Field(min_length=3, max_length=200)

    @field_validator("quantity_delta")
    @classmethod
    def require_nonzero_delta(cls, value: int) -> int:
        if value == 0:
            raise ValueError("quantity_delta must not be zero")
        return value


class InventoryMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    product_id: str
    quantity_delta: int
    reason: str
    created_at: datetime
