# 2.3.3 DTO 与 API Schema 设计模式

> 理解 DTO（数据传输对象）的概念，掌握 dify 的 API Schema 三层结构。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 DTO 的核心价值：解耦内部模型与外部 API
- 掌握 dify 的三层 Schema（Payload / Query / Response）
- 在 dify 中找到所有 DTO 定义的位置
- 设计清晰的 API Schema 边界

## 📚 前置知识

- [Pydantic 基础](./15-pydantic-basics.md)
- [dify Controller 设计](./14-flask-in-dify.md)
- DDD 基础（聚合根、实体；详见 [DDD 核心概念](./01-ddd-concepts.md)）

## 1. 核心概念

### 1.1 什么是 DTO？

**DTO（Data Transfer Object）** 是跨层/跨进程传输数据的对象。它的核心思想：
- **隐藏内部模型**：ORM 实体可能包含敏感字段（密码哈希、token）
- **明确传输契约**：API Schema 是前后端协作的协议
- **独立演化**：内部重构不影响 API

```python
# ❌ 错误：直接暴露 ORM 实体
@app.route("/users/<id>")
def get_user(id):
    user = User.query.get(id)  # 包含 password_hash 等敏感字段
    return user.to_dict()  # 把敏感字段也返回了

# ✅ 正确：使用 DTO
@app.route("/users/<id>")
def get_user(id):
    user = User.query.get(id)
    return UserResponse.model_validate(user).model_dump()  # 只暴露白名单字段
```

### 1.2 dify 的三层 Schema 模式

```
[External API]
    ↓ request
┌─────────────────────┐
│ *Payload (POST)     │  → 请求体
│ *Query (GET)        │  → 查询参数
└─────────────────────┘
    ↓ validate
[Service / Domain]
    ↓ return ORM / Entity
┌─────────────────────┐
│ *Response (DTO)     │  → 响应体
└─────────────────────┘
```

### 1.3 API_SCHEMA_GUIDE 规范

dify 的命名约定（来自 `api/controllers/API_SCHEMA_GUIDE.md`）：

| 类型 | 后缀 | 例子 | 说明 |
|------|------|------|------|
| 请求体 | `Payload` | `WorkflowRunPayload` | POST/PUT/PATCH body |
| 查询参数 | `Query` | `WorkflowRunListQuery` | GET query string |
| 响应 | `Response` | `WorkflowRunDetailResponse` | 返回 body |
| 列表响应 | `ListResponse` | `WorkflowRunListResponse` | 分页/列表 |

## 2. 代码示例

### 2.1 基础 DTO 三件套

```python
from pydantic import BaseModel, Field
from datetime import datetime


# 1. 请求体（POST）
class CreateArticlePayload(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str
    tags: list[str] = []


# 2. 查询参数（GET）
class ArticleListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    tag: str | None = None
    author: str | None = None


# 3. 响应（DTO；ConfigDict 详见 [Pydantic 配置](./18-pydantic-config.md)）
class ArticleResponse(BaseModel):
    id: str
    title: str
    content: str
    author: str
    tags: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)  # 支持从 ORM 反序列化


# 4. 列表响应（包装）
class ArticleListResponse(BaseModel):
    data: list[ArticleResponse]
    total: int
    page: int
    limit: int


# === Controller 使用 ===

@app.route("/articles", methods=["GET", "POST"])
def articles():
    if request.method == "GET":
        # 查询参数
        query = ArticleListQuery.model_validate(request.args.to_dict())
        articles = ArticleService.list(query)
        return ArticleListResponse(
            data=[ArticleResponse.model_validate(a) for a in articles],
            total=len(articles),
            page=query.page,
            limit=query.limit,
        ).model_dump(mode="json")

    elif request.method == "POST":
        # 请求体
        payload = CreateArticlePayload.model_validate(request.get_json())
        article = ArticleService.create(payload)
        return ArticleResponse.model_validate(article).model_dump(mode="json"), 201
```

### 2.2 嵌套 DTO

