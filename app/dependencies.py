"""全局共享的依赖：数据库会话、公共参数、认证依赖链。

所有 router 从这里拿依赖，避免每个文件各写一份。
"""
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlmodel import Session, select

from .database import engine
from .models.user import User

SECRET_KEY = "change-me-in-production"   # 生产环境从环境变量读取，>= 32 字节随机值
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30

pwd = PasswordHash.recommended()   # argon2id 密码哈希


# ---------- 数据库会话（yield 依赖） ----------

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]


# ---------- 公共分页参数（多个 router 复用） ----------

def pagination_params(
    skip: int = Query(0, ge=0, description="跳过的数量"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
) -> dict:
    return {"skip": skip, "limit": limit}

PaginationDep = Annotated[dict, Depends(pagination_params)]


# ---------- 认证依赖链：token -> 当前用户 -> 管理员 ----------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDep,
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效或过期的登录凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exc
    except InvalidTokenError:
        raise credentials_exc
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise credentials_exc
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]

def require_admin(user: CurrentUser) -> User:
    """子依赖：在登录校验之上再叠管理员校验"""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user

AdminUser = Annotated[User, Depends(require_admin)]
