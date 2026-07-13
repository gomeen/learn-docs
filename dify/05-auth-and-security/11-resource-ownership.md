# 5.2.4 资源所有权与租户隔离

> 理解 dify 的核心架构 —— 多租户隔离，看懂所有数据库查询背后的 tenant_id 过滤。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解多租户（Multi-Tenancy）架构的三种实现方式
- 掌握 dify 的"共享 DB + tenant_id 列"模式
- 能识别 dify 代码中所有"按 tenant_id 过滤"的查询模式
- 理解资源所有权（`created_by`）与租户隔离（`tenant_id`）的协同

## 📚 前置知识

- 10-acl.md
- 01-fundamentals/05-sqlalchemy-orm.md

## 1. 核心概念

### 1.1 什么是多租户（Multi-Tenancy）？

**一个软件实例服务多个客户（租户）**，每个租户的数据必须严格隔离。

```
┌──────────────────────────────────────────┐
│              dify 实例                    │
│                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ tenant-A │ │ tenant-B │ │ tenant-C │ │
│  │ (公司A)  │ │ (公司B)  │ │ (公司C)  │ │
│  │  apps    │ │  apps    │ │  apps    │ │
│  │  users   │ │  users   │ │  users   │ │
│  │  datasets│ │  datasets│ │  datasets│ │
│  └──────────┘ └──────────┘ └──────────┘ │
└──────────────────────────────────────────┘
```

### 1.2 三种多租户实现方式

| 模式 | 隔离度 | 成本 | 适用 |
|------|--------|------|------|
| 独立 DB | 强 | 高 | 大客户 |
| 共享 DB + 独立 Schema | 中 | 中 | 中型 SaaS |
| 共享 DB + tenant_id 列 | 弱 | 低 | 大型 SaaS（dify 用） |

**dify 选择第三种**：`tenant_id` 列存在于每张业务表，所有查询都按 `tenant_id` 过滤。

### 1.3 dify 的双层隔离模型

dify 的隔离分两层：

1. **租户隔离（tenant_id）**：跨租户数据物理上可见但逻辑上隔离
2. **资源所有权（created_by）**：租户内区分谁拥有某资源

```
资源访问检查流程：
1. tenant_id 匹配？否则 404
2. user 是 owner（created_by）？否则走 RBAC
```

## 2. 代码示例

### 2.1 简化版多租户查询基类

```python
from sqlalchemy import Column, String, select
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class TenantScopedMixin:
    """所有需要租户隔离的表都继承这个。"""
    tenant_id = Column(String, nullable=False, index=True)


class App(TenantScopedMixin, Base):
    __tablename__ = "apps"
    id = Column(String, primary_key=True)
    name = Column(String)
    created_by = Column(String, nullable=False)  # 资源所有权


# 通用查询函数：强制带 tenant_id
def list_apps(session, tenant_id: str) -> list[App]:
    stmt = select(App).where(App.tenant_id == tenant_id)  # 必须过滤
    return session.scalars(stmt).all()


def get_app(session, tenant_id: str, app_id: str) -> App | None:
    # 同时用 id + tenant_id 过滤，跨租户访问查不到
    stmt = select(App).where(App.id == app_id, App.tenant_id == tenant_id)
    return session.scalar(stmt)
```

### 2.2 常见错误：忘记加 tenant_id 过滤

```python
# ❌ 错误：跨租户数据泄露！
def get_app_buggy(session, app_id: str):
    return session.scalar(select(App).where(App.id == app_id))

# 攻击者：把 URL 中的 app_id 改成其他租户的 ID，就能读到别人数据

# ✅ 正确：始终带 tenant_id
def get_app_safe(session, tenant_id: str, app_id: str):
    return session.scalar(
        select(App).where(App.id == app_id, App.tenant_id == tenant_id)
    )
```

## 3. dify 仓库源码解读

### 3.1 资源查询按 tenant_id 过滤

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/apikey.py`
**核心代码**（行 57-66）：

```python
def _get_resource(resource_id, tenant_id, resource_model):
    with sessionmaker(db.engine).begin() as session:
        resource = session.execute(
            select(resource_model).filter_by(id=resource_id, tenant_id=tenant_id)
        ).scalar_one_or_none()

    if resource is None:
        flask_restx.abort(HTTPStatus.NOT_FOUND, message=f"{resource_model.__name__} not found.")

    return resource
