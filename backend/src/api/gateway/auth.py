"""
Gateway Auth Routes
Mock-compatible auth that mirrors the frontend's mock-auth.ts contract.
Returns the same session shape so the frontend can switch from localStorage
mock to real API calls without changing parsing logic.

Later migration path:
    1. Provision Supabase project
    2. Update frontend lib/auth.ts to use supabase.auth.signInWithPassword
    3. Gateway switches from password-verify to JWT validation
    4. API shapes remain identical
"""

from __future__ import annotations

import time
from fastapi import APIRouter, HTTPException, Header
from typing import Optional

from src.api.gateway.db import GatewayDB
from src.api.gateway.models import LoginRequest, LoginResponse, SessionOut, UserOut, UserMetadata

router = APIRouter(prefix="/gateway/v1/auth", tags=["gateway-auth"])

# Initialize DB once at module level (composition root can inject later)
_db = GatewayDB()

# In-memory token store (revocable, non-persistent). Production: Redis or JWT.
_token_store: dict[str, dict] = {}


def _make_token(user_id: str) -> str:
    return f"gw-token-{user_id}-{int(time.time() * 1000)}"


def _user_out_from_db(row) -> UserOut:
    return UserOut(
        id=f"user-{row.id}",
        email=row.email,
        user_metadata=UserMetadata(
            full_name=row.full_name or "",
            role=row.role or "Staff",
            school=row.tenant_id or "",
            avatar_seed=row.avatar_seed or row.full_name or "User",
        ),
    )


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    """
    Validate email/password against gateway users table.
    Returns session matching mock-auth.ts shape.
    """
    user = _db.get_user_by_email(body.email)
    if user is None:
        return LoginResponse(data=None, error={"message": "Invalid email or password."})

    # In mock mode, password is static for demo accounts.
    # Production: bcrypt verify here.
    demo_passwords = {
        "admin@school.edu": "password123",
        "teacher@school.edu": "password123",
    }
    expected = demo_passwords.get(body.email)
    if expected is None or body.password != expected:
        return LoginResponse(data=None, error={"message": "Invalid email or password."})

    token = _make_token(str(user.id))
    expires_at = int(time.time()) + 60 * 60 * 8  # 8 hours
    session = SessionOut(
        user=_user_out_from_db(user),
        access_token=token,
        expires_at=expires_at,
    )
    _token_store[token] = {"user_id": user.id, "expires_at": expires_at}
    return LoginResponse(data={"session": session.model_dump(), "user": session.user.model_dump()}, error=None)


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """Invalidate token."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        _token_store.pop(token, None)
    return {"status": "ok"}


@router.get("/session")
async def get_session(authorization: Optional[str] = Header(None)):
    """Validate token and return current session."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.replace("Bearer ", "")
    record = _token_store.get(token)
    if record is None or record["expires_at"] < time.time():
        raise HTTPException(status_code=401, detail="Session expired")

    user = _db.get_user_by_email(record.get("email", ""))
    if user is None:
        # Reconstruct from token store if DB missing
        raise HTTPException(status_code=401, detail="User not found")

    return {
        "session": SessionOut(
            user=_user_out_from_db(user),
            access_token=token,
            expires_at=record["expires_at"],
        ).model_dump()
    }
