from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import manage_user
from app.db.base import Base
from app.db.models import User, UserSession, utc_now
from app.services.auth_service import session_token_hash, verify_password


def test_reset_password_updates_hash_and_revokes_sessions(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, expire_on_commit=False)

    with test_session() as db:
        user = User(username="owner", password_hash=manage_user.hash_password("old-password-123"))
        db.add(user)
        db.flush()
        db.add(
            UserSession(
                id=session_token_hash("active-token"),
                user_id=user.id,
                expires_at=utc_now(),
            )
        )
        db.commit()

    answers = iter(["owner"])
    passwords = iter(["new-password-123", "new-password-123"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr(manage_user, "getpass", lambda _prompt: next(passwords))
    monkeypatch.setattr(manage_user, "SessionLocal", test_session)

    manage_user.reset_single_user_password()

    with test_session() as db:
        user = db.scalar(select(User))
        assert user is not None
        assert verify_password(user.password_hash, "new-password-123")
        assert not verify_password(user.password_hash, "old-password-123")
        assert list(db.scalars(select(UserSession)).all()) == []
