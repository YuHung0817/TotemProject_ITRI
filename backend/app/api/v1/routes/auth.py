from collections import defaultdict, deque
from threading import Lock
import time

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.api.errors import api_error
from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import AuthenticatedUser, LoginRequest, ReplaceSessionRequest
from app.services.auth_service import (
    as_utc,
    authenticate_user,
    consume_replacement_challenge,
    create_replacement_challenge,
    create_session_if_available,
    replace_user_sessions,
    revoke_session,
)


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


def set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_minutes * 60,
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="strict",
        path="/",
    )


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
    token, sessions = create_session_if_available(db, user)
    if sessions:
        challenge = create_replacement_challenge(
            user.id,
            {session.id for session in sessions},
        )
        raise api_error(
            status.HTTP_409_CONFLICT,
            "session_already_active",
            challenge=challenge,
            active_since=as_utc(
                min(session.created_at for session in sessions)
            ).isoformat(),
            expires_in_seconds=get_settings().session_replacement_challenge_minutes * 60,
        )
    if token is None:
        raise RuntimeError("Login session creation returned no token")
    set_session_cookie(response, token)
    return AuthenticatedUser(id=user.id, username=user.username)


@router.post("/login/replace", response_model=AuthenticatedUser)
def replace_login(
    request: ReplaceSessionRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    challenge_data = consume_replacement_challenge(request.challenge)
    if challenge_data is None:
        raise api_error(status.HTTP_409_CONFLICT, "invalid_replacement_challenge")
    user_id, expected_session_ids = challenge_data
    user = db.get(User, user_id)
    if user is None:
        raise api_error(status.HTTP_409_CONFLICT, "invalid_replacement_challenge")
    token = replace_user_sessions(db, user, expected_session_ids)
    if token is None:
        raise api_error(status.HTTP_409_CONFLICT, "invalid_replacement_challenge")
    set_session_cookie(response, token)
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
