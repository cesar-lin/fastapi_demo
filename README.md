# FastAPI 学习项目

一个渐进式 FastAPI 学习项目：从接口基础、依赖注入、数据库、JWT 认证，一路整合为标准项目结构 + TDD 测试套件的完整示例。

## 项目结构

```
fastapi_demo/
├── app/
│   ├── main.py            # 入口：创建 app、挂载 router、lifespan 初始化（建表+种子数据）
│   ├── database.py        # engine 与建表函数，全局唯一
│   ├── dependencies.py    # 共享依赖：SessionDep / PaginationDep / CurrentUser / AdminUser
│   ├── models/            # SQLModel 表模型 + 出入参模型（hero.py、user.py）
│   ├── schemas/           # 纯 Pydantic 模型（不落库的：item.py、token.py）
│   └── routers/           # APIRouter：items.py、heroes.py、auth.py
├── tests/
│   └── test_app.py        # 25 个单元测试，覆盖全部接口的成功与失败路径
├── conftest.py            # 使 pytest 能从项目根目录 import app 包
├── requirements.txt
└── README.md
```

## 快速开始

```bash
git clone https://github.com/cesar-lin/fastapi_demo.git
cd fastapi_demo

python3 -m venv .venv
source .venv/bin/activate      # Windows 用 .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

访问 `http://127.0.0.1:8000/docs` 使用交互式文档（右上角 Authorize 按钮可登录调试受保护接口）。

预置账号：管理员 `admin` / `admin123`（首次启动自动创建）。

## 运行测试

```bash
pytest -v          # 或 python -m pytest -v
```

## API 概览

| 接口 | 方法 | 说明 | 权限 |
|---|---|---|---|
| `/items/` | POST | 创建商品（内存存储，演示响应模型过滤字段） | 公开 |
| `/items/` | GET | 商品列表（复用分页依赖） | 公开 |
| `/items/{id}` | GET / DELETE | 查询 / 删除商品 | 公开 |
| `/heroes/` | GET | 英雄列表（数据库，分页） | 公开 |
| `/heroes/` | POST | 创建英雄 | 需登录 |
| `/heroes/{id}` | GET / PATCH | 查询 / 部分更新英雄 | 公开 |
| `/heroes/{id}` | DELETE | 删除英雄 | 需管理员 |
| `/auth/register` | POST | 注册（argon2id 哈希存密码） | 公开 |
| `/auth/login` | POST | 登录，返回 Bearer token（OAuth2 表单） | 公开 |
| `/auth/me` | GET | 当前用户信息 | 需登录 |
| `/auth/admin` | GET | 管理员专区 | 需管理员 |

## 测试设计（TDD）

`tests/test_app.py` 的 25 个用例即系统行为的完整定义，新增功能应先写测试再实现：

- **隔离**：测试用内存 SQLite（`StaticPool`），与开发库 `app.db` 完全无关；每个用例独立建表/清表，互不污染
- **依赖替换**：`app.dependency_overrides[get_session]` 把数据库会话换成测试会话——这是 FastAPI 测试的核心技巧，无需改业务代码
- **状态重置**：items 的内存 `fake_db` 每个用例清空
- **覆盖维度**：每个接口至少两条用例——成功路径 + 失败路径（401/403/404/409/422）；另验证敏感字段不外泄（`secret_name`、`hashed_password` 不出现在任何响应里）

```bash
pytest -v                                   # 全部测试
pytest tests/test_app.py -k heroes          # 按关键字过滤
pytest --tb=short                           # 失败时看简短堆栈
```

## 学习笔记

项目按五课渐进演化而来（早期的分课 demo 文件已整合删除，完整历史见 git 提交记录）：

1. **FastAPI 基础**：类型注解驱动校验与文档。路径参数 `{item_id}: int` 自动校验，查询参数 `Query(ge=, le=)`，请求体用 Pydantic `BaseModel`，`response_model` 控制出参，`HTTPException` 处理错误。代码即文档，`/docs` 自动生成。
2. **依赖注入（Depends）**：可复用逻辑抽成函数/类，`Depends` 声明注入。支持带参依赖、子依赖嵌套、类依赖（`__call__`）、`yield` 前置/后置（数据库 session 标准写法）、路由级 `dependencies=[...]`（鉴权）。官方推荐 `Annotated[X, Depends(fn)]` 写法。
3. **数据库（SQLModel）**：SQLAlchemy 2.0 + Pydantic。Model=表、Engine=连接池、Session=工作单元。写操作 `add → commit → refresh`。一个表拆 4 个模型（表/入参/出参/更新），`exclude_unset` 实现 PATCH 部分更新。CRUD 对应 REST：POST/GET/PATCH/DELETE。
4. **JWT 认证**：无状态认证——登录签发 JWT（`sub` + `exp`），请求头 `Authorization: Bearer <token>`。`OAuth2PasswordBearer` 提取 token 并让文档页出现 Authorize 按钮。依赖链 `get_current_user → require_admin` 叠出多级权限。401=未认证，403=权限不足。密码 argon2id 哈希存储。
5. **项目结构整合**：`APIRouter`（prefix/tags）模块化路由，入口 `include_router` 统一挂载；共享依赖集中 `dependencies.py`；`models/`（落库）与 `schemas/`（纯校验）分工；单一数据库。

## 生产环境差距

`SECRET_KEY` 用环境变量 + ≥32 字节随机值、Alembic 数据库迁移、refresh token 与注销黑名单、HTTPS、连接池参数、PostgreSQL 换库（仅改连接串）。

## 后续学习方向

- 环境配置管理（pydantic-settings，区分 dev/prod）
- Alembic 数据库迁移实战
- Docker 打包与生产部署（uvicorn 多进程 + Nginx）
- 限流与缓存（slowapi / Redis）
- pytest-cov 测试覆盖率、CI（GitHub Actions 自动跑测试）
