# 2.1.2 分层架构：Controller → Service → Repository → Domain

> 理解 dify 后端的四层分层架构，能定位代码职责边界。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握经典分层架构（Controller → Service → Repository → Domain）的职责划分
- 在 dify 仓库中识别每一层对应的代码目录
- 理解各层之间的依赖方向（依赖倒置）
- 避免跨层调用（如 Controller 直接访问 Repository）

## 📚 前置知识

- [DDD 基础概念](./01-ddd-concepts.md)
- Flask 路由基础（详见 [Flask 基础](./08-flask-basics.md)）
- SQLAlchemy ORM 基础（详见 [SQLAlchemy 映射](../03-database/12-sqlalchemy-mapping.md)）

## 1. 核心概念

### 1.1 四层架构的职责

经典分层架构（自顶向下）：

```
┌─────────────────────────────────────┐
│ Controller 层（HTTP 接口）            │  接收请求、参数校验、返回响应
├─────────────────────────────────────┤
│ Service 层（应用服务）                │  编排业务流程、事务控制
├─────────────────────────────────────┤
│ Repository 层（仓储）                 │  数据持久化、查询抽象
├─────────────────────────────────────┤
│ Domain 层（领域核心）                 │  业务规则、领域模型
└─────────────────────────────────────┘
```

| 层 | 职责 | 不应该做 |
|---|------|---------|
| **Controller** | 解析 HTTP 请求、参数校验、调用 Service、序列化响应 | 直接操作数据库、包含业务规则 |
| **Service** | 编排多个 Repository 操作、管理事务、跨领域协调 | 处理 HTTP 相关逻辑（request/response） |
| **Repository** | 封装数据访问（CRUD）、领域对象与 ORM 映射（模式详见 [仓储模式](./03-repository-pattern.md)） | 包含业务流程、调用其他 Repository |
| **Domain** | 业务规则、领域模型不变性、领域事件 | 依赖任何具体技术（数据库、HTTP 框架） |

### 1.2 dify 的目录映射

dify 的实际目录结构对应分层架构：

| 层级 | dify 目录 | 例子 |
|------|-----------|------|
| Controller | `api/controllers/` | `controllers/console/app/app.py` |
| Service | `api/services/` | `services/app_service.py` |
| Repository | `api/core/repositories/` | `core/repositories/sqlalchemy_workflow_execution_repository.py` |
| Domain | `api/core/` | `core/workflow/`、`core/app/` |
| 模型（ORM） | `api/models/` | `models/workflow.py` |

### 1.3 依赖倒置原则

**关键约束**：
- Controller → Service → Repository → Domain
- 上层依赖下层，**下层不能依赖上层**
- Domain 层定义接口（Protocol，详见 [Protocol 与 Generic](../01-fundamentals/09-protocol-generic.md)），Repository 层实现接口（依赖倒置；DI 详见 [依赖注入](./05-dependency-injection.md)）

这样设计的好处：
- 测试时可注入 Mock Repository
- 替换实现（如从 SQLAlchemy 切到 Celery-backed Repository）不影响上层

## 2. 代码示例

### 2.1 经典四层调用示例

```python
# === 1. Domain 层：定义接口和领域对象 ===
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class UserId:
    value: str

class UserRepository(Protocol):  # 仓储接口
    def find_by_id(self, user_id: UserId) -> "User | None": ...
    def save(self, user: "User") -> None: ...

@dataclass
class User:
    id: UserId
    email: str
    status: str = "active"

    def deactivate(self):
        if self.status != "active":
            raise ValueError("只能停用已激活的用户")
        self.status = "inactive"


# === 2. Repository 层：实现接口 ===
class SqlUserRepository:
    def __init__(self, db_session):
        self._session = db_session

    def find_by_id(self, user_id: UserId) -> User | None:
        row = self._session.query(...).filter_by(id=user_id.value).first()
        return User(id=UserId(row.id), email=row.email, status=row.status) if row else None

    def save(self, user: User) -> None:
        self._session.merge(...)


# === 3. Service 层：编排业务 ===
class UserApplicationService:
    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo

    def deactivate_user(self, user_id: str) -> None:
        user = self._user_repo.find_by_id(UserId(user_id))
        if user is None:
            raise UserNotFoundError(user_id)
        user.deactivate()  # 业务规则
        self._user_repo.save(user)


# === 4. Controller 层：HTTP 接口 ===
class UserController:
    def __init__(self, user_service: UserApplicationService):
        self._user_service = user_service

    def post_deactivate(self, user_id: str) -> dict:
        self._user_service.deactivate_user(user_id)
        return {"result": "success"}
```

