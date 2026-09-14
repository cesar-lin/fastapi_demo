"""用户：数据库表模型 + 出入参模型"""
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "user"
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    is_admin: bool = False


class UserRegister(SQLModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=6)


class UserPublic(SQLModel):
    """对外视图：绝不包含密码哈希"""
    id: int
    username: str
    is_admin: bool
