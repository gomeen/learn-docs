# 2.3.5 dify 的 Pydantic 使用规范

> 总结 dify 中 Pydantic 的使用规范，能写出符合 dify 风格的 Pydantic 模型。

## 🎯 学习目标

完成本文档后，你将能够：
- 总结 dify 中 Pydantic 的标准使用模式
- 掌握 `ResponseModel`、`field_validator`、`ConfigDict` 的组合用法
- 在 dify 中找到标准的 DTO 定义位置
- 独立写一个符合 dify 风格的 Pydantic 模型

## 📚 前置知识

- [Pydantic 基础](./15-pydantic-basics.md) 至 [Pydantic 配置](./18-pydantic-config.md)（Pydantic 全套）
- [DTO 三层 Schema](./17-pydantic-dto.md)

## 1. 核心概念

### 1.1 dify 的 Pydantic 使用全景

dify 在三个层级使用 Pydantic：

| 层级 | 用途 | 例子 |
|------|------|------|
| **API 层** | 请求/响应 DTO | `controllers/console/app/app.py` |
| **领域层** | 领域对象、值对象、事件 | `core/app/entities/`、`core/workflow/nodes/*/entities.py` |
| **配置层** | 应用配置（dify_config） | `configs/dify_config.py` |

### 1.2 dify 的 Pydantic 风格

总结 dify 中 Pydantic 的标准用法：

1. **类属性风格**：所有字段在类顶部统一定义
2. **`Field(...)` 详细描述**：description 用于 Swagger 文档
3. **命名约定**：`*Payload` / `*Query` / `*Response` / `*Entity`
4. **配置集中**：用 `ResponseModel` 基类统一定义配置
5. **校验器分离**：`@field_validator` 和 `@model_validator` 写在字段定义后

### 1.3 dify 的 Pydantic 位置速查

| 文件 | 用途 |
|------|------|
| `api/fields/base.py` | `ResponseModel` 基类 |
| `api/controllers/console/app/app.py` | App 相关 DTO |
| `api/core/app/entities/app_invoke_entities.py` | 应用领域对象 |
| `api/core/app/entities/queue_entities.py` | 队列事件 |
| `api/core/app/entities/task_entities.py` | 任务状态 |
| `api/core/workflow/nodes/*/entities.py` | 各节点配置 |
| `api/configs/dify_config.py` | 应用配置 |

## 2. 代码示例

### 2.1 标准的 dify 风格 DTO

```python
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fields.base import ResponseModel


# === 1. 枚举（如果需要） ===
class ArticleStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# === 2. 查询参数（GET） ===
class ArticleListQuery(BaseModel):
    """List articles query parameters."""
    model_config = ConfigDict(extra="forbid")  # 严格模式

    page: int = Field(default=1, ge=1, le=99999, description="Page number (1-99999)")
    limit: int = Field(default=20, ge=1, le=100, description="Page size (1-100)")
    status: ArticleStatus | None = Field(default=None, description="Filter by status")
    keyword: str | None = Field(default=None, max_length=200, description="Search keyword")
    tag_ids: list[str] | None = Field(default=None, description="Filter by tag IDs")

    @field_validator("tag_ids", mode="before")
    @classmethod
    def validate_tag_ids(cls, value: list[str] | None) -> list[str] | None:
        """处理空 list 转为 None"""
        if not value:
            return None
        return value


# === 3. 请求体（POST） ===
class CreateArticlePayload(BaseModel):
    """Create article request body."""
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=200, description="Article title")
    content: str = Field(..., min_length=1, description="Article content (Markdown)")
    status: ArticleStatus = Field(default=ArticleStatus.DRAFT, description="Initial status")
    tags: list[str] = Field(default_factory=list, description="Article tags")


# === 4. 响应（继承 ResponseModel） ===
class AuthorSummary(ResponseModel):
    """嵌套的作者摘要"""
    id: str
    name: str
    avatar_url: str | None = None


class ArticleResponse(ResponseModel):
    """Article detail response."""
    id: str
    title: str
    content: str
    status: ArticleStatus
    tags: list[str]
    author: AuthorSummary
    created_at: datetime
    updated_at: datetime


class ArticleListResponse(ResponseModel):
    """Article list with pagination."""
    data: list[ArticleResponse]
    total: int
    page: int
    limit: int
```

### 2.2 标准的领域对象