### 2.2 常见错误：跨层调用

```python
# ❌ 错误 1：Controller 直接访问 Repository
class BadController:
    def get_user(self, user_id: str):
        return self.user_repo.find_by_id(user_id)  # 绕过 Service

# ✅ 正确：Controller 只调用 Service
class GoodController:
    def get_user(self, user_id: str):
        return self.user_service.get_user_profile(user_id)

# ❌ 错误 2：Repository 包含业务流程
class BadRepository:
    def deactivate_user(self, user_id: str):
        user = self.find_by_id(user_id)
        if user.status == "active":  # 业务规则应在 Domain 层
            user.status = "inactive"
        self.save(user)

# ✅ 正确：业务规则放在 Domain 对象
class GoodRepository:
    def save(self, user: User): ...  # 只负责持久化
```

## 3. dify 仓库源码解读

### 3.1 Controller 层：`AppApi.get()`

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/app/app.py`
**核心代码**（行 730-766）：

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

        if FeatureService.get_system_features().webapp_auth.enabled:
            app_setting = EnterpriseService.WebAppAuth.get_app_access_mode_by_id(
                app_id=str(app_model.id)
            )
            app_model.access_mode = app_setting.access_mode
        # ... 组装响应
        response_model = AppDetailWithSite.model_validate(
            app_model, from_attributes=True
        ).model_copy(update={"permission_keys": permission_keys_map.get(str(app_model.id), [])})
        return response_model.model_dump(mode="json")
```

**解读**：
- 第 7-13 行：多个装饰器叠加完成**横切关注点**（鉴权、权限、租户注入；装饰器原理详见 [装饰器](../01-fundamentals/10-decorator.md)）
- 第 14 行：`get_app_model` 装饰器从 URL 中提取 `app_id` 并查询 App
- 第 16 行：`AppService()` 创建服务实例（注意：dify 习惯直接 `AppService()`）
- 第 18-21 行：调用 Service 获取 App，然后做权限补充
- 第 24-26 行：把 ORM 对象转为 Pydantic Response Model 再返回（详见 [Pydantic 基础](./15-pydantic-basics.md)）

### 3.2 Service 层：`AppService.get_app()`

**文件位置**：`/Users/xu/code/github/dify/api/services/app_service.py`
**核心代码**（行 50-80）：

```python
class AppService:
    def get_app(self, app: App) -> App:
        """Return an App with tenant-scope check.

        The caller (controller decorator) is responsible for loading the App
        with the correct tenant_id; this method is the application-level
        guard against accidental cross-tenant access.
        """
        # 业务校验：确保 App 属于当前租户
        if app.tenant_id != current_user.current_tenant_id:
            raise UnauthorizedAndForceLogout("无权访问该应用")

        # 业务逻辑：补充 site 配置
        if not app.site:
            app.site = self._ensure_site(app)

        # 业务逻辑：补充模型配置
        if app.mode in {AppMode.CHAT, AppMode.AGENT_CHAT, AppMode.ADVANCED_CHAT}:
            app.app_model_config = self._load_model_config(app)

        return app
```

