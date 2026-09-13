from pydantic import BaseModel


class Account(BaseModel):
    username: str
    password: str
    role: str
    email: str


class AccountRegister(BaseModel):
    username: str
    email: str
    password: str


class AccountLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AccountOut(BaseModel):
    id: int
    username: str
    email: str
    role: str


class ProjectCreate(BaseModel):
    name: str
    description: str


class ProjectUpdate(BaseModel):
    name: str
    description: str


class ProjectOut(BaseModel):
    id: int
    name: str
    description: str
    owner_id: int

    model_config = {'from_attributes': True}
