from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.modules.auth.models import Organization, User
from app.modules.marketplace.models import Product
from app.modules.orders.models import Order
from app.modules.shipments.models import Shipment

router = APIRouter()


class PlatformDashboardResponse(BaseModel):
    user_count: int
    organization_count: int
    product_count: int
    unpublished_product_count: int
    order_count: int
    orders_by_status: dict[str, int]
    shipment_count: int
    shipments_by_status: dict[str, int]


def grouped_counts(db: Session, model, field, *filters) -> dict[str, int]:
    rows = db.execute(select(field, func.count(model.id)).where(*filters).group_by(field)).all()
    return {key: count for key, count in rows}


@router.get("/admin/dashboard/summary", response_model=PlatformDashboardResponse)
def platform_dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.email.lower() not in get_settings().platform_admin_email_set:
        raise HTTPException(status_code=403, detail="Platform administrator access is required")
    return PlatformDashboardResponse(
        user_count=db.scalar(select(func.count(User.id))) or 0,
        organization_count=db.scalar(select(func.count(Organization.id))) or 0,
        product_count=db.scalar(select(func.count(Product.id))) or 0,
        unpublished_product_count=db.scalar(select(func.count(Product.id)).where(Product.published.is_(False))) or 0,
        order_count=db.scalar(select(func.count(Order.id))) or 0,
        orders_by_status=grouped_counts(db, Order, Order.status),
        shipment_count=db.scalar(select(func.count(Shipment.id))) or 0,
        shipments_by_status=grouped_counts(db, Shipment, Shipment.status),
    )
