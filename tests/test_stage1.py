import pytest

from app.extensions import db
from app.models import User
from app.seed import seed_all

GOOD = {"username": "sara_k", "email": "sara@example.com", "password": "Passw0rdX", "confirm": "Passw0rdX"}


@pytest.fixture()
def client(app):
    seed_all()
    return app.test_client()


def register(client, **overrides):
    return client.post("/auth/register", data={**GOOD, **overrides})


def test_seed_is_idempotent_and_loads_data(app):
    seed_all()
    seed_all()
    from app.models import Subject, Topic

    assert Subject.query.count() == 2
    assert Topic.query.count() > 10
    assert User.query.filter_by(username="admin").one().has_role("admin")


def test_register_uses_post_redirect_get(client):
    resp = register(client)
    assert resp.status_code == 302 and resp.headers["Location"].endswith("/auth/login")
    assert "Account created" in client.get("/auth/login").get_data(as_text=True)
    assert User.query.filter_by(username="sara_k").one().has_role("student")


@pytest.mark.parametrize("overrides,message", [
    ({"password": "short1", "confirm": "short1"}, "between 8 and 128"),
    ({"password": "onlyletters", "confirm": "onlyletters"}, "one letter and one number"),
    ({"confirm": "different1A"}, "must match"),
    ({"username": "admin"}, "already taken"),
    ({"email": "not-an-email"}, "email"),
])
def test_register_server_side_validation(client, overrides, message):
    resp = register(client, **overrides)
    assert resp.status_code == 200 and message in resp.get_data(as_text=True)


def test_login_logout_and_session_cookie(client):
    bad = client.post("/auth/login", data={"identifier": "admin", "password": "nope"})
    assert "Invalid username or password" in bad.get_data(as_text=True)
    ok = client.post("/auth/login", data={"identifier": "admin", "password": "Demo#12345", "remember": "y"})
    assert ok.status_code == 302
    with client.session_transaction() as sess:
        assert sess["user_id"] and sess.permanent
    assert "admin" in client.get("/").get_data(as_text=True)
    client.post("/auth/logout")
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_open_redirect_is_blocked(client):
    resp = client.post("/auth/login?next=//evil.com", data={"identifier": "admin", "password": "Demo#12345"})
    assert resp.headers["Location"].endswith("/")


def test_subject_pages_render_and_404(client):
    from app.models import Subject

    physics = Subject.query.filter_by(code="5054").one()
    page = client.get(f"/subjects/{physics.id}").get_data(as_text=True)
    assert "Motion, forces and energy" in page and "Paper 1" in page
    assert client.get("/subjects").status_code == 200
    assert client.get("/subjects/9999").status_code == 404
