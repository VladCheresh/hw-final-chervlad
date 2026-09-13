from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import declarative_base
import os


DATABASE_URL = os.getenv('DATABASE_URL',
                         'postgresql+asyncpg:'
                         '//postgres:postgres@db:5432/hw_final_chervlad')

engine = create_async_engine(DATABASE_URL, echo=False, future=True)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
