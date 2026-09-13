"""
auth_demo.py — JWT 用户认证示例（综合前三课：FastAPI 基础 + Depends + SQLModel）

流程:  注册(密码哈希存储) → 登录(校验密码, 签发 JWT) → 携带 JWT 访问受保护接口

运行:  uvicorn auth_demo:app --port 8003 --reload
文档:  http://127.0.0.1:8003/docs  （点右上角 Authorize 按钮可直接在文档里登录测试）
"""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select

SECRET_KEY = "change-me-in-production"   # 生产环境务必从环境变量读取！
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30

engine = create_engine("sqlite:///auth.db")
pwd = PasswordHash.recommended()         # 默认 argon2id，自动加盐的慢哈希


# ---------- 数据模型 ----------

class User(SQLModel, table=True):
    __tablename__ = "user"
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str                 # 永远只存哈希，不存明文密码
    is_admin: bool = False

class UserRegister(SQLModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=6)

class UserPublic(SQLModel):
    """对外用户信息：绝不包含密码哈希"""
    id: int
    username: str
    is_admin: bool

class Token(BaseModel):
    access_token: str
    token_type: str


# ---------- 启动：建表 + 预置一个管理员 ----------

@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        if not session.exec(select(User).where(User.username == "admin")).first():
            session.add(User(username="admin",
                             hashed_password=pwd.hash("admin123"),
                             is_admin=True))
            session.commit()
    yield

app = FastAPI(title="JWT 认证 Demo", lifespan=lifespan)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]


# ---------- 工具函数 ----------

def create_access_token(username: str) -> str:
    """签发 JWT: {'sub': 用户名, 'exp': 过期时间}"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


# ---------- 认证依赖（本次的核心）----------
# OAuth2PasswordBearer 两件事：
# 1. 告诉 Swagger 文档: 去 "auth/login" 拿 token（文档页出现 Authorize 按钮）
# 2. 从请求头 Authorization: Bearer <token> 中取出 token 注入给函数

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDep,
) -> User:
    """解析 token -> 查库 -> 返回当前登录用户；任何环节失败都返回 401"""
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
    except InvalidTokenError:          # 签名错误、过期等一律 401
        raise credentials_exc
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise credentials_exc
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]   # 受保护接口一行声明

def require_admin(user: CurrentUser) -> User:
    """子依赖：在 get_current_user 之上再叠一层管理员校验"""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user

AdminUser = Annotated[User, Depends(require_admin)]


# ---------- 接口 ----------

@app.post("/auth/register", response_model=UserPublic, status_code=201)
def register(body: UserRegister, session: SessionDep):
    if session.exec(select(User).where(User.username == body.username)).first():
        raise HTTPException(status_code=409, detail="用户名已被注册")
    user = User(username=body.username, hashed_password=pwd.hash(body.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@app.post("/auth/login", response_model=Token)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
):
    """OAuth2 标准登录：接收 form 表单（username + password），返回 Bearer token"""
    user = session.exec(select(User).where(User.username == form.username)).first()
    if not user or not pwd.verify(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return Token(access_token=create_access_token(user.username), token_type="bearer")


@app.get("/users/me", response_model=UserPublic)
def read_me(user: CurrentUser):
    """登录用户可见自己的信息"""
    return user


@app.get("/admin")
def admin_area(user: AdminUser):
    """仅管理员可见"""
    return {"message": f"你好，管理员 {user.username}！"}