```python
from pydantic import BaseModel, ConfigDict, Field


class WorkflowRunContext(BaseModel):
    """Workflow 执行上下文（领域对象）。"""
    model_config = ConfigDict(frozen=True)  # 不可变

    tenant_id: str
    app_id: str
    user_id: str
    invoke_from: str  # "web-app" / "service-api" / "debugger" 等
    trace_session_id: str | None = None


class QueueNodeStartedEvent(BaseModel):
    """节点开始执行事件。"""
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    event: str = "node_started"
    node_id: str
    node_type: str
    node_execution_id: str
    started_at: datetime
    inputs: dict[str, Any] = Field(default_factory=dict)
```

### 2.3 常见错误：不符合 dify 规范

```python
# ❌ 错误 1：用 dataclass 而非 Pydantic
from dataclasses import dataclass

@dataclass
class UserDTO:
    name: str  # 没有校验
    email: str

# ✅ 正确：用 BaseModel
class UserDTO(BaseModel):
    name: str = Field(..., min_length=1)
    email: str = Field(..., pattern=r"^[\w.-]+@[\w.-]+$")


# ❌ 错误 2：命名不规范
class ArticleData(BaseModel):  # 应为 ArticlePayload / ArticleResponse
    pass

# ✅ 正确
class ArticlePayload(BaseModel): ...  # 请求体
class ArticleResponse(ResponseModel): ...  # 响应
```

## 3. dify 仓库源码解读

### 3.1 完整的 dify 风格 DTO

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/app/app.py`
**核心代码**（行 80-145）：

```python
class AppListBaseQuery(BaseModel):
    page: int = Field(default=1, ge=1, le=99999, description="Page number (1-99999)")
    limit: int = Field(default=20, ge=1, le=100, description="Page size (1-100)")
    mode: AppListMode = Field(default=DEFAULT_APP_LIST_MODE, description="App mode filter")
    sort_by: AppListSortBy = Field(
        default="last_modified",
        description="Sort apps by last modified, recently created, or earliest created",
    )
    name: str | None = Field(default=None, description="Filter by app name")
    tag_ids: list[str] | None = Field(default=None, description="Filter by tag IDs")
    creator_ids: list[str] | None = Field(default=None, description="Filter by creator account IDs")
    is_created_by_me: bool | None = Field(default=None, description="Filter by creator")

    @field_validator("tag_ids", mode="before")
    @classmethod
    def validate_tag_ids(cls, value: list[str] | None) -> list[str] | None:
        if not value:
            return None
        return value

    @field_validator("mode", mode="before")
    @classmethod
    def validate_mode(cls, value: str | None) -> str:
        if value is None:
            return DEFAULT_APP_LIST_MODE
        return value


# 响应 DTO（继承 ResponseModel）
class AppDetailWithSite(ResponseModel):
    id: str
    name: str
    description: str
    mode: AppListMode
    icon_type: str
    icon: str
    icon_background: str
    created_at: datetime
    updated_at: datetime
    site: dict | None = None
    api_key: list[dict] | None = None
```

**解读**：
- 第 2-9 行：所有字段有详细 `description`（自动 Swagger）
- 第 10-12 行：Optional 字段用 `str | None = None`（Python 3.10+ 风格）
- 第 14-24 行：`field_validator` 处理空 list / None 默认值
- 第 31-42 行：Response 继承 `ResponseModel`，自动获得 `from_attributes=True`

### 3.2 复杂领域对象：DifyRunContext

**文件位置**：`/Users/xu/code/github/dify/api/core/app/entities/app_invoke_entities.py`
**核心代码**（行 17-100）：

```python
DIFY_RUN_CONTEXT_KEY = "_dify"
AGENT_RUNTIME_EXIT_INTENT_ARG = "_agent_runtime_exit_intent"
type AgentRuntimeExitIntent = Literal["suspend", "delete"]


class UserFrom(StrEnum):
    ACCOUNT = "account"
    END_USER = "end-user"


class InvokeFrom(StrEnum):
    SERVICE_API = "service-api"
    OPENAPI = "openapi"
    WEB_APP = "web-app"
    TRIGGER = "trigger"
    EXPLORE = "explore"
    DEBUGGER = "debugger"

    @classmethod
    def value_of(cls, value: str) -> "InvokeFrom":
        return cls(value)

    def to_source(self) -> str:
        source_mapping = {
            InvokeFrom.WEB_APP: "web_app",
            InvokeFrom.DEBUGGER: "dev",
            InvokeFrom.EXPLORE: "explore_app",
            InvokeFrom.TRIGGER: "trigger",
            InvokeFrom.SERVICE_API: "api",
            InvokeFrom.OPENAPI: "openapi",
        }
        return source_mapping.get(self, "dev")


class DifyRunContext(BaseModel):
    """Dify 运行上下文：每次工作流执行都带这个对象。"""
    tenant_id: str
    app_id: str
    user_id: str
    user_from: UserFrom
    invoke_from: InvokeFrom
    trace_session_id: str | None = None
