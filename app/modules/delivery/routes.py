from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.modules.audit.service import record_audit
from app.modules.auth.models import User
from app.modules.delivery.models import DeliveryAgent, ShipmentAssignment
from app.modules.delivery.schemas import (
    AgentApplication,
    AgentDashboardResponse,
    AgentStatusUpdate,
    AssignmentCreate,
    AssignmentResponse,
    AssignmentResponseUpdate,
    DeliveryAgentResponse,
    DeliveryEventCreate,
    DeliveryOperationsDashboardResponse,
)
from app.modules.shipments.lifecycle import TRANSITIONS
from app.modules.shipments.models import Shipment, ShipmentEvent

router = APIRouter()
AGENT_STATUS_PERMISSIONS = {
    "driver": {"pickup_scheduled", "picked_up", "in_transit", "exception"},
    "rider": {"out_for_delivery", "delivered", "exception"},
}


def require_platform_admin(user: User) -> None:
    if user.email.lower() not in get_settings().platform_admin_email_set:
        raise HTTPException(status_code=403, detail="Platform operations access is required")


def agent_response(agent: DeliveryAgent) -> DeliveryAgentResponse:
    return DeliveryAgentResponse(
        id=agent.id,
        user_id=agent.user_id,
        email=agent.user.email,
        full_name=agent.user.full_name,
        phone=agent.user.phone,
        agent_type=agent.agent_type,
        status=agent.status,
        created_at=agent.created_at,
    )


def assignment_response(assignment: ShipmentAssignment) -> AssignmentResponse:
    return AssignmentResponse(
        id=assignment.id,
        shipment_id=assignment.shipment.id,
        tracking_number=assignment.shipment.tracking_number,
        shipment_status=assignment.shipment.status,
        origin_zone=assignment.shipment.origin_zone,
        destination_zone=assignment.shipment.destination_zone,
        pickup_address=assignment.shipment.pickup_address,
        destination_address=assignment.shipment.destination_address,
        recipient_name=assignment.shipment.recipient_name,
        recipient_phone=assignment.shipment.recipient_phone,
        delivery_agent_id=assignment.delivery_agent_id,
        agent_type=assignment.agent_type,
        status=assignment.status,
        is_current=assignment.is_current,
        response_note=assignment.response_note,
        assigned_at=assignment.assigned_at,
        responded_at=assignment.responded_at,
    )


def get_assignment(db: Session, assignment_id: str, *, lock: bool = False) -> ShipmentAssignment | None:
    query = select(ShipmentAssignment).where(ShipmentAssignment.id == assignment_id)
    if lock:
        query = query.with_for_update()
    return db.scalar(query)


