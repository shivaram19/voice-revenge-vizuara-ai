"""
Pydantic models for the gateway API.
Defines request/response contracts shared between backend and frontend.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class UserMetadata(BaseModel):
    full_name: str
    role: str
    school: str
    avatar_seed: str


class UserOut(BaseModel):
    id: str
    email: str
    user_metadata: UserMetadata


class SessionOut(BaseModel):
    user: UserOut
    access_token: str
    expires_at: int


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, str]] = None


# ---------------------------------------------------------------------------
# Tenant
# ---------------------------------------------------------------------------

class TenantCreate(BaseModel):
    tenant_id: str
    name: str
    district: Optional[str] = None
    admin_email: Optional[str] = None
    student_count_range: Optional[str] = None


class TenantOut(BaseModel):
    id: int
    tenant_id: str
    name: str
    district: Optional[str] = None
    admin_email: Optional[str] = None
    student_count_range: Optional[str] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Student
# ---------------------------------------------------------------------------

class StudentCreate(BaseModel):
    name: str
    grade: str
    parent_name: str
    parent_phone: str
    attendance_status: str = "Present"


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    grade: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    attendance_status: Optional[str] = None


class StudentOut(BaseModel):
    id: int
    tenant_id: str
    name: str
    grade: str
    parent_name: str
    parent_phone: str
    attendance_status: str
    recent_call_summary: str
    created_at: datetime
    updated_at: datetime


class StudentListResponse(BaseModel):
    items: List[StudentOut]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Call / Transcript
# ---------------------------------------------------------------------------

class TranscriptLineOut(BaseModel):
    speaker: str
    text: str
    timestamp_ms: int


class CallOut(BaseModel):
    id: int
    call_sid: str
    tenant_id: str
    student_id: Optional[int] = None
    student_name: Optional[str] = None
    domain: Optional[str] = None
    direction: Optional[str] = None
    phone_to: Optional[str] = None
    phone_from: Optional[str] = None
    status: Optional[str] = None
    call_type: Optional[str] = None
    duration_seconds: int = 0
    transcript_summary: Optional[str] = None
    created_at: datetime
    ended_at: Optional[datetime] = None


class CallListResponse(BaseModel):
    items: List[CallOut]
    total: int
    page: int
    page_size: int


class ActiveCallOut(BaseModel):
    call_sid: str
    student_name: Optional[str] = None
    parent_name: Optional[str] = None
    call_type: str
    duration_seconds: int
    status: str
    transcript_count: int


class TriggerCallRequest(BaseModel):
    parent_phone: str
    language: str = "te-IN"
    domain: str = "education"
    call_type: str = "general"


# ---------------------------------------------------------------------------
# Analytics / Dashboard
# ---------------------------------------------------------------------------

class DashboardKPIs(BaseModel):
    total_calls: int = 0
    successful_contacts: int = 0
    failed_voicemail: int = 0
    active_agents: int = 0


class DashboardTrend(BaseModel):
    metric: str
    value: str
    direction: str  # "up" | "down" | "neutral"
    percentage: Optional[str] = None


class DashboardResponse(BaseModel):
    generated_at: datetime
    kpis: DashboardKPIs
    trends: List[DashboardTrend]
    recent_calls: List[Dict[str, Any]]


class SystemStatusResponse(BaseModel):
    gateway_status: str = "operational"
    ai_latency_ms: int = 850
    daily_quota_percent: int = 14
    active_calls: int = 0
    version: str = "0.1.0"


# ---------------------------------------------------------------------------
# WebSocket messages
# ---------------------------------------------------------------------------

class WSMessage(BaseModel):
    event: str  # "call_started", "transcript", "call_ended", "heartbeat"
    payload: Dict[str, Any] = Field(default_factory=dict)
