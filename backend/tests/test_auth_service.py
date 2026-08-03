from datetime import timedelta

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.db import Base
from app.db.models import User, UserSession, utc_now
from app.services.auth_service import (
    active_sessions,
    consume_replacement_challenge,
    create_replacement_challenge,
    create_session_if_available,
    hash_password,
    replace_user_sessions,
    replacement_challenge_lock,
    replacement_challenges,
    session_token_hash,
)


def sqlite_engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return engine


def test_only_one_active_session_is_created_and_replacement_revokes_it() -> None:
    engine = sqlite_engine()
    with Session(engine) as db:
        user = User(
            id="single-store",
            username="store",
            password_hash=hash_password("password"),
        )
        db.add(
            UserSession(
                id="expired",
                user=user,
                created_at=utc_now() - timedelta(hours=2),
                expires_at=utc_now() - timedelta(hours=1),
            )
        )
        db.commit()

        first_token, conflicts = create_session_if_available(db, user)
        assert first_token is not None
        assert conflicts == []

        second_token, conflicts = create_session_if_available(db, user)
        assert second_token is None
        assert len(conflicts) == 1

        replacement_token = replace_user_sessions(
            db,
            user,
            frozenset(session.id for session in conflicts),
        )
        assert replacement_token is not None
        assert replacement_token != first_token
        sessions = active_sessions(db, user.id)
        assert len(sessions) == 1
        assert sessions[0].id == session_token_hash(replacement_token)


def test_replacement_challenge_is_one_time_and_expiring() -> None:
    challenge = create_replacement_challenge("single-store", {"session-id"})
    assert consume_replacement_challenge(challenge) == (
        "single-store",
        frozenset({"session-id"}),
    )
    assert consume_replacement_challenge(challenge) is None

    expired = create_replacement_challenge("single-store", {"session-id"})
    key = session_token_hash(expired)
    with replacement_challenge_lock:
        replacement_challenges[key] = (
            "single-store",
            utc_now() - timedelta(seconds=1),
            frozenset({"session-id"}),
        )
    assert consume_replacement_challenge(expired) is None
