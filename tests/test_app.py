"""整合项目的单元测试（TDD：测试即行为的定义）

设计要点：
- 测试数据库与开发库完全隔离：内存 SQLite，每个用例独立建表/清表
- 用 dependency_overrides 把 get_session 换成测试会话
- items 的内存 fake_db 每个用例重置，保证用例间互不影响

运行: pytest -v
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.dependencies import get_session, pwd
from app.main import app
from app.models.user import User
from app.routers import items as items_router

# 测试专用内存数据库（StaticPool 保证整个测试进程共用同一连接）
test_engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    # items 的内存存储重置（注意 _id_counter 也要归零）
    items_router.fake_db.clear()
    items_router._id_counter = 0

    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    yield TestClient(app)
    app.dependency_overrides.clear()


def register_and_login(client: TestClient, username="alice", password="secret123"):
    client.post("/auth/register", json={"username": username, "password": password})
    r = client.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def make_admin(session: Session, username="admin"):
    session.add(
        User(username=username, hashed_password=pwd.hash("admin123"), is_admin=True)
    )
    session.commit()


# ==================== items（公开接口） ====================

def test_create_item(client):
    r = client.post("/items/?importance=2", json={"name": "键盘", "price": 299.0})
    assert r.status_code == 201
    # 响应模型只暴露 name 和 price_with_tax
    assert r.json() == {"name": "键盘", "price_with_tax": 299.0}


def test_create_item_price_must_be_positive(client):
    r = client.post("/items/", json={"name": "x", "price": -1})
    assert r.status_code == 422


def test_list_items_with_pagination(client):
    for i in range(3):
        client.post("/items/", json={"name": f"商品{i}", "price": 10.0})
    r = client.get("/items/?skip=1&limit=1")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert len(data["items"]) == 1


def test_read_item(client):
    client.post("/items/", json={"name": "键盘", "price": 299.0})
    r = client.get("/items/1")
    assert r.status_code == 200
    assert r.json()["name"] == "键盘"


def test_read_item_not_found(client):
    assert client.get("/items/999").status_code == 404


def test_delete_item(client):
    client.post("/items/", json={"name": "键盘", "price": 299.0})
    assert client.delete("/items/1").status_code == 200
    assert client.get("/items/1").status_code == 404


# ==================== heroes（三种保护级别） ====================

def test_read_heroes_is_public(client):
    assert client.get("/heroes/").status_code == 200


def test_create_hero_requires_login(client):
    r = client.post("/heroes/", json={"name": "D", "secret_name": "s"})
    assert r.status_code == 401


def test_create_hero_with_login_hides_secret_name(client):
    headers = register_and_login(client)
    r = client.post(
        "/heroes/",
        json={"name": "Deadpond", "secret_name": "Dive Wilson", "age": 25},
        headers=headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Deadpond"
    assert "secret_name" not in body


def test_read_hero(client):
    headers = register_and_login(client)
    client.post("/heroes/", json={"name": "D", "secret_name": "s"}, headers=headers)
    r = client.get("/heroes/1")
    assert r.status_code == 200
    assert r.json()["name"] == "D"


def test_read_hero_not_found(client):
    assert client.get("/heroes/999").status_code == 404


def test_patch_hero_partial_update(client):
    headers = register_and_login(client)
    client.post(
        "/heroes/",
        json={"name": "D", "secret_name": "s", "age": 25},
        headers=headers,
    )
    r = client.patch("/heroes/1", json={"age": 30})
    assert r.status_code == 200
    assert r.json()["age"] == 30
    assert r.json()["name"] == "D"   # 未提交的字段保持不变


def test_delete_hero_forbidden_for_normal_user(client):
    headers = register_and_login(client)
    client.post("/heroes/", json={"name": "D", "secret_name": "s"}, headers=headers)
    assert client.delete("/heroes/1", headers=headers).status_code == 403


def test_delete_hero_as_admin(client, session):
    headers = register_and_login(client)
    client.post("/heroes/", json={"name": "D", "secret_name": "s"}, headers=headers)
    make_admin(session)
    r = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    admin_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.delete("/heroes/1", headers=admin_headers).status_code == 200
    assert client.get("/heroes/1").status_code == 404


def test_delete_hero_not_found_as_admin(client, session):
    make_admin(session)
    r = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    admin_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.delete("/heroes/999", headers=admin_headers).status_code == 404


# ==================== auth ====================

def test_register(client):
    r = client.post(
        "/auth/register", json={"username": "alice", "password": "secret123"}
    )
    assert r.status_code == 201
    assert r.json() == {"id": 1, "username": "alice", "is_admin": False}
    assert "hashed_password" not in r.json()


def test_register_duplicate_username(client):
    client.post("/auth/register", json={"username": "alice", "password": "secret123"})
    r = client.post(
        "/auth/register", json={"username": "alice", "password": "secret123"}
    )
    assert r.status_code == 409


def test_register_password_too_short(client):
    r = client.post("/auth/register", json={"username": "bob", "password": "123"})
    assert r.status_code == 422


def test_login_wrong_password(client):
    client.post("/auth/register", json={"username": "alice", "password": "secret123"})
    r = client.post("/auth/login", data={"username": "alice", "password": "wrong"})
    assert r.status_code == 401


def test_login_success_returns_bearer_token(client):
    client.post("/auth/register", json={"username": "alice", "password": "secret123"})
    r = client.post("/auth/login", data={"username": "alice", "password": "secret123"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_rejects_invalid_token(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401


def test_me_returns_current_user(client):
    headers = register_and_login(client)
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["username"] == "alice"


def test_admin_requires_admin_role(client):
    headers = register_and_login(client)
    assert client.get("/auth/admin", headers=headers).status_code == 403


def test_admin_success(client, session):
    make_admin(session)
    r = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = client.get("/auth/admin", headers=headers)
    assert r.status_code == 200
    assert "admin" in r.json()["message"]