@router.post("/delivery/agents/apply", response_model=DeliveryAgentResponse, status_code=201)
def apply_as_delivery_agent(payload: AgentApplication, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.full_name or not user.phone:
        raise HTTPException(status_code=422, detail="Complete your profile name and phone number before applying")
    existing = db.scalar(select(DeliveryAgent).options(joinedload(DeliveryAgent.user)).where(DeliveryAgent.user_id == user.id, DeliveryAgent.agent_type == payload.agent_type))
    if existing is not None:
        raise HTTPException(status_code=409, detail="An application for this delivery role already exists")
    agent = DeliveryAgent(user_id=user.id, agent_type=payload.agent_type, status="pending")
    db.add(agent)
    try:
        db.flush()
        record_audit(db, actor_user_id=user.id, action="delivery_agent.applied", resource_type="delivery_agent", resource_id=agent.id, details={"agent_type": agent.agent_type})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An application for this delivery role already exists")
    return agent_response(db.scalar(select(DeliveryAgent).options(joinedload(DeliveryAgent.user)).where(DeliveryAgent.id == agent.id)))


@router.get("/delivery/me", response_model=list[DeliveryAgentResponse])
def list_my_delivery_profiles(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agents = db.scalars(select(DeliveryAgent).options(joinedload(DeliveryAgent.user)).where(DeliveryAgent.user_id == user.id).order_by(DeliveryAgent.agent_type))
    return [agent_response(agent) for agent in agents]


@router.get("/delivery/me/assignments", response_model=list[AssignmentResponse])
def list_my_assignments(
    include_history: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent_ids = select(DeliveryAgent.id).where(DeliveryAgent.user_id == user.id, DeliveryAgent.status == "active")
    query = select(ShipmentAssignment).options(joinedload(ShipmentAssignment.shipment)).where(ShipmentAssignment.delivery_agent_id.in_(agent_ids))
    if not include_history:
        query = query.where(ShipmentAssignment.is_current.is_(True))
    assignments = db.scalars(query.order_by(ShipmentAssignment.assigned_at.desc()).offset(offset).limit(limit))
    return [assignment_response(assignment) for assignment in assignments]


@router.get("/delivery/me/dashboard", response_model=AgentDashboardResponse)
def delivery_agent_dashboard(agent_type: str | None = Query(default=None, pattern="^(rider|driver)$"), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(DeliveryAgent).options(joinedload(DeliveryAgent.user)).where(DeliveryAgent.user_id == user.id, DeliveryAgent.status == "active")
    if agent_type:
        query = query.where(DeliveryAgent.agent_type == agent_type)
    agent = db.scalar(query.limit(1))
    if agent is None:
        raise HTTPException(status_code=404, detail="Active delivery profile not found")
    assignments = db.scalars(
        select(ShipmentAssignment)
        .options(joinedload(ShipmentAssignment.shipment))
        .where(ShipmentAssignment.delivery_agent_id == agent.id, ShipmentAssignment.is_current.is_(True))
        .order_by(ShipmentAssignment.assigned_at.desc())
    )
    response_assignments = [assignment_response(item) for item in assignments]
    return AgentDashboardResponse(agent=agent_response(agent), current_assignment_count=len(response_assignments), assignments=response_assignments)


@router.patch("/delivery/me/assignments/{assignment_id}", response_model=AssignmentResponse)
def respond_to_assignment(
    assignment_id: str,
    payload: AssignmentResponseUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assignment = get_assignment(db, assignment_id, lock=True)
    if assignment is None or assignment.delivery_agent.user_id != user.id or assignment.delivery_agent.status != "active":
        raise HTTPException(status_code=404, detail="Assignment not found")
    if not assignment.is_current or assignment.status != "assigned":
        raise HTTPException(status_code=409, detail="Assignment is no longer awaiting a response")
    assignment.status = payload.status
    assignment.response_note = payload.note
    assignment.responded_at = datetime.now(UTC)
    if payload.status == "declined":
        assignment.is_current = False
    record_audit(db, actor_user_id=user.id, action=f"shipment.assignment_{payload.status}", resource_type="shipment_assignment", resource_id=assignment.id, organization_id=assignment.shipment.organization_id, details={"agent_type": assignment.agent_type, "note_present": payload.note is not None})
    db.commit()
    return assignment_response(get_assignment(db, assignment.id))


@router.post("/admin/shipments/{shipment_id}/assignments", response_model=AssignmentResponse, status_code=201)
def assign_delivery_agent(
    shipment_id: str,
    payload: AssignmentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_platform_admin(user)
    shipment = db.scalar(select(Shipment).where(Shipment.id == shipment_id).with_for_update())
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if shipment.status in {"delivered", "cancelled"}:
        raise HTTPException(status_code=409, detail="A completed shipment cannot be assigned")
    agent = db.scalar(select(DeliveryAgent).where(DeliveryAgent.id == payload.delivery_agent_id).with_for_update())
    if agent is None or agent.status != "active":
        raise HTTPException(status_code=409, detail="Delivery agent is unavailable")
    existing = db.scalar(
        select(ShipmentAssignment)
        .where(ShipmentAssignment.shipment_id == shipment.id, ShipmentAssignment.agent_type == agent.agent_type, ShipmentAssignment.is_current.is_(True))
        .with_for_update()
    )
    if existing is not None and existing.delivery_agent_id == agent.id:
        return assignment_response(get_assignment(db, existing.id))
    if existing is not None:
        existing.status = "cancelled"
        existing.is_current = False
    assignment = ShipmentAssignment(
        shipment_id=shipment.id,
        delivery_agent_id=agent.id,
        agent_type=agent.agent_type,
        status="assigned",
        assigned_by_user_id=user.id,
    )
    db.add(assignment)
    db.flush()
    record_audit(db, actor_user_id=user.id, action="shipment.agent_assigned", resource_type="shipment_assignment", resource_id=assignment.id, organization_id=shipment.organization_id, details={"agent_type": agent.agent_type})
    db.commit()
    return assignment_response(get_assignment(db, assignment.id))


@router.get("/admin/delivery/agents", response_model=list[DeliveryAgentResponse])
def list_delivery_agents(
    agent_type: str | None = Query(default=None, pattern="^(rider|driver)$"),
    status: str | None = Query(default=None, pattern="^(pending|active|suspended)$"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_platform_admin(user)
    query = select(DeliveryAgent).options(joinedload(DeliveryAgent.user)).order_by(DeliveryAgent.created_at.desc())
    if agent_type:
        query = query.where(DeliveryAgent.agent_type == agent_type)
    if status:
        query = query.where(DeliveryAgent.status == status)
    agents = db.scalars(query.offset(offset).limit(limit))
    return [agent_response(agent) for agent in agents]


@router.patch("/admin/delivery/agents/{agent_id}", response_model=DeliveryAgentResponse)
def update_delivery_agent(agent_id: str, payload: AgentStatusUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_platform_admin(user)
    agent = db.scalar(select(DeliveryAgent).where(DeliveryAgent.id == agent_id).with_for_update())
    if agent is None:
        raise HTTPException(status_code=404, detail="Delivery agent not found")
    agent.status = payload.status
    if payload.status == "suspended":
        current_assignments = db.scalars(select(ShipmentAssignment).where(ShipmentAssignment.delivery_agent_id == agent.id, ShipmentAssignment.is_current.is_(True)))
        for assignment in current_assignments:
            assignment.status = "cancelled"
            assignment.is_current = False
    record_audit(db, actor_user_id=user.id, action=f"delivery_agent.{payload.status}", resource_type="delivery_agent", resource_id=agent.id, details={"agent_type": agent.agent_type})
    db.commit()
    return agent_response(agent)


@router.post("/delivery/me/assignments/{assignment_id}/events", response_model=AssignmentResponse)
def create_delivery_event(
    assignment_id: str,
    payload: DeliveryEventCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assignment = get_assignment(db, assignment_id, lock=True)
    if assignment is None or assignment.delivery_agent.user_id != user.id or assignment.delivery_agent.status != "active":
        raise HTTPException(status_code=404, detail="Assignment not found")
    if not assignment.is_current or assignment.status != "accepted":
        raise HTTPException(status_code=409, detail="Only an accepted current assignment can update shipment status")
    shipment = db.scalar(select(Shipment).where(Shipment.id == assignment.shipment_id).with_for_update())
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if payload.status not in AGENT_STATUS_PERMISSIONS[assignment.agent_type]:
        raise HTTPException(status_code=403, detail="This delivery role cannot record that shipment status")
    if payload.status not in TRANSITIONS[shipment.status]:
        raise HTTPException(status_code=409, detail="Shipment status transition is not allowed")
    if payload.status == "delivered" and (not payload.proof_method or not payload.proof_reference):
        raise HTTPException(status_code=422, detail="Proof method and reference are required for delivery completion")
    shipment.status = payload.status
    shipment.events.append(
        ShipmentEvent(
            status=payload.status,
            note=payload.note,
            proof_method=payload.proof_method,
            proof_reference=payload.proof_reference,
            created_by_user_id=user.id,
        )
    )
    if payload.status == "delivered":
        assignment.status = "completed"
        assignment.is_current = False
        db.query(ShipmentAssignment).filter(
            ShipmentAssignment.shipment_id == shipment.id,
            ShipmentAssignment.id != assignment.id,
            ShipmentAssignment.is_current.is_(True),
        ).update(
            {ShipmentAssignment.status: "completed", ShipmentAssignment.is_current: False},
            synchronize_session=False,
        )
    record_audit(db, actor_user_id=user.id, action="shipment.status_changed_by_agent", resource_type="shipment", resource_id=shipment.id, organization_id=shipment.organization_id, details={"status": payload.status, "agent_type": assignment.agent_type, "proof_method": payload.proof_method})
    db.commit()
    return assignment_response(get_assignment(db, assignment.id))


@router.get("/admin/operations/dashboard", response_model=DeliveryOperationsDashboardResponse)
def operations_dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_platform_admin(user)
    agent_rows = db.execute(select(DeliveryAgent.agent_type, DeliveryAgent.status, func.count(DeliveryAgent.id)).group_by(DeliveryAgent.agent_type, DeliveryAgent.status)).all()
    assignment_rows = db.execute(select(ShipmentAssignment.status, func.count(ShipmentAssignment.id)).where(ShipmentAssignment.is_current.is_(True)).group_by(ShipmentAssignment.status)).all()
    shipment_rows = db.execute(select(Shipment.status, func.count(Shipment.id)).group_by(Shipment.status)).all()
    return DeliveryOperationsDashboardResponse(
        agents_by_type_and_status={f"{agent_type}:{status}": count for agent_type, status, count in agent_rows},
        current_assignments_by_status={status: count for status, count in assignment_rows},
        shipments_by_status={status: count for status, count in shipment_rows},
    )