```python
class AuthorSummary(BaseModel):
    """作者概要（嵌套在 Article 中）"""
    id: str
    name: str


class ArticleDetailResponse(BaseModel):
    """包含完整作者信息"""
    id: str
    title: str
    content: str
    author: AuthorSummary  # 嵌套
    comments_count: int


class AuthorResponse(BaseModel):
    """作者详情（独立的响应）"""
    id: str
    name: str
    email: str
    articles: list[AuthorSummary] = []
```

### 2.3 DTO 与 ORM 分离

```python
# ORM 实体（数据库表）
class ArticleORM(Base):
    __tablename__ = "articles"
    id: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    content: Mapped[str]
    password_hash: Mapped[str]  # 敏感字段
    internal_notes: Mapped[str]  # 内部使用
    created_at: Mapped[datetime]


# DTO 响应（对外）
class ArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    content: str
    created_at: datetime
    # password_hash 不暴露
    # internal_notes 不暴露


# 转换
article_orm = ArticleORM.query.get(1)
response = ArticleResponse.model_validate(article_orm)  # 自动过滤
```

### 2.4 常见错误：DTO 暴露内部字段

```python
# ❌ 错误：把内部字段都包含在 DTO
class BadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    password_hash: str  # 泄漏！
    internal_state: str  # 内部状态


# ✅ 正确：只暴露 API 契约字段
class GoodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    # 显式列出要暴露的字段
```

## 3. dify 仓库源码解读

### 3.1 API_SCHEMA_GUIDE 关键规则

**文件位置**：`/Users/xu/code/github/dify/api/controllers/API_SCHEMA_GUIDE.md`
**核心代码**（行 1-30）：

```markdown
# API Schema Guide

This guide describes the expected Flask-RESTX + Pydantic pattern for controller request payloads, query
parameters, response schemas, and Swagger documentation.

## Principles

- Use Pydantic `BaseModel` for request bodies and query parameters.
- Use `fields.base.ResponseModel` for response DTOs.
- Keep runtime validation and Swagger documentation wired to the same Pydantic model.
- Prefer explicit validation and serialization in controller methods over Flask-RESTX marshalling.

## Naming

- Request body models: use a `Payload` suffix.
  - Example: `WorkflowRunPayload`, `DatasourceVariablesPayload`.
- Query parameter models: use a `Query` suffix.
  - Example: `WorkflowRunListQuery`, `MessageListQuery`.
- Response models: use a `Response` suffix and inherit from `ResponseModel`.
  - Example: `WorkflowRunDetailResponse`, `WorkflowRunNodeExecutionListResponse`.
- Use `ListResponse` or `PaginationResponse` for wrapper responses.
```

**解读**：
- 第 7-11 行：**核心原则**——Pydantic + 显式序列化，不用 Flask-RESTX 老式 `marshal_with`
- 第 16-21 行：**命名约定**——`Payload` / `Query` / `Response` 三种后缀
- 第 22-23 行：列表/分页用 `ListResponse` / `PaginationResponse` 包装

### 3.2 ResponseModel 基类

**文件位置**：`/Users/xu/code/github/dify/api/fields/base.py`
**核心代码**（节选）：

```python
from pydantic import BaseModel, ConfigDict


class ResponseModel(BaseModel):
    """所有响应 DTO 的基类。

    提供了统一的序列化配置：
    - from_attributes=True：支持从 ORM 对象创建
    - populate_by_name=True：支持序列化别名
    """
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
```

**解读**：
- 第 8-11 行：默认配置——`from_attributes=True` 让 DTO 可以从 ORM 对象反序列化
- **优势**：统一管理 DTO 配置，子类自动继承

### 3.3 完整的 Schema 三件套示例

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/app/app.py`
**核心代码**（节选）：

```python
# Query（GET）
class AppListBaseQuery(BaseModel):
    page: int = Field(default=1, ge=1, le=99999, description="Page number (1-99999)")
    limit: int = Field(default=20, ge=1, le=100, description="Page size (1-100)")
    mode: AppListMode = Field(default=DEFAULT_APP_LIST_MODE, description="App mode filter")
    name: str | None = Field(default=None, description="Filter by app name")
    tag_ids: list[str] | None = Field(default=None, description="Filter by tag IDs")


# Payload（POST）
class CreateAppPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=400)
    mode: AppListMode
    icon_type: str | None = None
    icon: str | None = None


