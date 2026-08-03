from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.db.models import User, UserSession
from app.db.session import get_db
from app.main import app
from app.services.auth_service import hash_password, session_token_hash


def test_password_hash_and_server_session_cookie() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        password_hash = hash_password("a-secure-test-password")
        assert "a-secure-test-password" not in password_hash
        db.add(User(id="single-store", username="store", password_hash=password_hash))
        db.commit()

    def override_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/images/assets").status_code == 401
            failed = client.post(
                "/api/v1/auth/login",
                json={"username": "store", "password": "wrong-password"},
            )
            assert failed.status_code == 401
            assert failed.json() == {
                "detail": {
                    "code": "invalid_credentials",
                    "message": "帳號或密碼錯誤。",
                }
            }
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "store", "password": "a-secure-test-password"},
            )
            assert response.status_code == 200
            token = client.cookies.get("totem_session")
            assert token
            assert "HttpOnly" in response.headers["set-cookie"]
            assert client.get("/api/v1/auth/me").json()["username"] == "store"
            assert client.get("/api/v1/images/assets").status_code == 200

            with Session(engine) as db:
                stored_session = db.scalar(select(UserSession))
                assert stored_session is not None
                assert stored_session.id == session_token_hash(token)
                assert stored_session.id != token

            assert client.post("/api/v1/auth/logout").status_code == 204
            unauthorized = client.get("/api/v1/auth/me")
            assert unauthorized.status_code == 401
            assert unauthorized.json() == {
                "detail": {
                    "code": "authentication_required",
                    "message": "請先登入後再繼續操作。",
                }
            }
    finally:
        app.dependency_overrides.clear()


def test_active_session_requires_explicit_one_time_replacement() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(
            id="single-store",
            username="store",
            password_hash=hash_password("a-secure-test-password"),
        )
        db.add_all(
            [
                user,
                UserSession(
                    id="expired-session",
                    user=user,
                    created_at=datetime.now(timezone.utc) - timedelta(hours=2),
                    expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
                ),
            ]
        )
        db.commit()

    def override_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as first, TestClient(app) as second:
            credentials = {
                "username": "store",
                "password": "a-secure-test-password",
            }
            assert first.post("/api/v1/auth/login", json=credentials).status_code == 200

            wrong = second.post(
                "/api/v1/auth/login",
                json={"username": "store", "password": "wrong-password"},
            )
            assert wrong.status_code == 401
            assert wrong.json()["detail"]["code"] == "invalid_credentials"

            conflict = second.post("/api/v1/auth/login", json=credentials)
            assert conflict.status_code == 409
            detail = conflict.json()["detail"]
            assert detail["code"] == "session_already_active"
            assert detail["challenge"]

            # Merely receiving or cancelling the prompt does not affect the old login.
            assert first.get("/api/v1/auth/me").status_code == 200
            assert second.get("/api/v1/auth/me").status_code == 401

            replaced = second.post(
                "/api/v1/auth/login/replace",
                json={"challenge": detail["challenge"]},
            )
            assert replaced.status_code == 200
            assert second.get("/api/v1/auth/me").status_code == 200
            assert first.get("/api/v1/auth/me").status_code == 401

            replay = first.post(
                "/api/v1/auth/login/replace",
                json={"challenge": detail["challenge"]},
            )
            assert replay.status_code == 409
            assert replay.json()["detail"]["code"] == "invalid_replacement_challenge"
            assert second.get("/api/v1/auth/me").status_code == 200
    finally:
        app.dependency_overrides.clear()
