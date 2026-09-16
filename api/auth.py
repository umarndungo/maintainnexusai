"""Authentication and server-side role authorization for the API."""

import base64
import hashlib
import hmac
import json
import time
from typing import Annotated

import bcrypt
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, field_validator
from config import AUTH_SECRET, INTERNAL_SERVICE_TOKEN
from database.db import SessionLocal
from database.models import StaffCredential

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
bearer = HTTPBearer(auto_error=False)
JWT_SECRET = AUTH_SECRET.encode()

USERS = {
    "tech-demo": {"name": "Demo Technician", "role": "technician", "station_ids": ["STATION-1"], "technician_id": "TECH-101"},
    "engineer-demo": {"name": "Demo Engineer", "role": "engineer", "station_ids": ["STATION-1"]},
    "executive-demo": {"name": "Demo Executive", "role": "executive", "station_ids": []},
    "supervisor-demo": {"name": "Demo Supervisor", "role": "supervisor", "station_ids": []},
}
USERS.update(
    {
        f"ENG-{number}": {
            "name": f"Engineer {number}",
            "role": "engineer",
            "station_ids": ["STATION-1"],
        }
        for number in range(1, 4)
    }
)
USERS.update(
    {
        f"SUP-{number}": {
            "name": f"Supervisor {number}",
            "role": "supervisor",
            "station_ids": [],
        }
        for number in range(1, 4)
    }
)
USERS.update(
    {
        f"EXEC-{number}": {
            "name": f"Executive {number}",
            "role": "executive",
            "station_ids": [],
        }
        for number in range(1, 4)
    }
)


class LoginRequest(BaseModel):
    user_id: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("New password must be at least 8 characters")
        return value


def _lookup_user(user_id: str) -> dict | None:
    """Resolve a login/token subject to a user record.

    Checks the static demo USERS dict first, then falls back to the HR
    technician roster (api/technicians.py) so a raw roster id like
    "TECH-105" is itself a valid login — no separate mapping table to
    keep in sync with the roster. Imported locally to avoid a circular
    import, since technicians.py imports from this module at load time.
    """
    user = USERS.get(user_id)
    if user is not None:
        return user
    from api.technicians import TECHNICIANS_BY_ID

    tech = TECHNICIANS_BY_ID.get(user_id)
    if tech is None:
        return None
    return {"name": tech["name"], "role": "technician", "station_ids": [], "technician_id": tech["id"]}


def _verify_password(user_id: str, password: str) -> dict | None:
    """Return the resolved identity only when its stored password matches."""
    db = SessionLocal()
    try:
        credential = db.get(StaffCredential, user_id)
        if credential is None:
            return None
        try:
            valid = bcrypt.checkpw(password.encode(), credential.password_hash.encode())
        except ValueError:
            valid = False
        if not valid:
            return None
        user = _lookup_user(user_id)
        if user is None:
            return None
        return {"id": user_id, **user, "must_change_password": credential.must_change_password}
    finally:
        db.close()


def _encode(value: dict) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _sign(header: str, payload: str) -> str:
    message = f"{header}.{payload}".encode()
    return base64.urlsafe_b64encode(hmac.new(JWT_SECRET, message, hashlib.sha256).digest()).decode().rstrip("=")


def create_access_token(user_id: str) -> str:
    header = _encode({"alg": "HS256", "typ": "JWT"})
    payload = _encode({"sub": user_id, "exp": int(time.time()) + 3600})
    return f"{header}.{payload}.{_sign(header, payload)}"


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    try:
        header, payload, signature = credentials.credentials.split(".")
        if not hmac.compare_digest(signature, _sign(header, payload)):
            raise ValueError
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if claims["exp"] < int(time.time()):
            raise ValueError
        user = _lookup_user(claims["sub"])
        if user is None:
            raise ValueError
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc
    return {"id": claims["sub"], **user}


def require_roles(*roles: str):
    def dependency(user: Annotated[dict, Depends(get_current_user)]) -> dict:
        if user["role"] not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return dependency


def require_internal_service(x_internal_service: str | None = Header(default=None)) -> None:
    if not hmac.compare_digest(x_internal_service or "", INTERNAL_SERVICE_TOKEN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Internal service access required")


def require_internal_or_user(
    x_internal_service: str | None = Header(default=None),
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)] = None,
) -> dict:
    if hmac.compare_digest(x_internal_service or "", INTERNAL_SERVICE_TOKEN):
        return {"id": "internal", "role": "internal", "station_ids": []}
    return get_current_user(credentials)


def require_internal_or_roles(*roles: str):
    """Like require_roles, but also accepts the internal-service header —
    for an endpoint the ETL pipeline calls unattended (no user session)
    that should otherwise keep its existing human role restriction intact.
    Unlike require_internal_or_user, a human caller still needs one of
    ``roles``; this doesn't open the endpoint to every logged-in user."""

    def dependency(
        x_internal_service: str | None = Header(default=None),
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)] = None,
    ) -> dict:
        if hmac.compare_digest(x_internal_service or "", INTERNAL_SERVICE_TOKEN):
            return {"id": "internal", "role": "internal", "station_ids": []}
        user = get_current_user(credentials)
        if user["role"] not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return dependency


@router.post("/login")
async def login(request: LoginRequest):
    user = _verify_password(request.user_id, request.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {"access_token": create_access_token(request.user_id), "token_type": "bearer", "user": user}


@router.patch("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user: Annotated[dict, Depends(get_current_user)],
):
    db = SessionLocal()
    try:
        credential = db.get(StaffCredential, user["id"])
        if credential is None or not bcrypt.checkpw(
            request.current_password.encode(), credential.password_hash.encode()
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid current password")
        credential.password_hash = bcrypt.hashpw(
            request.new_password.encode(), bcrypt.gensalt()
        ).decode()
        credential.must_change_password = False
        db.commit()
    finally:
        db.close()
    return {"status": "ok"}


@router.get("/me")
async def me(user: Annotated[dict, Depends(get_current_user)]):
    return user