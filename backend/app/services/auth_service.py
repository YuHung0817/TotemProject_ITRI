from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from threading import Lock

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import User, UserSession, utc_now


password_hasher = PasswordHasher()
replacement_challenges: dict[str, tuple[str, datetime, frozenset[str]]] = {}
replacement_challenge_lock = Lock()
login_session_lock = Lock()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    if not password_hash:
        return False
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.username == username.strip()))
    if user is None or not verify_password(user.password_hash, password):
        return None
    if password_hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.commit()
    return user


def session_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def create_session(db: Session, user: User) -> str:
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    now = utc_now()
    db.add(
        UserSession(
            id=session_token_hash(token),
            user_id=user.id,
            created_at=now,
            expires_at=now + timedelta(minutes=settings.session_ttl_minutes),
        )
    )
    db.commit()
    return token


def active_sessions(db: Session, user_id: str) -> list[UserSession]:
    now = utc_now()
    return list(
        db.scalars(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
            )
        ).all()
    )


def create_session_if_available(
    db: Session, user: User
) -> tuple[str | None, list[UserSession]]:
    with login_session_lock:
        sessions = active_sessions(db, user.id)
        if sessions:
            return None, sessions
        return create_session(db, user), []


def create_replacement_challenge(user_id: str, session_ids: set[str]) -> str:
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    key = session_token_hash(token)
    expires_at = utc_now() + timedelta(
        minutes=settings.session_replacement_challenge_minutes
    )
    with replacement_challenge_lock:
        now = utc_now()
        expired = [
            challenge_key
            for challenge_key, (_, expiry, _) in replacement_challenges.items()
            if expiry <= now
        ]
        for challenge_key in expired:
            replacement_challenges.pop(challenge_key, None)
        replacement_challenges[key] = (
            user_id,
            expires_at,
            frozenset(session_ids),
        )
    return token


def consume_replacement_challenge(
    token: str,
) -> tuple[str, frozenset[str]] | None:
    key = session_token_hash(token)
    with replacement_challenge_lock:
        challenge = replacement_challenges.pop(key, None)
    if challenge is None:
        return None
    user_id, expires_at, session_ids = challenge
    if expires_at <= utc_now():
        return None
    return user_id, session_ids


def replace_user_sessions(
    db: Session,
    user: User,
    expected_session_ids: frozenset[str],
) -> str | None:
    with login_session_lock:
        sessions = active_sessions(db, user.id)
        if frozenset(session.id for session in sessions) != expected_session_ids:
            return None
        settings = get_settings()
        token = secrets.token_urlsafe(32)
        now = utc_now()
        for session in sessions:
            session.revoked_at = now
        db.add(
            UserSession(
                id=session_token_hash(token),
                user_id=user.id,
                created_at=now,
                expires_at=now + timedelta(minutes=settings.session_ttl_minutes),
            )
        )
        db.commit()
        return token


def user_for_session(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    now = utc_now()
    session = db.get(UserSession, session_token_hash(token))
    if session is None or session.revoked_at is not None or as_utc(session.expires_at) <= now:
        return None
    return session.user


def revoke_session(db: Session, token: str | None) -> None:
    if not token:
        return
    session = db.get(UserSession, session_token_hash(token))
    if session is not None and session.revoked_at is None:
        session.revoked_at = utc_now()
        db.commit()