**解读**：
- 第 7-8 行：业务校验放在 Service 层（权限校验属于业务规则；多租户隔离详见 [多租户架构](./20-multi-tenancy.md)）
- 第 11-12 行：填充关联实体（site、model_config）—— Service 层负责编排
- **不直接操作 SQL**：Service 层不调用 `session.query()`，而是通过 ORM 关系或 Repository 加载

### 3.3 Repository 层：WorkflowExecutionRepository

**文件位置**：`/Users/xu/code/github/dify/api/core/repositories/factory.py`
**核心代码**（行 31-46）：

```python
class WorkflowExecutionRepository(Protocol):
    """仓储接口（Domain 层定义）。"""
    def save(self, execution: WorkflowExecution): ...

class WorkflowNodeExecutionRepository(Protocol):
    def save(self, execution: WorkflowNodeExecution): ...

    def save_execution_data(self, execution: WorkflowNodeExecution): ...

    def get_by_workflow_execution(
        self,
        workflow_execution_id: str,
        order_config: OrderConfig | None = None,
    ) -> Sequence[WorkflowNodeExecution]: ...


class DifyCoreRepositoryFactory:
    """根据配置动态创建 Repository 实例（依赖倒置）。"""

    @classmethod
    def create_workflow_execution_repository(cls, ...) -> WorkflowExecutionRepository:
        class_path = dify_config.CORE_WORKFLOW_EXECUTION_REPOSITORY
        repository_class = import_string(class_path)
        return repository_class(...)
```

**解读**：
- 第 4 行：`WorkflowExecutionRepository` 是 Protocol 接口（Domain 层）
- 第 12 行：`WorkflowNodeExecutionRepository` 是另一接口
- 第 24-28 行：`DifyCoreRepositoryFactory` 通过字符串路径动态创建实现类（`SQLAlchemyWorkflowExecutionRepository` 或 `CeleryWorkflowExecutionRepository`）
- **依赖倒置**：上层（Service）只依赖 Protocol 接口，不关心是 SQL 还是 Celery 实现

## 4. 关键要点总结

- **Controller** 只处理 HTTP 相关：参数校验、权限装饰器、调用 Service、序列化响应
- **Service** 编排业务流程：跨多个 Repository、事务控制、业务规则触发
- **Repository** 封装数据访问：通过 Protocol 接口抽象，支持多实现（SQL/Celery）
- **Domain** 包含核心业务规则：领域对象方法、不变量、领域事件
- dify 用 `controllers/`、`services/`、`core/repositories/`、`core/` 目录分别对应四层
- 通过 Protocol + Factory 实现依赖倒置，便于测试和多实现

## 5. 练习题

### 练习 1：基础（必做）

画一张图，展示 dify 中"获取 App 详情"的调用链路：
- Controller → Service → Repository → ORM
- 标注每一层所在的目录和文件名

### 练习 2：进阶

阅读 `api/core/repositories/sqlalchemy_workflow_execution_repository.py`：
1. 这个文件实现的是哪个 Protocol 接口？
2. 它如何处理 multi-tenancy（多租户）？
3. 为什么 Repository 要自己管理 session 生命周期？

### 练习 3：挑战（选做）

设计一个 `ConversationService.create_conversation()` 的实现，遵循分层架构：
- Controller 层负责参数校验和响应序列化
- Service 层负责事务控制和业务编排
- Repository 层只负责持久化
- Domain 层（`Conversation` 实体）包含创建规则

写完后用 mermaid 画出各层的调用关系。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/console/app/app.py` — Controller 层示例
- `/Users/xu/code/github/dify/api/services/app_service.py` — Service 层示例
- `/Users/xu/code/github/dify/api/core/repositories/factory.py` — Repository 抽象
- `/Users/xu/code/github/dify/api/core/repositories/sqlalchemy_workflow_execution_repository.py` — SQL 实现
- `/Users/xu/code/github/dify/api/models/workflow.py` — ORM 模型（Domain 层）
- Martin Fowler《企业应用架构模式》分层章节

---

**文档版本**：v1.0
**最后更新**：2026-07-13