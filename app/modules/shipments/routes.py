import csv
import io
import secrets
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.modules.audit.service import record_audit
from app.modules.auth.models import OrganizationMembership, User
from app.modules.pricing.models import PricingQuote
from app.modules.shipments.models import Shipment, ShipmentEvent
from app.modules.shipments.schemas import (
    PublicTrackingResponse,
    ShipmentCreate,
    ShipmentResponse,
    ShipmentStatusUpdate,
)

router = APIRouter()
TRANSITIONS = {
    "requested": {"pickup_scheduled", "cancelled", "exception"},
    "pickup_scheduled": {"picked_up", "cancelled", "exception"},
    "picked_up": {"in_transit", "exception"},
    "in_transit": {"out_for_delivery", "exception"},
    "out_for_delivery": {"delivered", "exception"},
    "exception": {"in_transit", "cancelled"},
    "delivered": set(),
    "cancelled": set(),
}


def is_platform_admin(user: User) -> bool:
    return user.email.lower() in get_settings().platform_admin_email_set


def require_membership(db: Session, user_id: str, organization_id: str) -> bool:
    return db.scalar(select(OrganizationMembership.id).where(OrganizationMembership.user_id == user_id, OrganizationMembership.organization_id == organization_id)) is not None


def create_from_quote(data: ShipmentCreate, user: User, db: Session) -> Shipment:
    if not require_membership(db, user.id, data.organization_id):
        raise HTTPException(status_code=404, detail="Organization not found")
    quote = db.scalar(select(PricingQuote).where(PricingQuote.id == data.quote_id).with_for_update())
    if quote is None:
        raise HTTPException(status_code=409, detail="Pricing quote is unavailable or expired")
    expires_at = quote.expires_at if quote.expires_at.tzinfo else quote.expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=409, detail="Pricing quote is unavailable or expired")
    if (
        quote.origin_zone != data.origin_zone
        or quote.destination_zone != data.destination_zone
        or quote.delivery_tier != data.delivery_tier
        or quote.package_weight_kg != data.package_weight_kg
    ):
        raise HTTPException(status_code=409, detail="Shipment details do not match the selected pricing quote")
    shipment = Shipment(
        organization_id=data.organization_id,
        quote_id=quote.id,
        tracking_number=f"DGO-{secrets.token_urlsafe(18).replace('-', '').replace('_', '').upper()}",
        waybill_number=f"WB-{uuid4().hex[:16].upper()}",
        qr_verification_code=secrets.token_urlsafe(24),
        origin_zone=quote.origin_zone,
        destination_zone=quote.destination_zone,
        delivery_tier=quote.delivery_tier,
        package_weight_kg=quote.package_weight_kg,
        pickup_address=data.pickup_address,
        destination_address=data.destination_address,
        recipient_name=data.recipient_name,
        recipient_phone=data.recipient_phone,
        package_category=data.package_category,
        status="requested",
        amount_minor=quote.amount_minor,
        currency=quote.currency,
    )
    try:
        db.add(shipment)
        db.flush()
        db.add(ShipmentEvent(shipment_id=shipment.id, status="requested", created_by_user_id=user.id))
        record_audit(db, actor_user_id=user.id, action="shipment.created", resource_type="shipment", resource_id=shipment.id, organization_id=shipment.organization_id, details={"status": shipment.status, "amount_minor": shipment.amount_minor, "currency": shipment.currency})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Pricing quote has already been used")
    return db.scalar(select(Shipment).options(selectinload(Shipment.events)).where(Shipment.id == shipment.id))


