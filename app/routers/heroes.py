"""英雄路由：数据库 CRUD，演示认证依赖跨 router 复用"""
from fastapi import APIRouter, HTTPException
from sqlmodel import select

from ..dependencies import AdminUser, CurrentUser, PaginationDep, SessionDep
from ..models.hero import Hero, HeroCreate, HeroPublic, HeroUpdate

router = APIRouter(prefix="/heroes", tags=["英雄"])


@router.post("/", response_model=HeroPublic, status_code=201)
def create_hero(hero: HeroCreate, session: SessionDep, user: CurrentUser):
    """创建英雄需要登录——认证依赖在任何 router 里都能直接用"""
    db_hero = Hero.model_validate(hero)
    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)
    return db_hero


@router.get("/", response_model=list[HeroPublic])
def read_heroes(session: SessionDep, page: PaginationDep):
    heroes = session.exec(select(Hero).offset(page["skip"]).limit(page["limit"])).all()
    return heroes


@router.get("/{hero_id}", response_model=HeroPublic)
def read_hero(hero_id: int, session: SessionDep):
    hero = session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(404, "英雄不存在")
    return hero


@router.patch("/{hero_id}", response_model=HeroPublic)
def update_hero(hero_id: int, hero: HeroUpdate, session: SessionDep):
    db_hero = session.get(Hero, hero_id)
    if not db_hero:
        raise HTTPException(404, "英雄不存在")
    update_data = hero.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_hero, key, value)
    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)
    return db_hero


@router.delete("/{hero_id}")
def delete_hero(hero_id: int, session: SessionDep, user: AdminUser):
    """删除英雄需要管理员——依赖链 require_admin 直接复用"""
    hero = session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(404, "英雄不存在")
    session.delete(hero)
    session.commit()
    return {"ok": True}
