# 11.05 dify 的代码规范分析（API + Web）

> 通过对比后端（api/）和前端（web/）的规范，理解 dify 的全栈工程标准。

## 🎯 学习目标

完成本文档后，你将能够：

- 对比 Python（后端）与 TypeScript（前端）的代码风格差异
- 列出 dify 后端的分层架构（controller → service → core/domain）
- 列出 dify 前端的状态管理策略（local / Jotai / feature store）
- 理解 dify 的 i18n 强制规范（所有用户可见字符串必须用 i18n key）
- 在自己的项目中借鉴 dify 的全栈工程实践

## 📚 前置知识

- 已完成 [01-pep8.md](./01-pep8.md) 到 [04-docstring.md](./04-docstring.md)
- 已完成 [02-agents-md.md](./02-agents-md.md)
- 了解 Flask / Next.js 基本概念

## 1. 核心概念

### 1.1 dify 全栈代码规范的三大支柱

1. **`api/AGENTS.md`** —— 后端规范（Python）：PEP 8 + 120 字符行宽 + 分层架构 + TypedDict 优先
2. **`web/CLAUDE.md`** —— 前端规范（TypeScript / React）：strict 模式 + i18n 强制 + overlay 组件强制
3. **`CONTRIBUTING.md`** —— 通用规范：贡献者入门、PR 流程、Issue 流程

### 1.2 后端规范核心（`api/AGENTS.md`）

| 维度 | 规则 |
|---|---|
| **工具** | Ruff（format + lint），行宽 ≤ 120 字符 |
| **命名** | snake_case（变量/函数）、PascalCase（类）、UPPER_CASE（常量） |
| **类型** | 所有公共 API 必须有类型注解；优先 `list[str]`、`TypedDict`；避免 `Any` |
| **类布局** | 成员变量必须显式声明在 `__init__` 之前 |
| **Pydantic** | v2 约定 + `model_config = ConfigDict(extra="forbid")` |
| **日志** | 用 `logging.getLogger(__name__)`，禁用 `print` |
| **异常** | 领域异常（如 `services/errors`、`core/errors`），在控制器层翻译成 HTTP |
| **数据库** | 用 `TypeBase` 基类；`with Session(db.engine, ...)` 上下文管理器；始终带 `tenant_id` |
| **存储** | 通过 `extensions.ext_storage.storage`，禁用直接文件 I/O |
| **HTTP** | 用 `core.helper.ssrf_proxy`，禁用 `requests` |
| **配置** | 用 `configs.dify_config`，禁用直接 `os.getenv` |
| **架构** | controller → service → core/domain 分层 |

### 1.3 前端规范核心（`web/CLAUDE.md`）

| 维度 | 规则 |
|---|---|
| **工作流** | 参考 `web/docs/test.md` 和 `web/docs/lint.md` |
| **i18n** | 用户可见字符串必须用 `web/i18n/en-US/` 下的 key，禁止硬编码 |
| **API 调用** | 用 `@/service/client` 的 `consoleQuery` / `consoleClient`，禁止手写 REST |
| **Overlay 组件** | 强制使用 `@langgenius/dify-ui/*`，禁止从 `@/app/components/base/*` 引入 |
| **UI 组件** | 优先用 `@langgenius/dify-ui/*`，避免魔法值（arbitrary values） |
| **SVG 图标** | 必须放在 `packages/iconify-collections/assets/`，运行 generate 脚本 |
| **设计 token** | 读 `packages/dify-ui/AGENTS.md` 获取 Figma token 映射 |
| **状态管理** | 局部状态用 useState；跨组件用 Jotai atom；高频复杂用 feature store；持久化用 `createLocalStorageState` |
| **测试** | 必须遵守 `frontend-testing` skill |

### 1.4 后端 vs 前端的关键差异

