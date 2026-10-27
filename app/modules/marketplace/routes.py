from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.modules.audit.service import record_audit
from app.modules.auth.models import OrganizationMembership, User
from app.modules.marketplace.models import InventoryMovement, Product, ProductCategory
from app.modules.marketplace.schemas import (
    CategoryResponse,
    InventoryAdjustment,
    InventoryMovementResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)

router = APIRouter()


def require_product_owner(db: Session, user_id: str, organization_id: str) -> None:
    membership = db.scalar(select(OrganizationMembership.role).where(OrganizationMembership.user_id == user_id, OrganizationMembership.organization_id == organization_id))
    if membership not in {"owner", "admin", "merchant_staff"}:
        raise HTTPException(status_code=404, detail="Merchant organization not found")


@router.get("/marketplace/categories", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return list(db.scalars(select(ProductCategory).order_by(ProductCategory.name)))


@router.get("/marketplace/products", response_model=list[ProductResponse])
def list_products(
    search: str | None = Query(default=None, max_length=120),
    category_id: str | None = None,
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = select(Product).where(Product.published.is_(True), Product.stock_quantity > 0).order_by(Product.created_at.desc())
    if search:
        query = query.where(Product.title.ilike(f"%{search}%"))
    if category_id:
        query = query.where(Product.category_id == category_id)
    return list(db.scalars(query.offset(offset).limit(limit)))


@router.get("/merchant/products", response_model=list[ProductResponse])
def list_merchant_products(
    organization_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_product_owner(db, user.id, organization_id)
    return list(db.scalars(select(Product).where(Product.organization_id == organization_id).order_by(Product.created_at.desc()).offset(offset).limit(limit)))


@router.post("/merchant/products", response_model=ProductResponse, status_code=201)
def create_product(payload: ProductCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_product_owner(db, user.id, payload.organization_id)
    if db.get(ProductCategory, payload.category_id) is None:
        raise HTTPException(status_code=422, detail="Unknown product category")
    data = payload.model_dump(exclude={"initial_stock"})
    product = Product(**data, stock_quantity=payload.initial_stock)
    db.add(product)
    if payload.initial_stock:
        db.flush()
        db.add(InventoryMovement(organization_id=payload.organization_id, product_id=product.id, quantity_delta=payload.initial_stock, reason="Initial stock", created_by_user_id=user.id))
    db.flush()
    record_audit(db, actor_user_id=user.id, action="product.created", resource_type="product", resource_id=product.id, organization_id=payload.organization_id, details={"initial_stock": payload.initial_stock})
    db.commit()
    db.refresh(product)
    return product


@router.patch("/merchant/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: str, payload: ProductUpdate, organization_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_product_owner(db, user.id, organization_id)
    product = db.scalar(select(Product).where(Product.id == product_id, Product.organization_id == organization_id).with_for_update())
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    data = payload.model_dump(exclude_unset=True)
    if any(value is None for value in data.values()):
        raise HTTPException(status_code=422, detail="Product fields cannot be null")
    if "category_id" in data and db.get(ProductCategory, data["category_id"]) is None:
        raise HTTPException(status_code=422, detail="Unknown product category")
    for key, value in data.items():
        setattr(product, key, value)
    record_audit(db, actor_user_id=user.id, action="product.updated", resource_type="product", resource_id=product.id, organization_id=organization_id, details={"fields": sorted(data)})
    db.commit()
    db.refresh(product)
    return product


@router.post("/merchant/products/{product_id}/inventory", response_model=InventoryMovementResponse, status_code=201)
def adjust_inventory(product_id: str, payload: InventoryAdjustment, organization_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_product_owner(db, user.id, organization_id)
    statement = (
        update(Product)
        .where(Product.id == product_id, Product.organization_id == organization_id, Product.stock_quantity + payload.quantity_delta >= 0)
        .values(stock_quantity=Product.stock_quantity + payload.quantity_delta)
    )
    result = db.execute(statement)
    if result.rowcount != 1:
        db.rollback()
        exists = db.scalar(select(Product.id).where(Product.id == product_id, Product.organization_id == organization_id))
        if exists is None:
            raise HTTPException(status_code=404, detail="Product not found")
        raise HTTPException(status_code=409, detail="Inventory adjustment would make stock negative")
    movement = InventoryMovement(organization_id=organization_id, product_id=product_id, quantity_delta=payload.quantity_delta, reason=payload.reason, created_by_user_id=user.id)
    db.add(movement)
    record_audit(db, actor_user_id=user.id, action="inventory.adjusted", resource_type="product", resource_id=product_id, organization_id=organization_id, details={"quantity_delta": payload.quantity_delta})
    db.commit()
    db.refresh(movement)
    return movement


@router.post("/merchant/products/{product_id}/publish", response_model=ProductResponse)
def publish_product(product_id: str, organization_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.email.lower() not in get_settings().platform_admin_email_set:
        raise HTTPException(status_code=403, detail="Platform administrator access is required")
    product = db.scalar(select(Product).where(Product.id == product_id, Product.organization_id == organization_id).with_for_update())
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    product.published = True
    record_audit(db, actor_user_id=user.id, action="product.published", resource_type="product", resource_id=product.id, organization_id=organization_id)
    db.commit()
    db.refresh(product)
    return product
