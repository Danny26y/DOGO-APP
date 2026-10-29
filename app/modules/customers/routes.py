from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.modules.audit.service import record_audit
from app.modules.auth.models import User
from app.modules.customers.models import CustomerAddress
from app.modules.customers.schemas import (
    CustomerAddressCreate,
    CustomerAddressResponse,
    CustomerAddressUpdate,
    CustomerDashboardResponse,
)
from app.modules.orders.models import Order

router = APIRouter()


@router.get("/customers/me/addresses", response_model=list[CustomerAddressResponse])
def list_addresses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(CustomerAddress).where(CustomerAddress.user_id == user.id).order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at.desc())))


@router.post("/customers/me/addresses", response_model=CustomerAddressResponse, status_code=201)
def create_address(payload: CustomerAddressCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.scalar(select(User.id).where(User.id == user.id).with_for_update())
    has_addresses = db.scalar(select(CustomerAddress.id).where(CustomerAddress.user_id == user.id).limit(1)) is not None
    make_default = payload.is_default or not has_addresses
    if make_default:
        db.query(CustomerAddress).filter(CustomerAddress.user_id == user.id, CustomerAddress.is_default.is_(True)).update({CustomerAddress.is_default: False}, synchronize_session=False)
    address = CustomerAddress(user_id=user.id, **payload.model_dump(exclude={"is_default"}), is_default=make_default)
    db.add(address)
    db.flush()
    record_audit(db, actor_user_id=user.id, action="customer.address_created", resource_type="customer_address", resource_id=address.id)
    db.commit()
    db.refresh(address)
    return address


@router.patch("/customers/me/addresses/{address_id}", response_model=CustomerAddressResponse)
def update_address(address_id: str, payload: CustomerAddressUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.scalar(select(User.id).where(User.id == user.id).with_for_update())
    address = db.scalar(select(CustomerAddress).where(CustomerAddress.id == address_id, CustomerAddress.user_id == user.id).with_for_update())
    if address is None:
        raise HTTPException(status_code=404, detail="Address not found")
    changes = payload.model_dump(exclude_unset=True)
    if any(value is None for key, value in changes.items() if key not in {"address_line2", "postal_code", "delivery_instructions"}):
        raise HTTPException(status_code=422, detail="Required address fields cannot be null")
    if changes.get("is_default") is True:
        db.query(CustomerAddress).filter(CustomerAddress.user_id == user.id, CustomerAddress.id != address.id, CustomerAddress.is_default.is_(True)).update({CustomerAddress.is_default: False}, synchronize_session=False)
    for key, value in changes.items():
        setattr(address, key, value)
    record_audit(db, actor_user_id=user.id, action="customer.address_updated", resource_type="customer_address", resource_id=address.id, details={"fields": sorted(changes)})
    db.commit()
    db.refresh(address)
    return address


@router.delete("/customers/me/addresses/{address_id}", status_code=204)
def delete_address(address_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.scalar(select(User.id).where(User.id == user.id).with_for_update())
    address = db.scalar(select(CustomerAddress).where(CustomerAddress.id == address_id, CustomerAddress.user_id == user.id).with_for_update())
    if address is None:
        raise HTTPException(status_code=404, detail="Address not found")
    was_default = address.is_default
    db.delete(address)
    db.flush()
    if was_default:
        replacement = db.scalar(select(CustomerAddress).where(CustomerAddress.user_id == user.id).order_by(CustomerAddress.created_at.desc()).limit(1))
        if replacement is not None:
            replacement.is_default = True
    record_audit(db, actor_user_id=user.id, action="customer.address_deleted", resource_type="customer_address", resource_id=address_id)
    db.commit()


@router.get("/customers/me/dashboard", response_model=CustomerDashboardResponse)
def customer_dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Order.status, func.count(Order.id)).where(Order.customer_user_id == user.id).group_by(Order.status)).all()
    status_counts = {status: count for status, count in rows}
    address_count = db.scalar(select(func.count(CustomerAddress.id)).where(CustomerAddress.user_id == user.id)) or 0
    return CustomerDashboardResponse(order_count=sum(status_counts.values()), orders_by_status=status_counts, saved_address_count=address_count)
