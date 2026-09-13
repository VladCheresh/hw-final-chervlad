import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app, get_db
from app.database import Base
from app import main as main_module

TEST_DATABASE_URL = (
    "postgresql+asyncpg://"
    "postgres:postgres@test-db:5432/test_db"
)
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app),
                           base_url="http://test",) as ac:
        yield ac


@pytest.fixture(autouse=True)
async def reset_redis():
    yield
    if main_module.redis_client is not None:
        await main_module.redis_client.aclose()
        main_module.redis_client = None


@pytest.fixture
async def authorized_user(client):
    register_response = await client.post("/register", json={
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "testpassword123"
    })
    register_data = register_response.json()

    login_response = await client.post("/login", json={
        "username": register_data["username"],
        "password": "testpassword123"
    })
    login_data = login_response.json()
    headers = {"Authorization": f"Bearer {login_data['access_token']}"}

    me_response = await client.get("/me", headers=headers)
    me_data = me_response.json()

    return {"headers": headers, "user_id": me_data["id"]}


@pytest.mark.asyncio
async def test_register(client):
    response = await client.post("/register", json={
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "testpassword123"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "testuser@example.com"
    assert "password" not in data


@pytest.mark.asyncio
async def test_login(client):
    register_response = await client.post("/register", json={
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "testpassword123"
    })
    data = register_response.json()
    response = await client.post("/login", json={
        "username": data["username"],
        "password": "testpassword123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_create_project(client, authorized_user):
    response = await client.post("/projects", json={
        "name": "testproject",
        "description": "testdescription"
    }, headers=authorized_user["headers"])
    assert response.status_code == 201
    data = response.json()
    assert data["owner_id"] == authorized_user["user_id"]


@pytest.mark.asyncio
async def test_update_project(client, authorized_user):
    create_response = await client.post("/projects", json={
        "name": "testproject",
        "description": "testdescription"
    }, headers=authorized_user["headers"])
    project_id = create_response.json()["id"]

    response = await client.put(f"/projects/{project_id}", json={
        "name": "updated project",
        "description": "updated description"
    }, headers=authorized_user["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "updated project"


@pytest.mark.asyncio
async def test_update_project_not_owner(client, authorized_user):
    create_response = await client.post("/projects", json={
        "name": "testproject",
        "description": "testdescription"
    }, headers=authorized_user["headers"])
    project_id = create_response.json()["id"]

    await client.post("/register", json={
        "username": "otheruser",
        "email": "other@example.com",
        "password": "otherpassword123"
    })
    other_login = await client.post("/login", json={
        "username": "otheruser",
        "password": "otherpassword123"
    })
    other_token = other_login.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    response = await client.put(f"/projects/{project_id}", json={
        "name": "hacked",
        "description": "hacked description"
    }, headers=other_headers)
    assert response.status_code == 403
