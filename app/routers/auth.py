"""认证路由：注册 / 登录 / 个人信息 / 管理员专区"""
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select

from ..dependencies import (
    ALGORITHM,
    SECRET_KEY,
    TOKEN_EXPIRE_MINUTES,
    AdminUser,
    CurrentUser,
    SessionDep,
    pwd,
)
from ..models.user import User, UserRegister, UserPublic
from ..schemas.token import Token

router = APIRouter(prefix="/auth", tags=["认证"])


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/register", response_model=UserPublic, status_code=201)
def register(body: UserRegister, session: SessionDep):
    if session.exec(select(User).where(User.username == body.username)).first():
        raise HTTPException(status_code=409, detail="用户名已被注册")
    user = User(username=body.username, hashed_password=pwd.hash(body.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep):
    user = session.exec(select(User).where(User.username == form.username)).first()
    if not user or not pwd.verify(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return Token(access_token=create_access_token(user.username), token_type="bearer")


@router.get("/me", response_model=UserPublic)
def read_me(user: CurrentUser):
    return user


@router.get("/admin")
def admin_area(user: AdminUser):
    return {"message": f"你好，管理员 {user.username}！"}
