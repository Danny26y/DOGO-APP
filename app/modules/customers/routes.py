from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.modules.audit.service import record_audit
from app.modules.auth.models import User
from app.modules.customers.models import (
    CustomerAddress,
    CustomerIdentitySubmission,
    CustomerVerificationConsent,
)
from app.modules.customers.schemas import (
    CustomerAddressCreate,
    CustomerAddressResponse,
    CustomerAddressUpdate,
    CustomerDashboardResponse,
    VerificationTermsAcceptance,
    VerificationTermsResponse,
)
from app.modules.orders.models import Order

router = APIRouter()


class IdentitySubmissionResponse(BaseModel):
    id: str
    user_id: str
    document_type: str
    status: str
    created_at: datetime


class IdentityReviewRequest(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    review_note: str | None = Field(default=None, max_length=500)


def active_verification_terms() -> tuple[str, str, str, str] | None:
    settings = get_settings()
    values = (
        getattr(settings, "customer_verification_terms_version", "").strip(),
        getattr(settings, "customer_verification_terms_url", "").strip(),
        getattr(settings, "privacy_policy_version", "").strip(),
        getattr(settings, "privacy_policy_url", "").strip(),
    )
    return values if all(values) else None


@router.post("/customers/me/identity-submissions", response_model=IdentitySubmissionResponse, status_code=201)
async def submit_identity_document(
    request: Request,
    document_type: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if document_type not in {"national_id", "passport", "drivers_license", "voters_card"}:
        raise HTTPException(status_code=422, detail="Unsupported identity document type")
    allowed = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type not in allowed:
        raise HTTPException(status_code=415, detail="Upload a PDF, JPEG, or PNG document")
    current = db.scalar(select(CustomerIdentitySubmission).where(CustomerIdentitySubmission.user_id == user.id, CustomerIdentitySubmission.status == "pending"))
    if current:
        raise HTTPException(status_code=409, detail="An identity submission is already pending review")
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Document must be 5 MB or smaller")
    if not content:
        raise HTTPException(status_code=413, detail="Document must be 5 MB or smaller")
    signatures = {"application/pdf": b"%PDF-", "image/jpeg": b"\xff\xd8\xff", "image/png": b"\x89PNG\r\n\x1a\n"}
    if not content.startswith(signatures[content_type]):
        raise HTTPException(status_code=415, detail="File content does not match its declared document type")
    name = f"{uuid4().hex}{allowed[content_type]}"
    root = Path(get_settings().verification_upload_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_bytes(content)
    filename = Path(request.headers.get("x-file-name", "identity-document")).name[:200]
    submission = CustomerIdentitySubmission(user_id=user.id, document_type=document_type, storage_name=name, original_filename=filename, content_type=content_type, status="pending")
    db.add(submission)
    db.flush()
    record_audit(db, actor_user_id=user.id, action="customer.identity_submitted", resource_type="customer_identity_submission", resource_id=submission.id, details={"document_type": document_type})
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/admin/identity-submissions", response_model=list[IdentitySubmissionResponse])
def list_identity_submissions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.email.lower() not in get_settings().platform_admin_email_set:
        raise HTTPException(status_code=403, detail="Platform administrator access is required")
    return list(db.scalars(select(CustomerIdentitySubmission).order_by(CustomerIdentitySubmission.created_at).limit(200)))


@router.get("/admin/identity-submissions/{submission_id}/document")
def download_identity_document(submission_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.email.lower() not in get_settings().platform_admin_email_set:
        raise HTTPException(status_code=403, detail="Platform administrator access is required")
    submission = db.get(CustomerIdentitySubmission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    path = Path(get_settings().verification_upload_dir).resolve() / submission.storage_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Document file not found")
    return FileResponse(path, media_type=submission.content_type, filename=submission.original_filename, content_disposition_type="attachment")


@router.patch("/admin/identity-submissions/{submission_id}", response_model=IdentitySubmissionResponse)
def review_identity_submission(submission_id: str, payload: IdentityReviewRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.email.lower() not in get_settings().platform_admin_email_set:
        raise HTTPException(status_code=403, detail="Platform administrator access is required")
    submission = db.scalar(select(CustomerIdentitySubmission).where(CustomerIdentitySubmission.id == submission_id).with_for_update())
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.status != "pending":
        raise HTTPException(status_code=409, detail="Submission has already been reviewed")
    submission.status = payload.status
    submission.review_note = payload.review_note
    submission.reviewed_by_user_id = user.id
    submission.reviewed_at = datetime.now(UTC)
    record_audit(db, actor_user_id=user.id, action=f"customer.identity_{payload.status}", resource_type="customer_identity_submission", resource_id=submission.id, details={"owner_user_id": submission.user_id})
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/customers/me/verification-terms", response_model=VerificationTermsResponse)
def get_verification_terms(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    configured = active_verification_terms()
    if configured is None:
        return VerificationTermsResponse(configured=False)
    terms_version, terms_url, privacy_version, privacy_url = configured
    consent = db.scalar(
        select(CustomerVerificationConsent).where(
            CustomerVerificationConsent.user_id == user.id,
            CustomerVerificationConsent.terms_version == terms_version,
            CustomerVerificationConsent.privacy_policy_version == privacy_version,
        )
    )
    return VerificationTermsResponse(
        configured=True,
        terms_version=terms_version,
        terms_url=terms_url,
        privacy_policy_version=privacy_version,
        privacy_policy_url=privacy_url,
        accepted_current_versions=consent is not None,
        accepted_at=consent.accepted_at if consent else None,
    )


@router.post("/customers/me/verification-terms/accept", response_model=VerificationTermsResponse)
def accept_verification_terms(
    payload: VerificationTermsAcceptance,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    configured = active_verification_terms()
    if configured is None:
        raise HTTPException(status_code=503, detail="Current verification terms and privacy policy are not configured")
    terms_version, terms_url, privacy_version, privacy_url = configured
    if payload.terms_version != terms_version or payload.privacy_policy_version != privacy_version:
        raise HTTPException(status_code=409, detail="The terms or privacy policy version has changed; reload the current documents")
    consent = db.scalar(
        select(CustomerVerificationConsent).where(
            CustomerVerificationConsent.user_id == user.id,
            CustomerVerificationConsent.terms_version == terms_version,
            CustomerVerificationConsent.privacy_policy_version == privacy_version,
        )
    )
    if consent is None:
        consent = CustomerVerificationConsent(
            user_id=user.id,
            terms_version=terms_version,
            privacy_policy_version=privacy_version,
        )
        db.add(consent)
        try:
            db.flush()
            record_audit(
                db,
                actor_user_id=user.id,
                action="customer.verification_terms_accepted",
                resource_type="customer_verification_consent",
                resource_id=consent.id,
                details={"terms_version": terms_version, "privacy_policy_version": privacy_version},
            )
            db.commit()
        except IntegrityError:
            db.rollback()
            consent = db.scalar(
                select(CustomerVerificationConsent).where(
                    CustomerVerificationConsent.user_id == user.id,
                    CustomerVerificationConsent.terms_version == terms_version,
                    CustomerVerificationConsent.privacy_policy_version == privacy_version,
                )
            )
            if consent is None:
                raise HTTPException(status_code=409, detail="Terms acceptance could not be recorded")
    return VerificationTermsResponse(
        configured=True,
        terms_version=terms_version,
        terms_url=terms_url,
        privacy_policy_version=privacy_version,
        privacy_policy_url=privacy_url,
        accepted_current_versions=True,
        accepted_at=consent.accepted_at,
    )


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
