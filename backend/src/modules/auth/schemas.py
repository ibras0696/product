from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CredentialsRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class CurrentAccount(BaseModel):
    id: UUID
    email: str
    status: Literal["active"]


class AuthenticatedAccount(BaseModel):
    account: CurrentAccount
    session_token: str
