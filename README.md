# FastAPI 学习项目

一个渐进式的 FastAPI 学习项目，包含 4 个独立可运行的 demo，按学习顺序排列：

| 课程 | 文件 | 端口 | 内容 |
|---|---|---|---|
| 第一课 | `main.py` | 8000 | FastAPI 基础：路由、参数、Pydantic 模型 |
| 第二课 | `depends_demo.py` | 8001 | 依赖注入（Depends）的 6 种典型用法 |
| 第三课 | `db_demo.py` | 8002 | 数据库集成（SQLModel + SQLite）完整 CRUD |
| 第四课 | `auth_demo.py` | 8003 | JWT 用户认证（综合前三课） |

## 快速开始

```bash
git clone <你的仓库地址>
cd fastapi_demo

python3 -m venv .venv
source .venv/bin/activate      # Windows 用 .venv\Scripts\activate

pip install -r requirements.txt
```

分别运行各课程 demo：

```bash
uvicorn main:app --reload --port 8000
uvicorn depends_demo:app --reload --port 8001
uvicorn db_demo:app --reload --port 8002
uvicorn auth_demo:app --reload --port 8003
```

每个 demo 启动后访问 `/docs` 都有自动生成的交互式文档（Swagger UI），可以直接在页面里调试接口。

---

## 第一课：FastAPI 基础（`main.py`）

**核心思想**：利用 Python 类型注解做数据校验和自动文档，代码即文档。

- **路径操作装饰器**：`@app.get("/")`、`@app.post(...)` 等注册路由，对应 HTTP 方法
- **路径参数**：`@app.get("/items/{item_id}")` + `def read_item(item_id: int)`，声明 `int` 即自动校验类型，传入 `abc` 自动返回 422
- **查询参数**：普通函数参数自动变成 `?q=xx&limit=10`；用 `Query()` 附加校验（`ge`、`le`、`max_length`）和默认值
- **请求体（Pydantic）**：用 `BaseModel` 声明 JSON 结构——解析、校验（`Field(gt=0)`）、类型转换全自动
- **响应模型**：`response_model=ItemResponse` 控制对外暴露的字段，隐藏内部数据
- **错误处理**：`raise HTTPException(status_code=404, detail="...")`
- **自动文档**：`/docs`（Swagger UI）、`/redoc`，无需手写文档

## 第二课：依赖注入 Depends（`depends_demo.py`）

**核心思想**：把可复用逻辑抽成函数/类，用 `Depends` 声明"由它提供参数"，FastAPI 自动调用注入。好处：复用（分页、DB 连接）、解耦（测试可换假实现）、校验前置（鉴权）。

demo 覆盖 6 种写法：

1. **基本函数依赖**：`def get_greeting()` 返回值注入参数
2. **带参数的依赖**：依赖函数自己的 `Query` 参数也由 FastAPI 解析（公共分页参数）
3. **子依赖**：依赖可以嵌套依赖，FastAPI 自底向上解析依赖树
4. **类作为依赖**：实现 `__call__` 的类，`Depends(实例)` 可配置（如 `QueryChecker(max_len=5)`）
5. **`yield` 依赖**：`yield` 前=前置准备（建连接），`yield` 后=事后清理（关连接），**即使接口异常也会执行**——数据库 session 的标准写法
6. **路由级依赖**：`dependencies=[Depends(verify_token)]` 只做前置校验（鉴权），结果不注入函数

要点：官方推荐 `Annotated[str, Depends(fn)]` 写法（老式 `= Depends(fn)` 效果相同但 IDE 支持差）；同一请求内同一依赖只执行一次（缓存）。

## 第三课：数据库集成（`db_demo.py`）

**核心思想**：ORM——用 Python 类操作数据库，类=表、实例=行。技术选型 **SQLModel**（FastAPI 作者开发，SQLAlchemy 2.0 + Pydantic 合体）。

三个核心对象：

- **Model**：`class Hero(SQLModel, table=True)` 定义表结构（`primary_key=True`、`index=True`）
- **Engine**：`create_engine(url)` 连接池，全局一个；`echo=True` 在终端打印生成的 SQL（学习时建议开）
- **Session**：`with Session(engine)` 一次工作单元；`create_engine("sqlite:///demo.db")` 换 PostgreSQL 只需改连接串

Session 依赖就是第二课的 yield 依赖：`SessionDep = Annotated[Session, Depends(get_session)]`。

**一个表拆 4 个模型**（重要设计思想）：`Hero`（表）、`HeroCreate`（入参）、`HeroPublic`（出参，故意不含敏感字段）、`HeroUpdate`（全可选字段 + `model_dump(exclude_unset=True)` 实现 PATCH 部分更新）。

写操作三部曲：`session.add()` → `session.commit()`（落盘）→ `session.refresh()`（取回自增 id）。

REST 约定：POST=创建、GET=查询（`offset/limit` 分页）、PATCH=部分更新、DELETE=删除。

生产环境差距：Alembic 数据库迁移、连接池参数、AsyncSession 异步。

## 第四课：JWT 用户认证（`auth_demo.py`）

**核心思想**：无状态认证——登录发签名令牌，后续请求带令牌，服务器验签不存会话。

流程：`注册（argon2id 哈希存密码）` → `登录（校验密码，签发 JWT）` → `请求头 Authorization: Bearer <token>`。

- **JWT**：`头部.载荷.签名`，Base64 不加密只防篡改；载荷放 `sub`（用户名）、`exp`（过期时间）
- **`OAuth2PasswordBearer(tokenUrl="auth/login")`**：从请求头提取 token；同时让 `/docs` 出现 Authorize 按钮（注意：form 表单解析需要 `python-multipart` 依赖）
- **`get_current_user` 依赖**：验签 → 取 `sub` → 查库 → 返回用户；任何失败返回 401
- **依赖链叠权限**：`require_admin` 依赖 `CurrentUser`（子依赖），接口声明 `user: AdminUser` 即完成"登录 + 管理员"双重校验
- **401 vs 403**：401=不知道你是谁；403=知道你是谁但权限不足

生产环境清单：`SECRET_KEY` 放环境变量且 ≥32 字节随机、refresh token、RS256 非对称算法、HTTPS、注销黑名单（Redis）。

---

## 后续学习方向

- 把 4 个 demo 整合成标准项目结构（`app/routers`、`app/models` 分包，`APIRouter` 组织路由）
- 限流与缓存（slowapi / Redis）
- 环境配置管理（pydantic-settings，区分 dev/prod）
- Alembic 数据库迁移实战
- Docker 打包与生产部署（uvicorn 多进程 + Nginx）
- 测试：pytest + TestClient
