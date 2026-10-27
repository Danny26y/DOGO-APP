from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db.session import get_db
from app.modules.audit.service import record_audit
from app.modules.auth.models import (
    Organization,
    OrganizationMembership,
    RefreshSession,
    User,
)
from app.modules.auth.schemas import (
    LoginRequest,
    OrganizationCreate,
    OrganizationMemberAdd,
    OrganizationMemberResponse,
    OrganizationResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter()
identity_router = APIRouter()
organizations_router = APIRouter()


def token_response(user: User, db: Session, family_id: str | None = None) -> tuple[TokenResponse, RefreshSession]:
    settings = get_settings()
    refresh_token = create_refresh_token()
    session = RefreshSession(
        user_id=user.id,
        family_id=family_id or str(uuid4()),
        token_hash=hash_refresh_token(refresh_token),
        expires_at=datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_days),
    )
    db.add(session)
    db.flush()
    return TokenResponse(access_token=create_access_token(user.id), refresh_token=refresh_token, expires_in=settings.jwt_access_token_minutes * 60), session


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower()
    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.flush()
        response, _ = token_response(user, db)
        record_audit(db, actor_user_id=user.id, action="user.registered", resource_type="user", resource_id=user.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    db.refresh(user)
    return response


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect", headers={"WWW-Authenticate": "Bearer"})
    response, _ = token_response(user, db)
    record_audit(db, actor_user_id=user.id, action="auth.login", resource_type="user", resource_id=user.id)
    db.commit()
    return response


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    session = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == hash_refresh_token(payload.refresh_token)).with_for_update())
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token", headers={"WWW-Authenticate": "Bearer"})
    now = datetime.now(UTC)
    expires_at = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=UTC)
    if session.revoked_at is not None:
        db.query(RefreshSession).filter(RefreshSession.family_id == session.family_id, RefreshSession.revoked_at.is_(None)).update({RefreshSession.revoked_at: now}, synchronize_session=False)
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token reuse detected", headers={"WWW-Authenticate": "Bearer"})
    if expires_at <= now:
        session.revoked_at = now
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token has expired", headers={"WWW-Authenticate": "Bearer"})
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        session.revoked_at = now
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid refresh token", headers={"WWW-Authenticate": "Bearer"})
    consumed = db.execute(update(RefreshSession).where(RefreshSession.id == session.id, RefreshSession.revoked_at.is_(None)).values(revoked_at=now))
    if consumed.rowcount != 1:
        db.rollback()
        db.query(RefreshSession).filter(RefreshSession.family_id == session.family_id, RefreshSession.revoked_at.is_(None)).update({RefreshSession.revoked_at: now}, synchronize_session=False)
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token reuse detected", headers={"WWW-Authenticate": "Bearer"})
    session.revoked_at = now
    response, replacement = token_response(user, db, family_id=session.family_id)
    session.replaced_by_id = replacement.id
    db.commit()
    return response


@router.post("/logout", status_code=204)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    session = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == hash_refresh_token(payload.refresh_token)))
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        record_audit(db, actor_user_id=session.user_id, action="auth.logout", resource_type="refresh_session", resource_id=session.id)
        db.commit()


@identity_router.get("/users/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user


@organizations_router.get("/organizations", response_model=list[OrganizationResponse])
def list_organizations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Organization, OrganizationMembership.role).join(OrganizationMembership).where(OrganizationMembership.user_id == user.id)).all()
    return [OrganizationResponse(id=org.id, name=org.name, organization_type=org.organization_type, role=role, created_at=org.created_at) for org, role in rows]


@organizations_router.post("/organizations", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(payload: OrganizationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    organization = Organization(name=payload.name, organization_type=payload.organization_type)
    db.add(organization)
    db.flush()
    db.add(OrganizationMembership(user_id=user.id, organization_id=organization.id, role="owner"))
    record_audit(db, actor_user_id=user.id, action="organization.created", resource_type="organization", resource_id=organization.id, organization_id=organization.id)
    db.commit()
    db.refresh(organization)
    return OrganizationResponse(id=organization.id, name=organization.name, organization_type=organization.organization_type, role="owner", created_at=organization.created_at)


@organizations_router.get("/organizations/{organization_id}/members", response_model=list[OrganizationMemberResponse])
def list_organization_members(organization_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    role = db.scalar(select(OrganizationMembership.role).where(OrganizationMembership.user_id == user.id, OrganizationMembership.organization_id == organization_id))
    if role not in {"owner", "admin"}:
        raise HTTPException(status_code=404, detail="Organization not found")
    rows = db.execute(select(User, OrganizationMembership).join(OrganizationMembership).where(OrganizationMembership.organization_id == organization_id).order_by(User.email)).all()
    return [OrganizationMemberResponse(user_id=member_user.id, email=member_user.email, role=membership.role, created_at=membership.created_at) for member_user, membership in rows]


@organizations_router.post("/organizations/{organization_id}/members", response_model=OrganizationMemberResponse, status_code=201)
def add_organization_member(organization_id: str, payload: OrganizationMemberAdd, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    role = db.scalar(select(OrganizationMembership.role).where(OrganizationMembership.user_id == user.id, OrganizationMembership.organization_id == organization_id))
    if role != "owner":
        raise HTTPException(status_code=404, detail="Organization not found")
    member_user = db.scalar(select(User).where(User.email == payload.email.lower(), User.is_active.is_(True)))
    if member_user is None:
        raise HTTPException(status_code=404, detail="Existing active user account not found")
    membership = OrganizationMembership(user_id=member_user.id, organization_id=organization_id, role=payload.role)
    db.add(membership)
    try:
        db.flush()
        record_audit(db, actor_user_id=user.id, action="organization.member_added", resource_type="organization_membership", resource_id=membership.id, organization_id=organization_id, details={"role": payload.role})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="User is already a member of this organization")
    db.refresh(membership)
    return OrganizationMemberResponse(user_id=member_user.id, email=member_user.email, role=membership.role, created_at=membership.created_at)
