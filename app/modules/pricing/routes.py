from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.modules.audit.service import record_audit
from app.modules.auth.models import User
from app.modules.pricing.models import PricingQuote, PricingRule
from app.modules.pricing.schemas import (
    PricingRuleCreate,
    PricingRuleResponse,
    QuoteRequest,
    QuoteResponse,
)

router = APIRouter()


def require_platform_admin(user: User = Depends(get_current_user)) -> User:
    if user.email.lower() not in get_settings().platform_admin_email_set:
        raise HTTPException(status_code=403, detail="Platform administrator access is required")
    return user


@router.post("/rules", response_model=PricingRuleResponse, status_code=201)
def create_rule(payload: PricingRuleCreate, user: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    rule = PricingRule(**payload.model_dump(), created_by_user_id=user.id)
    db.add(rule)
    try:
        db.flush()
        record_audit(db, actor_user_id=user.id, action="pricing.rule_created", resource_type="pricing_rule", resource_id=rule.id, details={"origin_zone": rule.origin_zone, "destination_zone": rule.destination_zone, "tier": rule.delivery_tier})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A rule already exists for this zone pair and tier")
    db.refresh(rule)
    return rule


@router.get("/rules", response_model=list[PricingRuleResponse])
def list_rules(_: User = Depends(require_platform_admin), db: Session = Depends(get_db)):
    return list(db.scalars(select(PricingRule).order_by(PricingRule.origin_zone, PricingRule.destination_zone, PricingRule.delivery_tier)))


@router.post("/quotes", response_model=QuoteResponse, status_code=201)
def quote(payload: QuoteRequest, db: Session = Depends(get_db)):
    rule = db.scalar(select(PricingRule).where(
        PricingRule.origin_zone == payload.origin_zone,
        PricingRule.destination_zone == payload.destination_zone,
        PricingRule.delivery_tier == payload.delivery_tier,
        PricingRule.enabled.is_(True),
    ))
    if rule is None:
        raise HTTPException(status_code=503, detail="No approved pricing rule is configured for this route and tier")
    weight_surcharge = (Decimal(rule.per_kg_minor) * payload.package_weight_kg).to_integral_value(rounding=ROUND_CEILING)
    amount_minor = rule.base_fare_minor + int(weight_surcharge)
    expires_at = datetime.now(UTC) + timedelta(minutes=15)
    result = PricingQuote(
        pricing_rule_id=rule.id,
        origin_zone=payload.origin_zone,
        destination_zone=payload.destination_zone,
        delivery_tier=payload.delivery_tier,
        package_weight_kg=payload.package_weight_kg,
        amount_minor=amount_minor,
        currency=rule.currency,
        expires_at=expires_at,
    )
    db.add(result)
    db.flush()
    record_audit(db, actor_user_id=None, action="pricing.quote_created", resource_type="pricing_quote", resource_id=result.id, details={"currency": result.currency, "amount_minor": result.amount_minor})
    db.commit()
    return QuoteResponse(quote_id=result.id, origin_zone=result.origin_zone, destination_zone=result.destination_zone, delivery_tier=result.delivery_tier, package_weight_kg=payload.package_weight_kg, amount_minor=result.amount_minor, currency=result.currency, expires_at=expires_at)
