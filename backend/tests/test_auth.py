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
            assert client.get("/api/v1/auth/me").status_code == 401
    finally:
        app.dependency_overrides.clear()
