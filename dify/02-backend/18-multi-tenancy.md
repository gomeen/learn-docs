# 2.4.1 多租户架构：`tenant_id` 贯穿全链路

> 理解多租户（Multi-tenancy）架构，掌握 dify 中 `tenant_id` 的全链路传递。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解多租户架构的核心概念：数据隔离 + 资源配额
- 掌握 dify 中 `tenant_id` 的来源（登录用户 → 当前租户）
- 在 dify 中找到所有需要 `tenant_id` 过滤的代码
- 设计多租户安全的数据访问层

## 📚 前置知识

- [分层架构](../../_common/22-architecture/02-layered-architecture.md)
- [Repository 模式](../../_common/22-architecture/03-repository-pattern.md)
- SQLAlchemy 基础（详见 [SQLAlchemy 映射](../03-database/02-sqlalchemy-mapping.md)）
- 查询层 `tenant_id` 过滤实践（详见 [多租户查询](../03-database/11-multi-tenant-query.md)）

## 1. 核心概念

### 1.1 什么是多租户？

**多租户（Multi-tenancy）** 是 SaaS 产品的标配：一个软件实例服务多个客户（租户），每个客户的数据必须严格隔离（通用多租户概念亦可参考 [`_common` 多租户](../../_common/08-authorization/05-multi-tenant.md)）。

```
SaaS 应用（dify）
├── Tenant A（公司 A）
│   ├── 用户 alice（A 公司员工）
│   ├── App 1
│   └── App 2
├── Tenant B（公司 B）
│   ├── 用户 bob（B 公司员工）
│   └── App 3
└── Tenant C（公司 C）
    └── ...
```

### 1.2 多租户的三大挑战

1. **数据隔离**：A 租户绝不能看到 B 租户的数据
2. **权限校验**：每个 API 都要校验"当前用户是否有权访问该租户资源"
3. **资源配额**：每个租户的存储、调用次数有上限（按订阅计划）

### 1.3 dify 的多租户模型

dify 的租户模型：

```
Account（用户）
  ↓ N:M
TenantAccountJoin（用户-租户关联）
  ↓ N:1
Tenant（租户/工作空间）
  ↓ 1:N
App, Workflow, Dataset, ...（所有业务数据）
```

每个业务表都有 `tenant_id` 列，通过它做数据隔离。请求上下文中的当前租户通常经 Flask `g` / 装饰器注入（详见 [Flask 上下文](./04-flask-context.md)）。

## 2. 代码示例

### 2.1 Tenant 数据模型

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import ForeignKey, String


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(StringUUID, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), default="normal")
    plan: Mapped[str] = mapped_column(String(16), default="sandbox")  # 套餐
    created_at: Mapped[datetime] = mapped_column(DateTime)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(StringUUID, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255))


class TenantAccountJoin(Base):
    """用户-租户关联（含角色）"""
    __tablename__ = "tenant_account_joins"

    id: Mapped[str] = mapped_column(StringUUID, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"))
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    role: Mapped[str] = mapped_column(String(16))  # owner / admin / editor / normal
    current: Mapped[bool] = mapped_column(Boolean, default=False)
```

### 2.2 Repository 层强制 tenant_id 过滤

```python
# ✅ 正确的多租户 Repository
class SqlAppRepository:
    def find_apps(self, tenant_id: str, page: int, limit: int) -> list[App]:
        """所有查询必须带 tenant_id。"""
        return self.session.query(App).filter_by(
            tenant_id=tenant_id,  # 强制过滤
        ).offset((page - 1) * limit).limit(limit).all()

    def find_by_id(self, tenant_id: str, app_id: str) -> App | None:
        """按 ID 查询也要带 tenant_id（防 IDOR 漏洞）。"""
        return self.session.query(App).filter_by(
            tenant_id=tenant_id,
            id=app_id,
        ).first()

    def delete(self, tenant_id: str, app_id: str) -> bool:
        """删除也要带 tenant_id。"""
        app = self.find_by_id(tenant_id, app_id)
        if app is None:
            return False
        self.session.delete(app)
        self.session.commit()
        return True
```

### 2.3 常见错误：忘记 tenant_id 过滤（IDOR 漏洞）

```python
# ❌ 严重错误：跨租户数据泄漏
class BadAppRepository:
    def find_by_id(self, app_id: str) -> App | None:
        # 没有 tenant_id 过滤！
        # A 租户用户传入 B 租户的 app_id 也能查到！
        return self.session.query(App).filter_by(id=app_id).first()

# 攻击示例：
# 1. 用户 A 登录，看到 URL /apps/123
# 2. 改成 /apps/456（属于租户 B）
# 3. 由于没 tenant_id 过滤，A 能读到 B 的应用！
```

### 2.4 Controller 层注入 tenant_id

```python
@app.route("/api/apps/<app_id>", methods=["GET"])
@login_required
def get_app(app_id: str):
    # 1. 从登录用户获取当前租户
    _, current_tenant_id = current_account_with_tenant()

    # 2. 用 (tenant_id, app_id) 查询
    app = AppRepository(db.session).find_by_id(current_tenant_id, app_id)
    if app is None:
        raise NotFound()

    return AppResponse.model_validate(app).model_dump()
```

## 3. 关键要点总结

- dify 的多租户根是 `Tenant`，所有业务表都有 `tenant_id` 列
- `Account.current_tenant_id` 是 property，从 `TenantAccountJoin.current=True` 取
- 所有 Repository 查询必须带 `tenant_id` 过滤（防 IDOR 漏洞）
- Controller 用 `@with_current_tenant_id` + `@get_app_model` 自动注入 tenant_id
- `_load_app_model` 同时按 `(app_id, tenant_id)` 查询——双保险
- `_load_app_model_with_trial` 是试用模式（不过滤 tenant_id），仅用于内部
- 用户切换租户通过 `Account.set_tenant_id(tenant_id)` 实现

---

**文档版本**：v1.0
**最后更新**：2026-07-13
