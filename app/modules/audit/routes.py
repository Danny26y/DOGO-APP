from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User

router = APIRouter()


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    actor_user_id: str | None
    organization_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    details: dict[str, Any]
    created_at: datetime


@router.get("/admin/audit-logs", response_model=list[AuditLogResponse])
def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    before: datetime | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.email.lower() not in get_settings().platform_admin_email_set:
        raise HTTPException(status_code=403, detail="Platform administrator access is required")
    query = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    if before is not None:
        query = query.where(AuditLog.created_at < before)
    return list(db.scalars(query.limit(limit)))
