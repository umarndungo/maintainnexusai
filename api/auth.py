"""Authentication and server-side role authorization for the API."""

import base64
import hashlib
import hmac
import json
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from config import AUTH_SECRET, INTERNAL_SERVICE_TOKEN

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
bearer = HTTPBearer(auto_error=False)
JWT_SECRET = AUTH_SECRET.encode()

USERS = {
    "tech-demo": {"name": "Demo Technician", "role": "technician", "station_ids": ["STATION-1"]},
    "engineer-demo": {"name": "Demo Engineer", "role": "engineer", "station_ids": ["STATION-1"]},
    "executive-demo": {"name": "Demo Executive", "role": "executive", "station_ids": []},
    "supervisor-demo": {"name": "Demo Supervisor", "role": "supervisor", "station_ids": []},
}


class LoginRequest(BaseModel):
    user_id: str


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
        if claims["exp"] < int(time.time()) or claims["sub"] not in USERS:
            raise ValueError
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc
    return {"id": claims["sub"], **USERS[claims["sub"]]}


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


@router.post("/login")
async def login(request: LoginRequest):
    user = USERS.get(request.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")
    return {"access_token": create_access_token(request.user_id), "token_type": "bearer", "user": {"id": request.user_id, **user}}


@router.get("/me")
async def me(user: Annotated[dict, Depends(get_current_user)]):
    return user