```

**解读**：
- 第 4-7 行：`UserFrom` 用 `StrEnum`（字符串值，序列化友好）
- 第 9-15 行：`InvokeFrom` 也用 `StrEnum`，包含业务方法（`value_of`、`to_source`）
- 第 17-20 行：`value_of` 类方法——从字符串构造枚举
- 第 22-31 行：`to_source` 实例方法——把枚举值转为埋点用的 source 字符串
- 第 34-42 行：`DifyRunContext` 不可变的领域上下文

### 3.3 完整的应用配置：dify_config

**文件位置**：`/Users/xu/code/github/dify/api/configs/dify_config.py`
**核心代码**（节选）：

```python
from pydantic import Field
from pydantic_settings import BaseSettings


class DifyConfig(BaseSettings):
    """Dify 应用配置（从环境变量读取）。"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # === 应用基础 ===
    EDITION: str = Field(default="SELF_HOSTED", description="SELF_HOSTED / CLOUD / ENTERPRISE")
    DEPLOY_ENV: str = Field(default="DEV", description="DEV / STAGING / PRODUCTION")

    # === 数据库 ===
    DB_USERNAME: str = Field(default="postgres")
    DB_PASSWORD: str = Field(...)
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432)
    DB_DATABASE: str = Field(default="dify")

    # === Redis ===
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: str | None = Field(default=None)

    # === Repository 配置 ===
    CORE_WORKFLOW_EXECUTION_REPOSITORY: str = Field(
        default="core.repositories.sqlalchemy_workflow_execution_repository.SQLAlchemyWorkflowExecutionRepository",
        description="Workflow execution repository implementation (SQL or Celery)",
    )
```

**解读**：
- 第 4 行：`BaseSettings`——自动从环境变量读取（详见 [pydantic-settings](../01-fundamentals/20-pydantic-settings.md)）
- 第 6-10 行：`SettingsConfigDict` 配置环境变量读取行为
- 第 7 行：`env_file=".env"`——从 .env 文件读取（环境变量约定详见 [环境变量](../01-fundamentals/19-env-vars.md)）
- 第 13 行：`Field(default)` 设置默认值
- 第 17-21 行：`Field(...)` 表示必填（无默认值时）
- 第 33-36 行：通过环境变量切换 Repository 实现（依赖倒置）

## 4. 关键要点总结

- dify 的 Pydantic 使用分为三层：**API 层**、**领域层**、**配置层**
- 命名约定：`Payload` / `Query` / `Response` / `Entity`
- 所有 Response 继承 `ResponseModel`（`from_attributes=True`）
- 字段带详细 `description`（自动 Swagger）
- 用 `field_validator` 处理默认值规范化（空 list → None）
- 用 `StrEnum` 定义枚举（序列化友好）
- 不可变领域对象用 `frozen=True`
- 配置用 `BaseSettings` 自动从环境变量读取

## 5. 练习题

### 练习 1：基础（必做）

为 dify 的 "文章评论" 设计完整 Pydantic 模型：

```python
# 1. CreateCommentPayload（POST 请求体）
# 2. CommentListQuery（GET 查询参数）
# 3. CommentResponse（响应，继承 ResponseModel）
# 4. CommentListResponse（列表响应）

# 要求：
# - 严格模式（extra="forbid"）
# - 字段带 description
# - 用 field_validator 处理默认值
```

### 练习 2：进阶

阅读 `api/configs/dify_config.py`：
1. 它继承哪个基类？（`BaseSettings`）
2. 它从哪些来源读取配置？（环境变量、.env 文件）
3. 找出一个 `Field(...)` 必填字段，说明它的作用。

### 练习 3：挑战（选做）

设计 dify 风格的 "模型管理" DTO：

```python
class ModelProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"

class CreateModelPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: ModelProvider
    model_name: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=20)
    # ...

# 要求：
# - 严格校验
# - 敏感字段标记（不暴露到响应）
# - 用 field_validator 规范化 model_name（小写、去空格）
```

## 6. 参考资料

- `/Users/xu/code/github/dify/api/fields/base.py` — ResponseModel 基类
- `/Users/xu/code/github/dify/api/controllers/console/app/app.py` — DTO 示例
- `/Users/xu/code/github/dify/api/core/app/entities/app_invoke_entities.py` — 领域对象
- `/Users/xu/code/github/dify/api/configs/dify_config.py` — 应用配置
- `/Users/xu/code/github/dify/api/controllers/API_SCHEMA_GUIDE.md` — 规范
- Pydantic v2 文档：https://docs.pydantic.dev/latest/

---

**文档版本**：v1.0
**最后更新**：2026-07-13