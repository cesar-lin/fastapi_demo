"""
depends_demo.py — FastAPI 依赖注入（Depends）示例

运行:  uvicorn depends_demo:app --port 8001 --reload
文档:  http://127.0.0.1:8001/docs
"""
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query

app = FastAPI(title="Depends 依赖注入 Demo")


# ===== 1. 最基本的依赖：一个普通函数 =====

def get_greeting() -> str:
    return "Hello from dependency!"

@app.get("/hello")
def hello(msg: Annotated[str, Depends(get_greeting)]):
    """FastAPI 先调用 get_greeting()，把返回值注入给参数 msg。"""
    return {"message": msg}


# ===== 2. 带参数的依赖 =====
# 依赖函数自己的参数（Query 等）也由 FastAPI 从请求中解析和校验。

def pagination_params(
    skip: int = Query(0, ge=0, description="跳过的数量"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
) -> dict:
    return {"skip": skip, "limit": limit}

@app.get("/users")
def list_users(
    page: Annotated[dict, Depends(pagination_params)],
    q: Optional[str] = Query(None, description="搜索关键字"),
):
    users = [{"id": i, "name": f"user{i}"} for i in range(1, 51)]
    if q:
        users = [u for u in users if q in u["name"]]
    return {"total": len(users), "items": users[page["skip"]: page["skip"] + page["limit"]]}


# ===== 3. 子依赖：依赖可以嵌套依赖 =====
# FastAPI 会自底向上依次解析依赖树。

def get_skip(skip: int = Query(0, ge=0)) -> int:
    return skip

def get_limit(limit: int = Query(10, ge=1, le=100)) -> int:
    return limit

def pagination(
    skip: Annotated[int, Depends(get_skip)],
    limit: Annotated[int, Depends(get_limit)],
) -> dict:
    return {"skip": skip, "limit": limit}

@app.get("/orders")
def list_orders(page: Annotated[dict, Depends(pagination)]):
    return {"page": page, "items": ["order-A", "order-B"]}


# ===== 4. 类作为依赖（适合可配置、有状态的依赖）=====
# 带 __call__ 的类：Depends(实例) 会把实例当函数调用。

class QueryChecker:
    def __init__(self, max_len: int):
        self.max_len = max_len

    def __call__(self, q: str = Query(..., description="搜索词")) -> str:
        if len(q) > self.max_len:
            raise HTTPException(422, f"q 太长，最多 {self.max_len} 个字符")
        return q

check_q = QueryChecker(max_len=5)

@app.get("/search")
def search(q: Annotated[str, Depends(check_q)]):
    return {"q": q}


# ===== 5. yield 依赖：前置准备 + 事后清理 =====
# yield 之前：请求处理前执行（如建立数据库连接）
# yield 之后：响应发送后执行，即使接口抛出异常也会执行（如关闭连接）

class FakeDBSession:
    def __init__(self):
        self.conn_id = id(self)

def get_db():
    db = FakeDBSession()      # 前置：建立连接
    try:
        yield db               # 把连接注入给接口函数
    finally:
        print(f"[teardown] 关闭连接 {db.conn_id}")   # 收尾：清理资源

@app.get("/db-test")
def db_test(db: Annotated[FakeDBSession, Depends(get_db)]):
    return {"db_conn": db.conn_id, "status": "连接使用中"}


# ===== 6. 全局/路由级依赖：dependencies=[...] =====
# 依赖在装饰器里声明，参数不注入给函数，只做前置校验（如鉴权）。

def verify_token(x_token: Annotated[str, Header(description="访问令牌")]):
    if x_token != "secret-token":
        raise HTTPException(status_code=401, detail="X-Token 无效")

@app.get("/admin", dependencies=[Depends(verify_token)])
def admin_panel():
    return {"message": "欢迎访问管理后台"}
