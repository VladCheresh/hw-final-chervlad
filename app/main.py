from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from .database import get_db, AsyncSessionLocal
import redis.asyncio as aioredis
from . import auth
from . import models
from . import schemas
from . import crud
import json
import os


app = FastAPI()
redis_client = None


async def get_redis():
    global redis_client
    if redis_client is None:
        redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
    return redis_client


@app.on_event("startup")
async def seed_admin():
    async with AsyncSessionLocal() as db:
        existing = await crud.get_account_by_username(db, "admin")
        if existing is None:
            await crud.create_admin_account(db,
                                            "admin",
                                            "admin@example.com",
                                            auth.hash_password("admin12345"))


@app.post('/register', status_code=201, response_model=schemas.AccountOut)
async def register(user: schemas.AccountRegister,
                   db: AsyncSession = Depends(get_db)
                   ):
    existing_user = await crud.get_account_by_username(db=db,
                                                       username=user.username)
    if existing_user is not None:
        raise HTTPException(status_code=409,
                            detail='User with this username already exists')
    existing_email = await crud.get_account_by_email(db=db, email=user.email)
    if existing_email:
        raise HTTPException(status_code=409,
                            detail='User with this email already exists')

    new_account = await crud.create_account(db=db,
                                            account=user,
                                            hashed_password=auth
                                            .hash_password(user.password))
    return new_account


@app.post('/login', response_model=schemas.Token)
async def log_in(credentials: schemas.AccountLogin,
                 db: AsyncSession = Depends(get_db)):
    user = await crud.get_account_by_username(username=credentials.username,
                                              db=db)
    if user is None:
        raise HTTPException(status_code=401, detail='Incorrect username')
    password = auth.verify_password(password=credentials.password,
                                    hashed=user.password)  # type:ignore
    if password is False:
        raise HTTPException(status_code=401,
                            detail='Password is incorrect')
    token = auth.create_access_token(data={'sub': user.username})
    return schemas.Token(access_token=token, token_type='bearer')


@app.get('/me', response_model=schemas.AccountOut)
async def current_account(
    current_user: models.Account = Depends(auth.get_current_user)
):
    return current_user


@app.get('/admin/stats')
async def view_admin_statistics(
    current_admin: models.Account = Depends(auth.require_admin),
    db: AsyncSession = Depends(get_db)
):
    return await crud.get_accounts_count(db=db)


@app.post('/projects', status_code=201, response_model=schemas.ProjectOut)
async def create_project(
    project: schemas.ProjectCreate,
    current_user: models.Account = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    new_project = await crud.create_project(
        db=db,
        project=project,
        owner_id=current_user.id)  # type:ignore
    await redis.delete('projects_list')
    return new_project


@app.get('/projects', status_code=200, response_model=List[schemas.ProjectOut])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: models.Account = Depends(auth.get_current_user),
    redis: aioredis.Redis = Depends(get_redis)
):
    cached = await redis.get('projects_list')
    if cached:
        return json.loads(cached)

    projects = await crud.get_projects(db=db)
    projects_data = [schemas.ProjectOut
                     .model_validate(p)
                     .model_dump() for p in projects]
    await redis.set('projects_list', json.dumps(projects_data), ex=60)
    return projects_data


@app.get('/projects/{id}', status_code=200, response_model=schemas.ProjectOut)
async def get_project(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.Account = Depends(auth.get_current_user)
):
    project = await crud.get_project(db=db, project_id=id)
    if project is None:
        raise HTTPException(status_code=404, detail='Project not found')
    return project


@app.put('/projects/{id}', response_model=schemas.ProjectOut)
async def update_project(
    id: int,
    project: schemas.ProjectUpdate,
    current_user: models.Account = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    existing_project = await crud.get_project(db=db, project_id=id)
    if existing_project is None:
        raise HTTPException(status_code=404, detail='Project not found')

    if existing_project.owner_id != current_user.id:  # type:ignore
        raise HTTPException(status_code=403,
                            detail='Denied: you are not owner of this project')

    project_to_update = await crud.update_project(db=db,
                                                  project_id=id,
                                                  project=project)
    await redis.delete('projects_list')
    return project_to_update


@app.delete('/projects/{id}', status_code=204)
async def delete_project(
    id: int,
    current_user: models.Account = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    project_to_delete = await crud.get_project(db=db, project_id=id)
    if project_to_delete is None:
        raise HTTPException(status_code=404, detail='Project not found')
    if project_to_delete.owner_id != current_user.id:  # type:ignore
        raise HTTPException(
            status_code=403,
            detail='Denied: you are not owner of this project'
            )

    await crud.delete_project(db=db, project_id=id)
    await redis.delete('projects_list')
    return None
