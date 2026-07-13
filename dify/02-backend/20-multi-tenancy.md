# 2.4.1 多租户架构：`tenant_id` 贯穿全链路

> 理解多租户（Multi-tenancy）架构，掌握 dify 中 `tenant_id` 的全链路传递。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解多租户架构的核心概念：数据隔离 + 资源配额
- 掌握 dify 中 `tenant_id` 的来源（登录用户 → 当前租户）
- 在 dify 中找到所有需要 `tenant_id` 过滤的代码
- 设计多租户安全的数据访问层

## 📚 前置知识

- 02-backend/02-layered-architecture.md（分层架构）
- 02-backend/03-repository-pattern.md（Repository 模式）
- SQLAlchemy 基础（详见 03-database 系列）

## 1. 核心概念

### 1.1 什么是多租户？

**多租户（Multi-tenancy）** 是 SaaS 产品的标配：一个软件实例服务多个客户（租户），每个客户的数据必须严格隔离。

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

每个业务表都有 `tenant_id` 列，通过它做数据隔离。

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

## 3. dify 仓库源码解读

### 3.1 Tenant 模型

**文件位置**：`/Users/xu/code/github/dify/api/models/account.py`
**核心代码**（行 252-290）：

```python
class Tenant(TypeBase):
    """Tenant 实体：dify 的多租户根。"""
    __tablename__ = "tenants"
    __table_args__ = (
        sa.Index("tenant_status_idx", "status"),
    )

    id: Mapped[str] = mapped_column(StringUUID, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    plan: Mapped[str] = mapped_column(String(16), default="sandbox")
    status: Mapped[str] = mapped_column(String(16), default="normal")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def get_accounts(self) -> list[Account]:
        """获取该租户的所有账号。"""
        return [
            join.account
            for join in self.tenant_account_joins
            if join.account.status == AccountStatus.ACTIVE
        ]
```

**解读**：
- 第 2-5 行：基本租户字段（id、name、plan、status）
- 第 8 行：`plan` 字段标识租户的订阅计划（控制资源配额）
- 第 9 行：`status` 标识租户状态（normal、archived 等）
- 第 16-19 行：`get_accounts` 通过 `tenant_account_joins` 反向查询关联账号

### 3.2 Account.current_tenant_id

**文件位置**：`/Users/xu/code/github/dify/api/models/account.py`
**核心代码**（行 152-170）：

```python
@property
def current_tenant_id(self) -> str | None:
    """当前登录账号的当前租户 ID。

    这是一个 property，不是数据库字段：
    - 如果账号已登录：返回 join.current == True 的 tenant_id
    - 如果账号未登录：返回 None
    """
    join = db.session.query(TenantAccountJoin).filter_by(
        account_id=self.id,
        current=True,
    ).first()
    return join.tenant_id if join else None


def set_tenant_id(self, tenant_id: str):
    """切换当前租户（用户在多个租户之间切换时调用）。"""
    db.session.query(TenantAccountJoin).filter_by(
        account_id=self.id,
    ).update({TenantAccountJoin.current: False})
    db.session.query(TenantAccountJoin).filter_by(
        account_id=self.id,
        tenant_id=tenant_id,
    ).update({TenantAccountJoin.current: True})
    db.session.commit()
```

**解读**：
- 第 2-3 行：`current_tenant_id` 是 property（不是数据库字段）
- 第 7-9 行：查询 `current=True` 的 join 记录
- 第 13-23 行：`set_tenant_id` 实现租户切换——把其他租户的 `current=False`，目标租户设为 `current=True`

### 3.3 Controller 层 tenant_id 注入

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/app/app.py`
**核心代码**（行 730-748）：

```python
@console_ns.route("/apps/<uuid:app_id>")
class AppApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    @enterprise_license_required
    @with_current_user
    @with_current_tenant_id
    @rbac_permission_required(RBACResourceScope.APP, RBACPermission.APP_VIEW_LAYOUT)
    @get_app_model(mode=None)
    def get(self, current_tenant_id: str, current_user: Account, app_model: App):
        """Get app detail"""
        app_service = AppService()

        app_model = app_service.get_app(app_model)
