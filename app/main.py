"""应用入口：创建 FastAPI 实例、挂载所有 router、初始化数据"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session, select

from .database import create_db_and_tables, engine
from .dependencies import pwd
from .models.hero import Hero
from .models.user import User
from .routers import auth, heroes, items


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    with Session(engine) as session:
        # 预置管理员账号
        if not session.exec(select(User).where(User.username == "admin")).first():
            session.add(User(username="admin",
                             hashed_password=pwd.hash("admin123"),
                             is_admin=True))
        # 预置示例英雄
        if not session.exec(select(Hero)).first():
            session.add(Hero(name="Spider-Boy", secret_name="Pedro Parqueador"))
            session.add(Hero(name="Rusty-Man", secret_name="Tommy Sharp", age=48))
        session.commit()
    yield


app = FastAPI(title="FastAPI 整合项目", lifespan=lifespan)

app.include_router(items.router)
app.include_router(heroes.router)
app.include_router(auth.router)


@app.get("/")
def read_root():
    return {"message": "整合项目运行中", "docs": "/docs"}