| 维度 | 后端（api/） | 前端（web/） |
|---|---|---|
| 配置文件 | `api/AGENTS.md` | `web/CLAUDE.md` |
| 工具链 | Ruff + mypy/pyrefly + pytest | ESLint + TypeScript + Vitest |
| 行宽 | 120 字符 | （未明确，建议参考 ESLint 默认） |
| 命名约定 | snake_case | camelCase（变量/函数）、PascalCase（组件） |
| 类型系统 | 动态类型 + 强制类型注解 | 静态类型（TypeScript strict） |
| 状态管理 | DB + Redis + Celery | useState / Jotai / feature store |
| 并发模型 | Celery 异步任务 | React 渲染周期 + async/await |
| 异步调度 | Celery worker | 无（直接 Promise） |
| 日志 | logging（结构化） | console（开发）/ Sentry（生产） |
| 错误处理 | 领域异常 + 控制器翻译 | ErrorBoundary + try/catch |
| i18n | 不涉及 | 强制要求 |
| 风格基线 | PEP 8 + TypedDict | ESLint + Prettier |

## 2. 代码示例

### 2.1 后端 Pydantic + TypedDict 风格

```python
# 文件：example_backend_style.py
from datetime import datetime
from typing import NotRequired, TypedDict

from pydantic import BaseModel, ConfigDict, field_validator


class UserProfile(TypedDict):
    """用户档案的强类型字典。"""
    user_id: str
    email: str
    created_at: datetime
    nickname: NotRequired[str]  # 可选字段


class Example:
    """dify 风格的类布局：成员变量先声明。"""

    user_id: str
    created_at: datetime

    def __init__(self, user_id: str, created_at: datetime) -> None:
        self.user_id = user_id
        self.created_at = created_at


class TriggerConfig(BaseModel):
    """dify 风格的 Pydantic 模型：禁用额外字段。"""

    endpoint: str
    secret: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("secret")
    def ensure_secret_prefix(cls, value: str) -> str:
        if not value.startswith("dify_"):
            raise ValueError("secret must start with dify_")
        return value
```

**说明**：
- `UserProfile` 用 `TypedDict` 而非 `dict`，**每个 key/value 类型显式可见**
- `NotRequired[str]` 标注可选字段（PEP 655）
- `Example` 类的成员变量在 `__init__` 之前**显式声明**，即使没有默认值——这是 dify 强制规范
- `TriggerConfig` 用 `extra="forbid"`，避免外部传入未知字段

### 2.2 前端 i18n + Jotai 状态管理风格

```typescript
// 文件：example_frontend_style.tsx
'use client'

import { atom, useAtom } from 'jotai'
import { useTranslation } from '@/i18n/client'
import { consoleQuery } from '@/service/client'

// 1. i18n 强制：用户可见字符串必须用 i18n key
function UserCard({ userId }: { userId: string }) {
  const { t } = useTranslation()
  // ❌ 错误：硬编码中文字符串
  // return <div>用户ID：{userId}</div>
  // ✅ 正确：用 i18n key
  return <div>{t('user.card.idLabel', { id: userId })}</div>
}

// 2. Jotai 状态：跨组件共享的简单状态
const userCountAtom = atom(0)

function useUserCount() {
  const [count, setCount] = useAtom(userCountAtom)
  return { count, increment: () => setCount(c => c + 1) }
}

// 3. API 调用：用 consoleQuery，不用手写 fetch
function useUserProfile(userId: string) {
  return consoleQuery({
    url: `/users/${userId}`,
    method: 'GET',
  })
}
```

**说明**：
- 第 1 行：所有用户可见字符串必须通过 `t('key')` 翻译
- 第 14 行：跨组件共享状态用 **Jotai atom**，避免 React Context 的 re-render 问题
- 第 24 行：API 调用统一通过 `consoleQuery`，禁止在组件中手写 `fetch` / `axios`

### 2.3 反例：违反 dify 规范

```python
# ❌ 反例 1：成员变量未显式声明
class BadExample:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id  # 看不到类有哪些属性

# ✅ 正例：成员变量先声明
class GoodExample:
    user_id: str

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
```

```typescript
// ❌ 反例 1：硬编码中文字符串
function BadButton() {
  return <button>点击我</button>
}

// ✅ 正例：使用 i18n key
function GoodButton() {
  const { t } = useTranslation()
  return <button>{t('common.button.click')}</button>
}
```