# Response（DTO）
class AppDetailResponse(ResponseModel):
    id: str
    name: str
    description: str
    mode: AppListMode
    icon_type: str
    icon: str
    icon_background: str
    created_at: datetime
    updated_at: datetime


# ListResponse
class AppListResponse(ResponseModel):
    data: list[AppDetailResponse]
    total: int
    page: int
    limit: int
```

**解读**：
- 第 2-8 行：Query 模型带 `description`（自动生成 Swagger 文档）
- 第 11-17 行：Payload 模型用 `Field(...)` 表示必填
- 第 20-30 行：Response 继承 `ResponseModel`（自动获得 `from_attributes=True`）
- 第 33-38 行：ListResponse 包装 data 列表和分页信息

### 3.4 Controller 中的使用

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/app/app.py`
**核心代码**（行 558-600）：

```python
@console_ns.route("/apps")
class AppListApi(Resource):
    @console_ns.doc("list_apps")
    @console_ns.doc(params=query_params_from_model(AppListBaseQuery))
    @console_ns.response(200, "Success", console_ns.models[AppListResponse.__name__])
    @setup_required
    @login_required
    def get(self):
        """List apps"""
        # 1. 校验查询参数
        args = AppListBaseQuery.model_validate(request.args.to_dict(flat=True))

        # 2. 业务逻辑
        app_service = AppService()
        apps, total = app_service.list_apps(...)

        # 3. ORM → DTO
        return AppListResponse(
            data=[AppDetailResponse.model_validate(a, from_attributes=True) for a in apps],
            total=total,
            page=args.page,
            limit=args.limit,
        ).model_dump(mode="json")
```

**解读**：
- 第 11 行：`AppListBaseQuery.model_validate()` 校验查询参数
- 第 18 行：ORM 对象通过 `from_attributes=True` 反序列化为 DTO
- 第 24 行：`model_dump(mode="json")` 转 JSON 友好格式

## 4. 关键要点总结

- DTO 解耦**内部模型**（ORM）与**外部契约**（API）
- dify 用三层 Schema：`Payload`（请求体） / `Query`（查询参数） / `Response`（响应）
- 所有 Response 继承 `ResponseModel`（自动获得 `from_attributes=True`）
- 用 Pydantic 的 `from_attributes` 从 ORM 对象反序列化
- Controller 只负责"DTO ↔ ORM"转换，业务逻辑在 Service 层
- 严格遵循 **API_SCHEMA_GUIDE.md** 的命名约定

## 5. 练习题

### 练习 1：基础（必做）

为 "文章管理" 设计完整的三层 DTO：
- `CreateArticlePayload`（POST 请求体）
- `ArticleListQuery`（GET 查询参数，含 page、limit、tag、author）
- `ArticleResponse`（响应）
- `ArticleListResponse`（列表响应，含 data、total、page、limit）

要求：所有 Response 继承 `ResponseModel`。

### 练习 2：进阶

阅读 `api/controllers/console/app/app.py`：
1. 列出所有 `Payload` 后缀的类
2. 列出所有 `Query` 后缀的类
3. 列出所有继承 `ResponseModel` 的类
4. 它们都用了哪些 Pydantic 配置（`from_attributes`、`populate_by_name` 等）？

### 练习 3：挑战（选做）

为 dify 设计 `WorkflowRunListQuery` 和 `WorkflowRunDetailResponse`：
- `WorkflowRunListQuery`：page、limit、status、created_after、created_before
- `WorkflowRunDetailResponse`：id、workflow_id、status、inputs、outputs、created_at、finished_at、node_executions（嵌套）
- `WorkflowRunNodeExecution`：id、node_id、node_type、status、started_at、finished_at

用 `model_validator` 校验日期范围。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/API_SCHEMA_GUIDE.md` — Schema 规范
- `/Users/xu/code/github/dify/api/fields/base.py` — ResponseModel 基类
- `/Users/xu/code/github/dify/api/controllers/console/app/app.py` — 三层 Schema 示例
- Pydantic v2 模型配置：https://docs.pydantic.dev/latest/concepts/config/

---

**文档版本**：v1.0
**最后更新**：2026-07-13