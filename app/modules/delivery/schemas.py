from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AgentApplication(BaseModel):
    agent_type: Literal["rider", "driver"]


class AgentStatusUpdate(BaseModel):
    status: Literal["active", "suspended"]


class DeliveryAgentResponse(BaseModel):
    id: str
    user_id: str
    email: str
    full_name: str | None
    phone: str | None
    agent_type: str
    status: str
    created_at: datetime


class AssignmentCreate(BaseModel):
    delivery_agent_id: str


class AssignmentResponse(BaseModel):
    id: str
    shipment_id: str
    tracking_number: str
    shipment_status: str
    origin_zone: str
    destination_zone: str
    pickup_address: str
    destination_address: str
    recipient_name: str
    recipient_phone: str
    delivery_agent_id: str
    agent_type: str
    status: str
    is_current: bool
    response_note: str | None
    assigned_at: datetime
    responded_at: datetime | None


class AssignmentResponseUpdate(BaseModel):
    status: Literal["accepted", "declined"]
    note: str | None = Field(default=None, max_length=300)


class DeliveryEventCreate(BaseModel):
    status: Literal["pickup_scheduled", "picked_up", "in_transit", "out_for_delivery", "delivered", "exception"]
    note: str | None = Field(default=None, max_length=500)
    proof_method: Literal["otp", "photo", "signature"] | None = None
    proof_reference: str | None = Field(default=None, max_length=500)


class AgentDashboardResponse(BaseModel):
    agent: DeliveryAgentResponse
    current_assignment_count: int
    assignments: list[AssignmentResponse]


class DeliveryOperationsDashboardResponse(BaseModel):
    agents_by_type_and_status: dict[str, int]
    current_assignments_by_status: dict[str, int]
    shipments_by_status: dict[str, int]
