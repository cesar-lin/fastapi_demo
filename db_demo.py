"""
db_demo.py — FastAPI + SQLModel 数据库集成示例

SQLModel = SQLAlchemy(ORM) + Pydantic(数据校验)，由 FastAPI 作者开发。

运行:  uvicorn db_demo:app --port 8002 --reload
文档:  http://127.0.0.1:8002/docs
数据库: SQLite 文件 demo.db（无需安装任何数据库服务）
"""
from contextlib import asynccontextmanager
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select

sqlite_url = "sqlite:///demo.db"          # 换 PostgreSQL 只需改成: postgresql://user:pass@host/db
engine = create_engine(sqlite_url, echo=True)  # echo=True 在终端打印生成的 SQL，便于学习


# ---------- 模型：一个类同时是「数据库表」和「Pydantic 模型」 ----------

class Hero(SQLModel, table=True):
    __tablename__ = "hero"
    id: Optional[int] = Field(default=None, primary_key=True)  # None = 数据库自增
    name: str = Field(index=True)          # index=True 建索引，加速按名字查询
    secret_name: str                       # 机密字段：对外永不返回
    age: Optional[int] = None


# 创建/更新/返回各用一个模型：控制哪些字段可写、哪些可见
class HeroCreate(SQLModel):
    name: str
    secret_name: str
    age: Optional[int] = None


class HeroPublic(SQLModel):
    """对外暴露的视图：故意不含 secret_name"""
    id: int
    name: str
    age: Optional[int] = None


class HeroUpdate(SQLModel):
    """更新模型：所有字段可选，实现部分更新（PATCH）"""
    name: Optional[str] = None
    secret_name: Optional[str] = None
    age: Optional[int] = None


# ---------- 应用启动时：建表 + 写入种子数据 ----------

@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)   # 按模型定义创建表（已存在则跳过）
    with Session(engine) as session:       # 空库时插入两条示例数据
        if not session.exec(select(Hero)).first():
            session.add(Hero(name="Spider-Boy", secret_name="Pedro Parqueador"))
            session.add(Hero(name="Rusty-Man", secret_name="Tommy Sharp", age=48))
            session.commit()
    yield

app = FastAPI(title="数据库集成 Demo", lifespan=lifespan)


# ---------- Session 依赖：上一课 yield 依赖的经典实战 ----------

def get_session():
    with Session(engine) as session:   # 前置：打开会话   收尾：自动关闭会话
        yield session

SessionDep = Annotated[Session, Depends(get_session)]   # 类型别名，接口里一行声明


# ---------- CRUD ----------

@app.post("/heroes/", response_model=HeroPublic, status_code=201)
def create_hero(hero: HeroCreate, session: SessionDep):
    db_hero = Hero.model_validate(hero)   # Pydantic 模型 -> 数据库模型
    session.add(db_hero)                  # 加入会话（ INSERT ）
    session.commit()                      # 提交事务，真正写入数据库
    session.refresh(db_hero)              # 取回数据库生成的自增 id
    return db_hero


@app.get("/heroes/", response_model=list[HeroPublic])
def read_heroes(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
):
    heroes = session.exec(select(Hero).offset(offset).limit(limit)).all()
    return heroes


@app.get("/heroes/{hero_id}", response_model=HeroPublic)
def read_hero(hero_id: int, session: SessionDep):
    hero = session.get(Hero, hero_id)     # 按主键查询
    if not hero:
        raise HTTPException(404, "英雄不存在")
    return hero


@app.patch("/heroes/{hero_id}", response_model=HeroPublic)
def update_hero(hero_id: int, hero: HeroUpdate, session: SessionDep):
    db_hero = session.get(Hero, hero_id)
    if not db_hero:
        raise HTTPException(404, "英雄不存在")
    update_data = hero.model_dump(exclude_unset=True)   # 只包含请求里实际提交的字段
    for key, value in update_data.items():
        setattr(db_hero, key, value)
    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)
    return db_hero


@app.delete("/heroes/{hero_id}")
def delete_hero(hero_id: int, session: SessionDep):
    hero = session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(404, "英雄不存在")
    session.delete(hero)
    session.commit()
    return {"ok": True}
