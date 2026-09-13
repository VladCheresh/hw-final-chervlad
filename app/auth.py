from passlib.context import CryptContext  # type: ignore
from jose import jwt, JWTError  # type: ignore
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from . import models
from .database import get_db
from . import crud


pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

SECRET_KEY = 'your-secret-key-here'
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(data: dict, expires_delta=None):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_delta or
                                           ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


security = HTTPBearer()


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')  # type: ignore
        if username is None:
            raise HTTPException(status_code=401,
                                detail='Invalid token payload')
    except JWTError:
        raise HTTPException(status_code=401, detail='Invalid or expired token')

    account = await crud.get_account_by_username(db, username)
    if account is None:
        raise HTTPException(status_code=401, detail='User not found')
    return account


async def require_admin(possible_admin:
                        models.Account = Depends(get_current_user)):
    if possible_admin.role != 'admin':  # type: ignore
        raise HTTPException(status_code=403, detail='Admin access required')
    return possible_admin
