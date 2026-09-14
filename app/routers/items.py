"""商品路由：基础 CRUD（内存存储），演示公共分页依赖的复用"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..dependencies import PaginationDep
from ..schemas.item import Item, ItemResponse

router = APIRouter(prefix="/items", tags=["商品"])

fake_db: dict[int, dict] = {}
_id_counter = 0


@router.post("/", response_model=ItemResponse, status_code=201)
def create_item(item: Item, importance: int = Query(1, ge=1, le=5)):
    global _id_counter
    _id_counter += 1
    stored = item.model_dump()
    stored["importance"] = importance
    fake_db[_id_counter] = stored
    return ItemResponse(name=item.name, price_with_tax=item.price + (item.tax or 0))


@router.get("/")
def list_items(page: PaginationDep, q: Optional[str] = Query(None, description="按名称搜索")):
    items = list(fake_db.values())
    if q:
        items = [i for i in items if q in i["name"]]
    return {"total": len(items), "items": items[page["skip"]: page["skip"] + page["limit"]]}


@router.get("/{item_id}")
def read_item(item_id: int):
    if item_id not in fake_db:
        raise HTTPException(404, "商品不存在")
    return {"item_id": item_id, **fake_db[item_id]}


@router.delete("/{item_id}")
def delete_item(item_id: int):
    if item_id not in fake_db:
        raise HTTPException(404, "商品不存在")
    del fake_db[item_id]
    return {"message": f"商品 {item_id} 已删除"}
