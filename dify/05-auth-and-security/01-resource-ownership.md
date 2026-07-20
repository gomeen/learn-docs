# 5.2.4 资源所有权与租户隔离

> 理解 dify 的核心架构 —— 多租户隔离，看懂所有数据库查询背后的 tenant_id 过滤。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解多租户（Multi-Tenancy）架构的三种实现方式
- 掌握 dify 的"共享 DB + tenant_id 列"模式
- 能识别 dify 代码中所有"按 tenant_id 过滤"的查询模式
- 理解资源所有权（`created_by`）与租户隔离（`tenant_id`）的协同

## 📚 前置知识

- 多租户与资源所有权理论（详见 [多租户架构](../../_common/08-authorization/05-multi-tenant.md)、[资源所有权](../../_common/08-authorization/04-resource-ownership.md)）
- ACL 背景（详见 [ACL](../../_common/08-authorization/03-acl.md)）
- SQLAlchemy 查询基础（详见 [SQLAlchemy 查询](../03-database/03-sqlalchemy-query.md)）

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
2. user 是 owner（created_by）？否则走 RBAC（详见 [RBAC](../../_common/08-authorization/01-rbac.md)）
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

## 3. 关键要点总结

- 多租户 = 一个实例服务多个客户，数据严格隔离
- dify 用 **共享 DB + tenant_id 列** 模式
- **所有 DB 查询都必须带 `tenant_id`**，这是硬性规范
- 跨租户访问返回 **404 而不是 403**，防资源枚举
- `tenant_id` 隔离数据集，`created_by` 隔离所有者，二者协同
- 复合索引 `(tenant_id, type)` 优化租户内按类型查询的性能

---

**文档版本**：v1.0
**最后更新**：2026-07-13