```

**解读**：
- 第 9 行：`@with_current_tenant_id` 装饰器——把当前租户 ID 注入到 view 函数
- 第 11 行：`@get_app_model(mode=None)` 装饰器——从 URL 拿 `app_id`，并用 (tenant_id, app_id) 查询
- 第 12 行：方法签名包含 `current_tenant_id` 参数

### 3.4 get_app_model 的 tenant_id 过滤

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/app/wraps.py`
**核心代码**（行 25-50）：

```python
def _load_app_model(session: Session, app_id: str) -> App | None:
    """Load the tenant-scoped app row with the request session owned by `with_session`."""
    _, current_tenant_id = current_account_with_tenant()
    app_model = session.scalar(
        select(App).where(
            App.id == app_id,
            App.tenant_id == current_tenant_id,  # 强制 tenant_id 过滤
            App.status == "normal",
        ).limit(1)
    )
    return app_model


def _load_app_model_with_trial(app_id: str) -> App | None:
    """Load the app row with trial mode (no tenant filter)."""
    app_model = db.session.scalar(
        select(App).where(App.id == app_id, App.status == "normal").limit(1)
    )
    return app_model
```

**解读**：
- 第 3-13 行：核心查询——同时按 `app_id` + `tenant_id` 过滤
- 第 4 行：从 `current_account_with_tenant()` 拿当前租户
- 第 6-11 行：用 SQLAlchemy 2.0 风格的 `select(...).where(...).limit(1)`
- 第 16-19 行：`_load_app_model_with_trial` 是试用模式（无 tenant_id 过滤）

## 4. 关键要点总结

- dify 的多租户根是 `Tenant`，所有业务表都有 `tenant_id` 列
- `Account.current_tenant_id` 是 property，从 `TenantAccountJoin.current=True` 取
- 所有 Repository 查询必须带 `tenant_id` 过滤（防 IDOR 漏洞）
- Controller 用 `@with_current_tenant_id` + `@get_app_model` 自动注入 tenant_id
- `_load_app_model` 同时按 `(app_id, tenant_id)` 查询——双保险
- `_load_app_model_with_trial` 是试用模式（不过滤 tenant_id），仅用于内部
- 用户切换租户通过 `Account.set_tenant_id(tenant_id)` 实现

## 5. 练习题

### 练习 1：基础（必做）

实现一个多租户安全的 `DatasetRepository`：

```python
class SqlDatasetRepository:
    def find_datasets(self, tenant_id: str, page: int, limit: int) -> list[Dataset]: ...
    def find_by_id(self, tenant_id: str, dataset_id: str) -> Dataset | None: ...
    def save(self, dataset: Dataset) -> None: ...
    def delete(self, tenant_id: str, dataset_id: str) -> bool: ...
```

要求所有方法都带 `tenant_id` 参数。

### 练习 2：进阶

阅读 `api/core/repositories/sqlalchemy_workflow_execution_repository.py`：
1. 它的 `__init__` 接收哪些参数？（`session_factory`、`user`、`app_id`、`triggered_from`）
2. 它在 `save` 方法中如何设置 `tenant_id`？
3. 如果不传 `tenant_id`，会出现什么安全问题？

### 练习 3：挑战（选做）

设计 dify 的租户配额检查：

```python
class QuotaService:
    """租户配额服务"""
    def check_storage_quota(self, tenant_id: str, additional_bytes: int) -> None:
        """检查存储配额，超限抛 QuotaExceededError"""
        pass

    def check_messages_quota(self, tenant_id: str) -> None:
        """检查消息配额"""
        pass
```

要求：
- 从 `Tenant.plan` 读取配额上限
- 从 `FeatureService` 读取当前用量
- 超限抛 `QuotaExceededError`（继承 `BaseHTTPException`）

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/account.py` — Tenant / TenantAccountJoin 模型
- `/Users/xu/code/github/dify/api/controllers/console/app/app.py` — Controller tenant_id 注入
- `/Users/xu/code/github/dify/api/controllers/console/app/wraps.py` — get_app_model 实现
- `/Users/xu/code/github/dify/api/libs/login.py` — current_account_with_tenant
- `/Users/xu/code/github/dify/api/services/feature_service.py` — 配额管理

---

**文档版本**：v1.0
**最后更新**：2026-07-13