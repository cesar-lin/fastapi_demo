from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Path
from pydantic import BaseModel, Field

app = FastAPI(
    title="FastAPI Demo",
    description="一个用于学习 FastAPI 基本概念的示例项目",
    version="0.1.0",
)


# ---------- Pydantic 模型（定义请求体 / 响应体的数据结构） ----------

class Item(BaseModel):
    name: str = Field(..., example="手机", description="商品名称")
    description: Optional[str] = Field(None, example="一部新手机")
    price: float = Field(..., gt=0, example=5999.0, description="价格，必须大于 0")
    tax: Optional[float] = Field(None, example=100.0)


class ItemResponse(BaseModel):
    name: str
    price_with_tax: float


# 模拟数据库
fake_db: dict[int, dict] = {}
_id_counter = 0


# ---------- 1. 最基本的 GET 路由 ----------

@app.get("/")
def read_root():
    return {"message": "Hello FastAPI!"}


# ---------- 2. 路径参数（path parameter）----------

@app.get("/items/{item_id}")
def read_item(item_id: int):  # 声明为 int，FastAPI 会自动做类型校验和转换
    if item_id not in fake_db:
        raise HTTPException(status_code=404, detail="商品不存在")
    return {"item_id": item_id, **fake_db[item_id]}


# ---------- 3. 查询参数（query parameter）----------

@app.get("/items/")
def list_items(
    q: Optional[str] = Query(None, max_length=50, description="按名称搜索"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
    skip: int = Query(0, ge=0, description="跳过的数量"),
):
    items = list(fake_db.values())
    if q:
        items = [i for i in items if q in i["name"]]
    return {"total": len(items), "items": items[skip : skip + limit]}


# ---------- 4. 请求体（request body）+ 路径参数 + 查询参数混合 ----------

@app.post("/items/", response_model=ItemResponse, status_code=201)
def create_item(item: Item, importance: int = Query(1, ge=1, le=5)):
    global _id_counter
    _id_counter += 1
    stored = item.model_dump()
    stored["importance"] = importance
    fake_db[_id_counter] = stored
    return ItemResponse(
        name=item.name,
        price_with_tax=item.price + (item.tax or 0),
    )


# ---------- 5. PUT 更新 ----------

@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    if item_id not in fake_db:
        raise HTTPException(status_code=404, detail="商品不存在")
    fake_db[item_id] = item.model_dump()
    return {"item_id": item_id, **fake_db[item_id]}


# ---------- 6. DELETE 删除 ----------

@app.delete("/items/{item_id}")
def delete_item(item_id: int = Path(..., ge=1, description="商品 ID")):
    if item_id not in fake_db:
        raise HTTPException(status_code=404, detail="商品不存在")
    del fake_db[item_id]
    return {"message": f"商品 {item_id} 已删除"}