```

**解读**：
- 第 3-5 行：`filter_by(id=..., tenant_id=...)` 强制双条件查询
- 第 7-8 行：**查不到一律返回 404**——不区分"不存在"和"无权访问"
- **设计意图**：用 404 抹平"跨租户访问"的痕迹，攻击者无法通过状态码差异判断资源是否存在

### 3.2 API Token 表的 tenant_id 索引

**文件位置**：`/Users/xu/code/github/dify/api/models/model.py`
**核心代码**（行 2236-2251）：

```python
class ApiToken(Base):
    __tablename__ = "api_tokens"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="api_token_pkey"),
        sa.Index("api_token_app_id_type_idx", "app_id", "type"),
        sa.Index("api_token_token_idx", "token", "type"),
        sa.Index("api_token_tenant_idx", "tenant_id", "type"),  # 复合索引
    )

    id = mapped_column(StringUUID, default=lambda: str(uuid4()))
    app_id = mapped_column(StringUUID, nullable=True)
    tenant_id = mapped_column(StringUUID, nullable=True)  # 必填字段
    type: Mapped[ApiTokenType] = mapped_column(EnumText(ApiTokenType, length=16), nullable=False)
    token: Mapped[str] = mapped_column(String(255), nullable=False)
    last_used_at = mapped_column(sa.Date, nullable=True)
    created_at = mapped_column(sa.DateTime, nullable=False, server_default=func.current_timestamp())
```

**解读**：
- 第 7 行：**复合索引** `("tenant_id", "type")` —— 让"按 tenant 查询 + 类型过滤"性能最优
- 第 12 行：`tenant_id` 字段必填，所有 API Token 都属于某个租户
- **设计意图**：索引 + 必填字段双重保证，租户隔离在 DB 层就是不可绕过的

### 3.3 资源所有权判断

**文件位置**：`/Users/xu/code/github/dify/api/controllers/common/wraps.py`
**核心代码**（行 109-119）：

```python
def _is_resource_owned_by_current_user(
    tenant_id: str, account_id: str, resource_type: RBACResourceScope, resource_id: str
) -> bool:
    """Check if current user is the resource owner."""
    if resource_type == RBACResourceScope.APP:
        with sessionmaker(db.engine).begin() as session:
            resource = session.scalar(
                select(App).where(App.id == resource_id, App.tenant_id == tenant_id)
            )
        if resource is None:
            return False
        return resource.created_by == account_id
```

**解读**：
- 第 8-9 行：查资源时**也带 tenant_id**，避免跨租户误判所有权
- 第 13 行：`resource.created_by == account_id` —— 资源所有权的核心判断
- **协同关系**：`tenant_id` 先过滤数据集，`created_by` 再做个体判断
- **设计意图**：owner 拥有全部权限，无需在 RBAC 策略里把每条权限都列出来

## 4. 关键要点总结

- 多租户 = 一个实例服务多个客户，数据严格隔离
- dify 用 **共享 DB + tenant_id 列** 模式
- **所有 DB 查询都必须带 `tenant_id`**，这是硬性规范
- 跨租户访问返回 **404 而不是 403**，防资源枚举
- `tenant_id` 隔离数据集，`created_by` 隔离所有者，二者协同
- 复合索引 `(tenant_id, type)` 优化租户内按类型查询的性能

## 5. 练习题

### 练习 1：基础（必做）

写一个 `TenantScopedQuery` 上下文管理器：在 `with` 块内所有查询自动注入 `tenant_id=current_tenant_id`，离开 `with` 块时校验所有 ORM 对象都已被过滤。

### 练习 2：进阶

阅读 `api/models/model.py:2236-2251`，为什么 `api_token_tenant_idx` 要做成 `(tenant_id, type)` 复合索引而不是单列索引？

### 练习 3：挑战（选做）

设计一个 **租户级查询审计器**：扫描所有 `select(...)` 调用，如果某个查询没带 `tenant_id` 过滤，自动在 CI 阶段报错。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/console/apikey.py`
- `/Users/xu/code/github/dify/api/models/model.py`
- `/Users/xu/code/github/dify/api/controllers/common/wraps.py`
- 多租户架构模式：https://docs.microsoft.com/en-us/azure/architecture/guide/multitenant/approaches/
- 共享 DB 模式安全：https://cheatsheetseries.owasp.org/cheatsheets/Multi-Tenant_Cloud_Hosting_Security_Cheat_Sheet.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13