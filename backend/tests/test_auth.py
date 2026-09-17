from app.config import get_settings
from app.models import User
from app.security import set_session_cookie
from tests.conftest import make_user, signed_in_client


def test_sign_up_sets_session_cookie(client, db):
    response = client.post(
        "/api/auth/signup", json={"email": "New@Example.com", "password": "correct horse", "display_name": "Mere"}
    )
    assert response.status_code == 201, response.text
    assert response.json()["email"] == "new@example.com"
    assert response.json()["role"] == "student"
    assert "password_hash" not in response.json()
    cookie = response.headers["set-cookie"]
    assert "httponly" in cookie.lower()
    assert "samesite=lax" in cookie.lower()
    assert client.get("/api/me").json()["display_name"] == "Mere"


def test_password_is_hashed_with_argon2(client, db):
    client.post("/api/auth/signup", json={"email": "a@example.com", "password": "password123", "display_name": "A"})
    user = db.query(User).filter_by(email="a@example.com").one()
    assert user.password_hash.startswith("$argon2")


def test_duplicate_email(client, db):
    make_user(db, email="taken@example.com")
    response = client.post("/api/auth/signup", json={"email": "taken@example.com", "password": "password123", "display_name": "B"})
    assert response.status_code == 409


def test_short_password_rejected(client, db):
    response = client.post("/api/auth/signup", json={"email": "c@example.com", "password": "short", "display_name": "C"})
    assert response.status_code == 422


def test_sign_in_and_out(client, db):
    signed_in_client(client, db)
    assert client.get("/api/me").status_code == 200
    assert client.post("/api/auth/signout").status_code == 204
    client.cookies.clear()
    assert client.get("/api/me").status_code == 401


def test_wrong_password(client, db):
    make_user(db)
    response = client.post("/api/auth/signin", json={"email": "student@example.com", "password": "wrong-password"})
    assert response.status_code == 401


def test_tampered_token_rejected(client, db):
    make_user(db)
    client.cookies.set(get_settings().cookie_name, "not-a-real-token")
    assert client.get("/api/me").status_code == 401


def test_admin_routes_need_admin(client, db):
    signed_in_client(client, db)
    assert client.get("/api/admin/summary").status_code == 403


def test_admin_routes_need_sign_in(client, db):
    assert client.get("/api/admin/summary").status_code == 401


def test_admin_can_use_admin_routes(client, db):
    signed_in_client(client, db, email="boss@example.com", role="admin")
    assert client.get("/api/admin/summary").status_code == 200


def test_cookie_is_secure_when_configured(db, monkeypatch):
    from fastapi import Response

    monkeypatch.setattr(get_settings(), "cookie_secure", True)
    response = Response()
    set_session_cookie(response, make_user(db))
    assert "secure" in response.headers["set-cookie"].lower()


def test_health_checks_database(client):
    assert client.get("/api/health").json() == {"status": "ok", "database": "ok"}


def test_task_types_listed(client):
    types = client.get("/api/task-types").json()
    assert len(types) == 22
    assert types[0]["code"] == "RA"
    assert {t["section"] for t in types} == {"speaking_writing", "reading", "listening"}
