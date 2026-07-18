from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from modules.auth.domain import RoleName


class CredentialsRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class CurrentAccount(BaseModel):
    id: UUID
    email: str
    status: Literal["active"]


class AdminAccount(CurrentAccount):
    display_name: str
    roles: list[RoleName]


class AuthenticatedAccount(BaseModel):
    account: CurrentAccount
    session_token: str
