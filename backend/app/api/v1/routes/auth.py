from collections import defaultdict, deque
from threading import Lock
import time

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.auth import AuthenticatedUser, LoginRequest
from app.services.auth_service import authenticate_user, create_session, revoke_session


router = APIRouter(prefix="/auth")
failed_logins: dict[str, deque[float]] = defaultdict(deque)
failed_login_lock = Lock()


def login_key(request: Request, username: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{host}:{username.strip().casefold()}"


def enforce_login_limit(key: str) -> None:
    settings = get_settings()
    cutoff = time.monotonic() - settings.login_failure_window_minutes * 60
    with failed_login_lock:
        attempts = failed_logins[key]
        while attempts and attempts[0] < cutoff:
            attempts.popleft()
        if len(attempts) >= settings.login_failure_limit:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many login attempts")


def record_login_failure(key: str) -> None:
    with failed_login_lock:
        failed_logins[key].append(time.monotonic())


def clear_login_failures(key: str) -> None:
    with failed_login_lock:
        failed_logins.pop(key, None)


@router.post("/login", response_model=AuthenticatedUser)
def login(
    credentials: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    key = login_key(request, credentials.username)
    enforce_login_limit(key)
    user = authenticate_user(db, credentials.username, credentials.password)
    if user is None:
        record_login_failure(key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    clear_login_failures(key)
    settings = get_settings()
    token = create_session(db, user)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_minutes * 60,
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="strict",
        path="/",
    )
    return AuthenticatedUser(id=user.id, username=user.username)


@router.get("/me", response_model=AuthenticatedUser)
def me(user: CurrentUser) -> AuthenticatedUser:
    return AuthenticatedUser(id=user.id, username=user.username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=get_settings().session_cookie_name),
) -> Response:
    revoke_session(db, session_token)
    response.delete_cookie(get_settings().session_cookie_name, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
