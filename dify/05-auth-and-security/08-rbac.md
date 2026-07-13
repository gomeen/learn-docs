# 5.2.1 RBAC：基于角色的访问控制

> 理解 RBAC 模型，看懂 dify 的角色权限体系。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 RBAC 三要素：用户、角色、权限
- 理解 0 阶、1 阶、2 阶 RBAC 模型的区别
- 能在 dify 中识别 RBAC 装饰器的用法
- 区分 RBAC 与 ACL、ABAC 的适用场景

## 📚 前置知识

- 01-fundamentals/03-decorator.md（Python 装饰器）

## 1. 核心概念

### 1.1 RBAC 是什么？

RBAC（Role-Based Access Control）= **用角色绑定用户，用角色绑定权限**。

```
┌────────┐         ┌────────┐         ┌──────────┐
│ Alice  │ ─角色─→ │ Admin  │ ─权限─→ │ app:delete│
│ Bob    │ ─角色─→ │ Editor │ ─权限─→ │ app:edit  │
└────────┘         └────────┘         └──────────┘
```

**好处**：权限变更只需调整"角色→权限"，不用动"用户→权限"。

### 1.2 RBAC 的三个阶

| 阶 | 名称 | 特点 |
|----|------|------|
| RBAC0 | 核心 | 用户-角色-权限 三层 |
| RBAC1 | 继承 | 角色可继承（如 SeniorEditor 继承 Editor） |
| RBAC2 | 约束 | 角色互斥、基数限制（如一个用户最多一个 Owner） |
| RBAC3 | 完整 | 1 + 2 |

### 1.3 dify 的角色体系

dify 的 RBAC 定义在 `core/rbac.py`，核心概念：

```
RBACResourceScope（资源类型）：APP / DATASET / WORKSPACE
RBACPermission（权限点）：APP_DELETE / DATASET_API_KEY_MANAGE / ...
```

资源类型 + 权限点 = 一条具体的权限（如 `DATASET` 上的 `DATASET_API_KEY_MANAGE`）。

## 2. 代码示例

### 2.1 简化版 RBAC 实现

```python
from enum import Enum
from typing import Callable

class Permission(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"

class Role:
    def __init__(self, name: str, permissions: set[Permission]):
        self.name = name
        self.permissions = permissions

class User:
    def __init__(self, name: str, role: Role):
        self.name = name
        self.role = role

# 定义角色
ADMIN = Role("admin", {Permission.READ, Permission.WRITE, Permission.DELETE})
EDITOR = Role("editor", {Permission.READ, Permission.WRITE})
VIEWER = Role("viewer", {Permission.READ})

# 定义装饰器
def require_permission(perm: Permission) -> Callable:
    def decorator(func: Callable) -> Callable:
        def wrapper(user: User, *args, **kwargs):
            if perm not in user.role.permissions:
                raise PermissionError(f"{user.name} lacks {perm.value}")
            return func(user, *args, **kwargs)
        return wrapper
    return decorator

# 使用
@require_permission(Permission.DELETE)
def delete_app(user: User, app_id: str) -> str:
    return f"{user.name} deleted {app_id}"

# 测试
alice = User("alice", ADMIN)
bob = User("bob", EDITOR)

print(delete_app(alice, "app-1"))  # OK
print(delete_app(bob, "app-1"))    # PermissionError
```

### 2.2 角色继承（RBAC1）

```python
class RoleWithInheritance(Role):
    def __init__(self, name: str, permissions: set[Permission], parents: list["Role"] = None):
        super().__init__(name, permissions)
        self.parents = parents or []
        # 把父角色的权限并入
        for parent in self.parents:
            self.permissions |= parent.permissions

# SeniorEditor 继承 Editor
SENIOR_EDITOR = RoleWithInheritance(
    "senior_editor",
    {Permission.DELETE},      # 额外的权限
    parents=[EDITOR],         # 继承 editor 的 READ + WRITE
)
```

## 3. dify 仓库源码解读

### 3.1 RBAC 权限检查装饰器

**文件位置**：`/Users/xu/code/github/dify/api/controllers/common/wraps.py`
**核心代码**（行 68-106）：

