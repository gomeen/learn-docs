# 2.3.5 dify 的 Pydantic 使用规范

> 总结 dify 中 Pydantic 的使用规范，能写出符合 dify 风格的 Pydantic 模型。

## 🎯 学习目标

完成本文档后，你将能够：
- 总结 dify 中 Pydantic 的标准使用模式
- 掌握 `ResponseModel`、`field_validator`、`ConfigDict` 的组合用法
- 在 dify 中找到标准的 DTO 定义位置
- 独立写一个符合 dify 风格的 Pydantic 模型

## 📚 前置知识

- [Pydantic 基础](./12-pydantic-basics.md) 至 [Pydantic 配置](./15-pydantic-config.md)（Pydantic 全套）
- [DTO 三层 Schema](./14-pydantic-dto.md)

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

## 3. 关键要点总结

- dify 的 Pydantic 使用分为三层：**API 层**、**领域层**、**配置层**
- 命名约定：`Payload` / `Query` / `Response` / `Entity`
- 所有 Response 继承 `ResponseModel`（`from_attributes=True`）
- 字段带详细 `description`（自动 Swagger）
- 用 `field_validator` 处理默认值规范化（空 list → None）
- 用 `StrEnum` 定义枚举（序列化友好）
- 不可变领域对象用 `frozen=True`
- 配置用 `BaseSettings` 自动从环境变量读取

---

**文档版本**：v1.0
**最后更新**：2026-07-13
