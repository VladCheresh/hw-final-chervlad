from . import models
from . import schemas
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_projects(db: AsyncSession):
    result = await db.execute(select(models.Project))
    projects = result.scalars().all()
    return projects


async def get_project(db: AsyncSession, project_id: int):
    result = await db.execute(select(models.Project)
                              .where(models.Project.id == project_id))
    project = result.scalar_one_or_none()
    return project


async def create_project(db: AsyncSession,
                         project: schemas.ProjectCreate,
                         owner_id: int):
    new_project = models.Project(**project.dict(), owner_id=owner_id)
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    return new_project


async def update_project(db: AsyncSession,
                         project_id: int,
                         project: schemas.ProjectUpdate):
    result = await db.execute(select(models.Project)
                              .where(models.Project.id == project_id))
    project_to_update = result.scalar_one_or_none()
    if project_to_update is None:
        return None

    project_to_update.name = project.name  # type:ignore
    project_to_update.description = project.description  # type:ignore
    db.add(project_to_update)
    await db.commit()
    await db.refresh(project_to_update)
    return project_to_update


async def delete_project(db: AsyncSession, project_id: int):
    result = await db.execute(select(models.Project)
                              .where(models.Project.id == project_id))
    project_to_delete = result.scalar_one_or_none()
    if project_to_delete is None:
        return None

    await db.delete(project_to_delete)
    await db.commit()
    return project_to_delete


async def get_account_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(models.Account)
                              .where(models.Account.username == username))
    return result.scalar_one_or_none()


async def get_account_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.Account)
                              .where(models.Account.email == email))
    return result.scalar_one_or_none()


async def create_account(db: AsyncSession, account: schemas.AccountRegister,
                         hashed_password: str):
    new_account = models.Account(
        username=account.username,
        email=account.email,
        password=hashed_password,
        role="user"
    )
    db.add(new_account)
    await db.commit()
    await db.refresh(new_account)
    return new_account


async def create_admin_account(db: AsyncSession,
                               username: str,
                               email: str,
                               hashed_password: str):
    new_account = models.Account(username=username,
                                 email=email,
                                 password=hashed_password, role="admin")
    db.add(new_account)
    await db.commit()
    await db.refresh(new_account)
    return new_account


async def get_accounts_count(db: AsyncSession):
    result = await db.execute(select(models.Account))
    all_accounts = result.scalars().all()

    return ({
        'Всего зарегистрированных аккаунтов': len(all_accounts),
        'Всего обычных пользователей': sum(1 for a in all_accounts
                                           if a.role == 'user'),  # type:ignore
        'Всего админ-аккаунтов': sum(1 for a in all_accounts
                                     if a.role == 'admin'),  # type:ignore
    })
