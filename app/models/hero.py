"""英雄：数据库表模型 + 出入参模型"""
from typing import Optional

from sqlmodel import Field, SQLModel


class Hero(SQLModel, table=True):
    __tablename__ = "hero"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    secret_name: str
    age: Optional[int] = None


class HeroCreate(SQLModel):
    name: str
    secret_name: str
    age: Optional[int] = None


class HeroPublic(SQLModel):
    """对外视图：不含 secret_name"""
    id: int
    name: str
    age: Optional[int] = None


class HeroUpdate(SQLModel):
    """全可选字段，配合 exclude_unset 实现部分更新"""
    name: Optional[str] = None
    secret_name: Optional[str] = None
    age: Optional[int] = None