```python
# ❌ 反例 2：直接读环境变量
import os
db_url = os.getenv('DB_URL', 'sqlite:///test.db')

# ✅ 正例：用 dify_config
from configs import dify_config
db_url = dify_config.DB_URL
```

## 3. dify 仓库源码解读

### 3.1 后端控制器层规范（API_SCHEMA_GUIDE）

**文件位置**：`/Users/xu/code/github/dify/api/controllers/API_SCHEMA_GUIDE.md`
**核心代码**（行 17-25）：

```markdown
## Naming

- Request body models: use a `Payload` suffix.
  - Example: `WorkflowRunPayload`, `DatasourceVariablesPayload`.
- Query parameter models: use a `Query` suffix.
  - Example: `WorkflowRunListQuery`, `MessageListQuery`.
- Response models: use a `Response` suffix and inherit from `ResponseModel`.
  - Example: `WorkflowRunDetailResponse`, `WorkflowRunNodeExecutionListResponse`.
- Use `ListResponse` or `PaginationResponse` for wrapper responses.
  - Example: `WorkflowRunNodeExecutionListResponse`, `WorkflowRunPaginationResponse`.
- Keep these models near the controller when they are endpoint-specific. Move them to `fields/*_fields.py` only when shared by multiple controllers.
```

**解读**：
- **命名后缀统一**：`Payload`（请求体）、`Query`（查询参数）、`Response`（响应）、`ListResponse` / `PaginationResponse`（包装响应）
- 这套约定让 Swagger 文档**自动可读**——开发者和前端都能从类名看出它的角色
- 第 25 行：**"Keep these models near the controller"** —— 局部模型就近放置，避免过度抽象；只有跨 controller 复用时才提到 `fields/` 下

### 3.2 后端 Pydantic v2 模式（api/AGENTS.md）

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`
**核心代码**（行 152-168）：

```python
from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator


class TriggerConfig(BaseModel):
    endpoint: HttpUrl
    secret: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("secret")
    def ensure_secret_prefix(cls, value: str) -> str:
        if not value.startswith("dify_"):
            raise ValueError("secret must start with dify_")
        return value
```

**解读**：
- 第 2 行：`pydantic` v2 的导入
- 第 6 行：`model_config = ConfigDict(extra="forbid")` —— 禁止额外字段，**所有外部输入严格校验**
- 第 8-12 行：`@field_validator` 用于领域规则（不是简单类型校验），如"secret 必须以 dify_ 开头"
- **关键设计**：在边界处（API 层）拦截非法输入，**业务层不需要重复校验**

### 3.3 前端 i18n 强制规范（web/CLAUDE.md）

**文件位置**：`/Users/xu/code/github/dify/web/CLAUDE.md`
**核心代码**（行 8-10）：

```markdown
## i18n

- User-facing strings must use `web/i18n/en-US/` keys instead of hardcoded text.
- When adding or renaming an i18n key, update all supported locale files with correct localized values. Do not leave fallback English in non-English locales unless the repo already intentionally does so for that exact key.
```

**解读**：
- 第 9 行：**强制**——所有用户可见字符串必须用 i18n key，**禁止硬编码**
- 第 10 行：新增/重命名 key 时必须同步**所有 locale 文件**——避免某些语言显示英文 fallback
- 唯一例外："unless the repo already intentionally does so for that exact key"——尊重既有约定
- 这条规则在 dify 中是 **hard rule**，违反会被 PR review 拒绝

### 3.4 前端 Overlay 组件强制规范

**文件位置**：`/Users/xu/code/github/dify/web/CLAUDE.md`
**核心代码**（行 16-21）：

```markdown
## Overlay Components (Mandatory)

- `../packages/dify-ui/README.md` is the permanent contract for overlay primitives, portals, root `isolation: isolate`, and the `z-50` / `z-60` layering.
- `./docs/overlay.md` records the current web overlay best practices.
- In new or modified code, use only overlay primitives from `@langgenius/dify-ui/*`.
- Do not introduce overlay imports from `@/app/components/base/*`; when touching existing callers, migrate them.
```

**解读**：
- **Overlay 组件（弹窗、Drawer、Tooltip 等）** 在 dify 有专门的规范：
  - 必须来自 `@langgenius/dify-ui/*`（新版组件库）
  - 禁止从 `@/app/components/base/*`（旧版组件库）引入
  - 已有调用方需**主动迁移**
- **z-index 分层**：50、60 两个层级（`packages/dify-ui/README.md` 定义）
- 关键词 "Mandatory" 标识这是**硬约束**

### 3.5 后端 SQLAlchemy 模式（api/AGENTS.md）

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`
**核心代码**（行 120-138，SQLAlchemy Patterns 整段）：

```markdown
### SQLAlchemy Patterns

- Models inherit from `models.base.TypeBase`; do not create ad-hoc metadata or engines.
- Open sessions with context managers:

```python
from sqlalchemy.orm import Session

with Session(db.engine, expire_on_commit=False) as session:
    stmt = select(Workflow).where(
        Workflow.id == workflow_id,
        Workflow.tenant_id == tenant_id,
    )
    workflow = session.execute(stmt).scalar_one_or_none()
```

- Prefer SQLAlchemy expressions; avoid raw SQL unless necessary.
- Always scope queries by `tenant_id` and protect write paths with safeguards (`FOR UPDATE`, row counts, etc.).
- Introduce repository abstractions only for very large tables (e.g., workflow executions) or when alternative storage strategies are required.
```

**解读**：
- 第 122 行：所有 model 必须继承 `models.base.TypeBase`——**禁止**临时创建 metadata / engine，避免出现"游离"的 ORM 对象
- 第 124-133 行：**`with Session(db.engine, expire_on_commit=False) as session:`**——dify 强制用上下文管理器，**永远不**直接用全局 `db.session`。`expire_on_commit=False` 让对象在 session 关闭后仍可访问属性
- 第 130-131 行：查询必须**同时**带 `id` 和 `tenant_id`——这是 dify 多租户隔离的底线，差一行就 cross-tenant 泄漏
- 第 135 行：写路径要带 `FOR UPDATE` 或 row-count 校验，避免 race
- 第 136 行：只对超大表（workflow executions）才引入 Repository 抽象——**反对过早抽象**

### 3.6 后端 Controller / Service 边界（api/AGENTS.md）

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`
**核心代码**（行 193-202）：

```markdown
### Controllers & Services

- Controllers: parse input via Pydantic, invoke services, return serialised responses; no business logic.
- Services: coordinate repositories, providers, background tasks; keep side effects explicit.
- Document non-obvious behaviour with concise docstrings and comments.
- For `204 No Content` responses, return an empty body only; never return a dict, model, or other payload.
- For Flask-RESTX controller request, query, and response schemas, follow `controllers/API_SCHEMA_GUIDE.md`.
  In short: use Pydantic models, document GET query params with `query_params_from_model(...)`, register response
  DTOs with `register_response_schema_models(...)`, serialize response DTOs with `dump_response(...)`,
  and avoid adding new legacy `ns.model(...)`, `@marshal_with(...)`, or GET `@ns.expect(...)` patterns.
```

**解读**：
- 第 194 行：**Controller 三大职责**——`parse`（Pydantic）、`invoke`（调 service）、`return`（序列化响应）。**没有业务逻辑**。这层"瘦"才能让 Service 单元可测
- 第 195 行：**Service 三大职责**——`coordinate`（仓库/Provider/后台任务）、`explicit side effects`（副作用要明显）、`document`（docstring + comment）
- 第 197 行：`204 No Content` 只能返回**空 body**——**禁止**返回 dict / model 等"我顺手把对象也吐出来"的写法，避免后续误用
- 第 198-201 行：dify 正在从 Flask-RESTX 的 `ns.model(...)` 迁移到 **Pydantic 模型** + `query_params_from_model(...)` / `register_response_schema_models(...)` / `dump_response(...)`——AGENTS.md 明确说"不要新增 legacy `ns.model(...)` 写法"，把迁移写进规范

### 3.7 前端状态管理选型树（web/CLAUDE.md）

**文件位置**：`/Users/xu/code/github/dify/web/CLAUDE.md`
**核心代码**（行 39-46）：

```markdown
## Client State Management

- Use local component state for state owned by one component.
- Use feature-level Jotai atoms for simple client state shared across components in the same feature, especially when components need a shared source of truth, derived values, or shared actions.
- Use existing feature stores for complex or high-frequency interaction state such as workflow canvas, drag, resize, and panel runtime state.
- For shared low-frequency, client-only persistence such as user preferences, dismissed notices, and UI defaults, use feature-owned storage modules built with `createLocalStorageState`.
- For high-frequency interactions, update the feature state during interaction and persist storage only on commit or settled updates.
- Keep storage keys and raw/custom formats in the owner module; callers should import the named storage hooks instead of scattering direct storage access.
- Do not add ad hoc global event listeners for shared state. Prefer atoms, existing stores, or a shared subscription hook so listeners are centralized and deduplicated.
```

**解读**：
- 第 40 行：状态被组件独占 → **local state**（`useState` / `useReducer`）
- 第 41 行：跨组件共享、需要 derived value → **Jotai atom**（推荐粒度：feature-level）
- 第 42 行：高频交互（workflow canvas、drag、resize）→ 既有 **feature store**（Redux-like）
- 第 43 行：低频持久化（用户偏好、关闭过的提示）→ `createLocalStorageState`
- 第 44 行：**高频交互**期间只更新 feature state，**提交时**才落 storage——避免每帧写 localStorage
- 第 45 行：存储 key 和 raw 格式**只在 owner 模块里暴露**——调用方只 `useFoo()` 钩子，不直接 `localStorage.getItem`
- 第 46 行：禁止 ad-hoc `addEventListener`——所有共享状态走 atom/store/subscription hook，**监听器集中**

## 4. 关键要点总结

- dify 的代码规范分三层：项目级（CONTRIBUTING）→ 后端（api/AGENTS.md）→ 前端（web/CLAUDE.md）
- 后端核心：**PEP 8 + 120 字符 + TypedDict 优先 + 分层架构（controller → service → core）+ 领域异常**
- 前端核心：**i18n 强制 + overlay 组件强制 + Jotai 状态管理 + consoleQuery API**
- **强制条款用强语义词**（Mandatory、MUST、Do not），不要用"建议"
- Pydantic v2 + `extra="forbid"` 在边界处拦截非法输入
- dify 没有 CHANGELOG.md，使用 GitHub Releases 自动归类（PR 标题驱动）
- 学习 dify 的规范不是为了"模仿"，而是理解"为什么这样约束"

## 5. 练习题

### 练习 1：基础（必做）

阅读 `/Users/xu/code/github/dify/api/AGENTS.md` 和 `/Users/xu/code/github/dify/web/CLAUDE.md`，列出 5 条后端独有规范、5 条前端独有规范、5 条共有规范。

**参考答案**：见 `solutions/05-style-in-dify.md`

### 练习 2：进阶

打开 `/Users/xu/code/github/dify/api/controllers/console/` 下任意一个 controller 文件，看它是否遵循 `API_SCHEMA_GUIDE.md` 的命名约定（`Payload` / `Query` / `Response` 后缀）。统计：符合规范的有几个、有例外吗？

### 练习 3：挑战（选做）

阅读 `/Users/xu/code/github/dify/web/i18n/` 目录（如果存在），列出所有 locale 文件（如 `en-US/`, `zh-CN/`, `ja-JP/`），对比同一 key 在不同语言文件中的差异。思考：i18n key 的命名约定是什么？是用嵌套目录还是扁平的？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/AGENTS.md`
- `/Users/xu/code/github/dify/api/controllers/API_SCHEMA_GUIDE.md`
- `/Users/xu/code/github/dify/web/CLAUDE.md`
- `/Users/xu/code/github/dify/web/docs/test.md`
- `/Users/xu/code/github/dify/web/docs/lint.md`
- `/Users/xu/code/github/dify/web/docs/overlay.md`
- `/Users/xu/code/github/dify/CONTRIBUTING.md`

---

**文档版本**：v1.0
**最后更新**：2026-07-13