@router.post("/shipments", response_model=ShipmentResponse, status_code=201)
def create_shipment(payload: ShipmentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return create_from_quote(payload, user, db)


@router.get("/shipments", response_model=list[ShipmentResponse])
def list_shipments(organization_id: str | None = None, limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(Shipment).options(selectinload(Shipment.events)).order_by(Shipment.created_at.desc())
    if organization_id is None:
        if not is_platform_admin(user):
            raise HTTPException(status_code=422, detail="organization_id is required")
    else:
        if not require_membership(db, user.id, organization_id) and not is_platform_admin(user):
            raise HTTPException(status_code=404, detail="Organization not found")
        query = query.where(Shipment.organization_id == organization_id)
    return list(db.scalars(query.offset(offset).limit(limit)))


@router.get("/shipments/{shipment_id}", response_model=ShipmentResponse)
def get_shipment(shipment_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(Shipment).options(selectinload(Shipment.events)).where(Shipment.id == shipment_id)
    if not is_platform_admin(user):
        query = query.join(OrganizationMembership, OrganizationMembership.organization_id == Shipment.organization_id).where(OrganizationMembership.user_id == user.id)
    shipment = db.scalar(query)
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment


@router.get("/tracking/{tracking_number}", response_model=PublicTrackingResponse)
def public_tracking(tracking_number: str, db: Session = Depends(get_db)):
    shipment = db.scalar(select(Shipment).options(selectinload(Shipment.events)).where(Shipment.tracking_number == tracking_number))
    if shipment is None:
        raise HTTPException(status_code=404, detail="Tracking number not found")
    timeline = [{"status": event.status, "note": None, "created_at": event.created_at} for event in shipment.events]
    return PublicTrackingResponse(tracking_number=shipment.tracking_number, status=shipment.status, timeline=timeline)


@router.get("/waybills/verify/{verification_code}")
def verify_waybill(verification_code: str, db: Session = Depends(get_db)):
    shipment = db.scalar(select(Shipment).where(Shipment.qr_verification_code == verification_code))
    if shipment is None:
        raise HTTPException(status_code=404, detail="Waybill verification code is invalid")
    return {"valid": True, "waybill_number": shipment.waybill_number, "tracking_number": shipment.tracking_number, "status": shipment.status}


@router.patch("/shipments/{shipment_id}/status", response_model=ShipmentResponse)
def update_status(shipment_id: str, payload: ShipmentStatusUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not is_platform_admin(user):
        raise HTTPException(status_code=403, detail="Platform operations access is required")
    shipment = db.scalar(select(Shipment).options(selectinload(Shipment.events)).where(Shipment.id == shipment_id).with_for_update())
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if payload.status not in TRANSITIONS[shipment.status]:
        raise HTTPException(status_code=409, detail="Shipment status transition is not allowed")
    if payload.status == "delivered" and (not payload.proof_method or not payload.proof_reference):
        raise HTTPException(status_code=422, detail="Proof method and reference are required for delivery completion")
    shipment.status = payload.status
    event = ShipmentEvent(shipment_id=shipment.id, status=payload.status, note=payload.note, proof_method=payload.proof_method, proof_reference=payload.proof_reference, created_by_user_id=user.id)
    db.add(event)
    record_audit(db, actor_user_id=user.id, action="shipment.status_changed", resource_type="shipment", resource_id=shipment.id, organization_id=shipment.organization_id, details={"status": payload.status, "proof_method": payload.proof_method})
    db.commit()
    db.refresh(shipment)
    return db.scalar(select(Shipment).options(selectinload(Shipment.events)).where(Shipment.id == shipment.id))


@router.post("/shipments/bulk", status_code=200)
def bulk_shipments(organization_id: str, csv_text: str = Body(media_type="text/csv"), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not require_membership(db, user.id, organization_id):
        raise HTTPException(status_code=404, detail="Organization not found")
    if len(csv_text.encode("utf-8")) > 2_000_000:
        raise HTTPException(status_code=413, detail="CSV content exceeds the 2 MB request limit")
    reader = csv.DictReader(io.StringIO(csv_text))
    required = {"quote_id", "pickup_address", "destination_address", "recipient_name", "recipient_phone", "package_category"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise HTTPException(status_code=422, detail=f"CSV must include columns: {', '.join(sorted(required))}")
    rows = list(reader)
    if len(rows) > 500:
        raise HTTPException(status_code=413, detail="CSV may contain at most 500 shipment rows")
    results = []
    for index, row in enumerate(rows, start=2):
        try:
            payload = ShipmentCreate(organization_id=organization_id, **row)
            shipment = create_from_quote(payload, user, db)
            results.append({"row": index, "status": "created", "shipment_id": shipment.id, "tracking_number": shipment.tracking_number})
        except HTTPException as exc:
            db.rollback()
            results.append({"row": index, "status": "failed", "code": "ROW_INVALID", "message": exc.detail})
        except ValidationError:
            db.rollback()
            results.append({"row": index, "status": "failed", "code": "ROW_INVALID", "message": "The row could not be processed"})
    return {"total_rows": len(rows), "created": sum(item["status"] == "created" for item in results), "failed": sum(item["status"] == "failed" for item in results), "results": results}