```python
def rbac_permission_required[**P, R](
    resource_type: RBACResourceScope,
    scene: RBACPermission,
    *,
    resource_required: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Check enterprise RBAC permissions for the current flask-login user.

    When ``RBAC_ENABLED`` is ``False`` the decorator is a no-op and the
    request passes through unchanged. When enabled it resolves the current
    account/tenant and delegates to :func:`enforce_rbac_access`, raising
    ``Forbidden`` if access is denied.
    """

    def decorator(view: Callable[P, R]) -> Callable[P, R]:
        @wraps(view)
        def decorated(*args: P.args, **kwargs: P.kwargs) -> R:
            if not dify_config.RBAC_ENABLED:
                return view(*args, **kwargs)

            current_user, current_tenant_id = current_account_with_tenant()
            enforce_rbac_access(
                tenant_id=current_tenant_id,
                account_id=current_user.id,
                resource_type=resource_type,
                scene=scene,
                resource_required=resource_required,
                path_args=kwargs,
            )
            return view(*args, **kwargs)

        return decorated

    return decorator
```

**解读**：
- 第 1-5 行：装饰器工厂接收两个关键参数：**资源类型**（App/Dataset/Workspace）和**权限点**（具体操作）
- 第 18-20 行：**RBAC_ENABLED = False 时装饰器直接放行**，方便单机模式
- 第 22-24 行：通过 `current_account_with_tenant()` 拿到当前账号 + 租户
- 第 25-30 行：调用 `enforce_rbac_access` 做实际检查
- **设计意图**：用 `@rbac_permission_required(RBACResourceScope.APP, RBACPermission.APP_DELETE)` 这种声明式语法，把权限策略外置到配置层

### 3.2 API Key 创建：RBAC 应用实例

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/apikey.py`
**核心代码**（行 186-201）：

```python
    @console_ns.doc("create_app_api_key")
    @console_ns.doc(description="Create a new API key for an app")
    @console_ns.doc(params={"resource_id": "App ID"})
    @console_ns.response(201, "API key created successfully", console_ns.models[ApiKeyItem.__name__])
    @console_ns.response(400, "Maximum keys exceeded")
    @with_current_tenant_id
    @edit_permission_required
    @rbac_permission_required(RBACResourceScope.APP, RBACPermission.APP_RELEASE_AND_VERSION)
    def post(self, current_tenant_id: str, resource_id: UUID) -> tuple[dict[str, object], int]:
        """Create a new API key for an app"""
        return dump_response(ApiKeyItem, self._create_api_key(str(resource_id), current_tenant_id)), 201
```

**解读**：
- 第 8 行：`@rbac_permission_required(RBACResourceScope.APP, RBACPermission.APP_RELEASE_AND_VERSION)` 声明此接口需要"APP 资源 + 发布权限"
- 第 7 行：`@edit_permission_required` 是另一层装饰器（基本编辑权限），**两层权限检查叠加**
- 第 9-10 行：调用方未持有足够权限时，`Forbidden` 异常被 Flask 自动转为 **403**
- **设计意图**：把权限检查做成装饰器，业务代码完全不用关心"用户是否有权限"

## 4. 关键要点总结

- RBAC = 用户-角色-权限的三层映射，权限变更只需改"角色→权限"
- dify 用 `@rbac_permission_required(resource_type, permission)` 装饰器做权限检查
- RBAC 是 **配置驱动** 的，权限策略集中在 `RBACPermission` 枚举里
- **资源所有权** 短路：当用户拥有资源时直接放行，跳过权限检查
- RBAC vs ABAC：RBAC 简单可控，ABAC 灵活但复杂；dify 主要用 RBAC

## 5. 练习题

### 练习 1：基础（必做）

用 Python 实现一个简化版 RBAC：定义 `Role`、`Permission`、`User` 三个类，实现 `has_permission(user, perm)` 函数。

### 练习 2：进阶

阅读 `api/controllers/common/wraps.py:18-66` 的 `enforce_rbac_access`，解释 `_is_resource_owned_by_current_user` 的"短路"逻辑为什么能优化性能。

### 练习 3：挑战（选做）

设计一个支持"角色继承 + 权限否定"的 RBAC：例如 `SeniorEditor` 继承 `Editor` 但**显式拒绝** `DELETE` 权限（用 `~Permission.DELETE` 语法）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/common/wraps.py`
- `/Users/xu/code/github/dify/api/controllers/console/apikey.py`
- NIST RBAC 模型：https://csrc.nist.gov/projects/role-based-access-control
- RBAC vs ABAC：https://www.okta.com/identity-101/rbac-vs-abac/

---

**文档版本**：v1.0
**最后更新**：2026-07-13