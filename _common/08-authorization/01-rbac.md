# 8.1 RBAC：基于角色的访问控制

> 理解 RBAC（Role-Based Access Control）的核心模型，能设计企业级权限系统。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 RBAC 的核心元素：用户、角色、权限、资源
- 区分 RBAC0/1/2/3 四种模型
- 在 dify 和 ruoyi 中识别 RBAC 实现
- 为自己的系统设计合理的角色权限模型

## 📚 前置知识

- 8 授权系列前置
- 数据库多对多关系
- 装饰器 / AOP 基础

## 1. 核心概念

### 1.1 什么是 RBAC？

RBAC（Role-Based Access Control）通过**角色**关联**用户**和**权限**，简化权限管理。

```
用户 ──多对多──> 角色 ──多对多──> 权限
                                     ↓
                                  资源 + 操作
```

**对比直接授权**：

```
❌ 直接授权：用户 Alice → 资源 A 的读权限
                Alice → 资源 A 的写权限
                Alice → 资源 B 的读权限
                （每新增一个用户都要配置）

✅ RBAC：Alice → 角色 "编辑" → 资源 A 的读写 + 资源 B 的读
         （新增用户只需分配角色）
```

### 1.2 RBAC 核心元素

| 元素 | 含义 | 示例 |
|------|------|------|
| **User** | 用户 | Alice |
| **Role** | 角色 | 管理员、编辑、只读用户 |
| **Permission** | 权限 | `app:read`, `app:write`, `app:delete` |
| **Resource** | 资源 | 应用 A、文档 X |
| **Session** | 会话 | 用户当前激活的角色 |

### 1.3 RBAC 四种模型（ NIST 标准）

```
RBAC0: 基础模型（用户-角色-权限）
   ↓
RBAC1: 角色继承（管理员继承编辑的权限）
   ↓
RBAC2: 角色约束（互斥、基数限制）
   ↓
RBAC3: RBAC1 + RBAC2 统一
```

#### RBAC0（基础）

```
用户 Alice ──> 角色 Admin ──> 权限 app:delete
```

#### RBAC1（角色继承）

```
           超级管理员
              ↓ 继承
            管理员
              ↓ 继承
            普通用户
```

#### RBAC2（角色约束）

- **互斥角色**：同一用户不能同时拥有财务 + 审计
- **基数限制**：超级管理员最多 1 人
- **先决条件**：要成为部门经理，必须先是员工

### 1.4 权限设计模式

#### 模式 1：粗粒度（基于资源类型）

```
权限: app:read, app:write, app:delete
       ↓
判断: 用户是否有 app:read 权限？
适用: 一般系统，ruoyi 默认
```

#### 模式 2：细粒度（基于资源实例）

```
权限: app:123:read, app:123:write, app:456:read
       ↓
判断: 用户是否有 app:123:write 权限？
适用: 多租户系统，dify 企业版
```

### 1.5 dify 和 ruoyi 的 RBAC 实现

| 项目 | 角色模型 | 权限粒度 |
|------|---------|---------|
| **dify** | TenantAccountRole（owner/admin/editor/normal）| 细粒度（资源实例级 RBAC）|
| **ruoyi** | system_role（超级管理员/普通角色） + data_scope | 中粒度（菜单级）+ 数据权限 |

**dify 特色**：企业版支持细粒度 RBAC，能控制"谁能编辑某个 App"
**ruoyi 特色**：内置数据权限（自己部门 / 本人 / 全部 / 自定义）

## 2. 代码示例

### 2.1 数据库设计（基础 RBAC）

```sql
-- 文件: schema.sql
-- 5 张核心表：users, roles, permissions, user_roles, role_permissions

CREATE TABLE users (
    id BIGINT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE roles (
    id BIGINT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT
);

CREATE TABLE permissions (
    id BIGINT PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL,  -- 例如: app:read
    description TEXT
);

-- 多对多：用户-角色
CREATE TABLE user_roles (
    user_id BIGINT REFERENCES users(id),
    role_id BIGINT REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
);

-- 多对多：角色-权限
CREATE TABLE role_permissions (
    role_id BIGINT REFERENCES roles(id),
    permission_id BIGINT REFERENCES permissions(id),
    PRIMARY KEY (role_id, permission_id)
);

-- 示例数据
INSERT INTO roles VALUES (1, 'admin', '管理员'), (2, 'editor', '编辑'), (3, 'viewer', '只读');
INSERT INTO permissions VALUES
    (1, 'app:read', '查看应用'),
    (2, 'app:write', '编辑应用'),
    (3, 'app:delete', '删除应用');
INSERT INTO role_permissions VALUES
    (1, 1), (1, 2), (1, 3),  -- admin 全部
    (2, 1), (2, 2),          -- editor 读写
    (3, 1);                  -- viewer 只读
```

### 2.2 Python 实现：RBAC 权限校验

```python
# 文件：rbac_check.py
# RBAC 权限校验实现
from functools import wraps
from flask import g, abort

# 模拟用户-角色-权限数据
USER_PERMISSIONS = {
    "alice": {"app:read", "app:write", "app:delete"},
    "bob": {"app:read", "app:write"},
    "charlie": {"app:read"},
}


def get_user_permissions(user_id: str) -> set[str]:
    """从数据库查询用户的所有权限（含继承）"""
    return USER_PERMISSIONS.get(user_id, set())


def require_permission(*required_permissions):
    """权限校验装饰器"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_perms = g.user_permissions  # 中间件层注入
            for perm in required_permissions:
                if perm not in user_perms:
                    abort(403, f"missing permission: {perm}")
            return f(*args, **kwargs)
        return wrapper
    return decorator


# 业务使用
@app.route("/apps/<int:app_id>")
@require_permission("app:read")
def view_app(app_id):
    return {"app_id": app_id}

@app.route("/apps/<int:app_id>", methods=["DELETE"])
@require_permission("app:delete")
def delete_app(app_id):
    return {"deleted": app_id}
```

### 2.3 角色继承（RBAC1）

```python
# 文件：rbac_inheritance.py
# 角色继承实现
ROLE_HIERARCHY = {
    "super_admin": {"admin"},
    "admin": {"editor"},
    "editor": {"viewer"},
}

ROLE_PERMISSIONS = {
    "super_admin": {"user:delete", "system:config"},
    "admin": {"app:delete", "user:manage"},
    "editor": {"app:write", "app:read"},
    "viewer": {"app:read"},
}


def get_effective_permissions(role: str) -> set[str]:
    """获取角色的所有权限（含继承）"""
    permissions = set(ROLE_PERMISSIONS.get(role, set()))
    # 递归获取父角色权限
    for parent_role in ROLE_HIERARCHY.get(role, set()):
        permissions |= get_effective_permissions(parent_role)
    return permissions

# 测试
print(get_effective_permissions("super_admin"))
# {'user:delete', 'system:config', 'app:delete', 'user:manage', 'app:write', 'app:read'}
```

### 2.4 角色互斥（RBAC2）

```python
# 文件：rbac_mutually_exclusive.py
# 角色互斥：财务 + 审计不能同人
MUTUALLY_EXCLUSIVE_ROLES = [
    {"finance", "audit"},  # 财务和审计不能同人
]

def check_role_assignment(user_roles: set[str], new_role: str) -> bool:
    """检查能否给用户分配新角色（基于互斥约束）"""
    candidate = user_roles | {new_role}
    for exclusive_set in MUTUALLY_EXCLUSIVE_ROLES:
        if exclusive_set <= candidate:
            # 如果新角色会导致互斥冲突
            return False
    return True

# 测试
print(check_role_assignment({"employee"}, "finance"))  # True
print(check_role_assignment({"audit"}, "finance"))  # False（互斥）
```

## 3. dify 仓库源码解读

### 3.1 dify 的 RBAC 权限枚举（细粒度）

**文件位置**：`/Users/xu/code/github/dify/api/core/rbac/entities.py`
**核心代码**（行 1-50）：

```python
from enum import StrEnum


class RBACResourceScope(StrEnum):
    """Resource scopes accepted by the ``rbac_permission_required`` decorator.

    ``WORKSPACE`` denotes a workspace-level check that carries no concrete
    resource id; ``APP`` and ``DATASET`` are resource-scoped checks.
    """

    APP = "app"
    DATASET = "dataset"
    WORKSPACE = "workspace"


class RBACResourceWhitelistScope(StrEnum):
    """Whitelist scopes accepted by RBAC app and dataset access config APIs."""

    ALL = "all"
    SPECIFIC = "specific"
    ONLY_ME = "only_me"


class RBACPermission(StrEnum):
    """Permission points (RBAC scenes) checked by ``rbac_permission_required``.

    Each member's value is the scene name forwarded to the RBAC
    ``check-access`` endpoint.
    """

    APP_VIEW_LAYOUT = "app_view_layout"
    APP_TEST_AND_RUN = "app_test_and_run"
    APP_PREVIEW = "app_preview"
    APP_CREATE_AND_MANAGEMENT = "app_create_and_management"
    APP_RELEASE_AND_VERSION = "app_release_and_version"
    APP_IMPORT_EXPORT_DSL = "app_import_export_dsl"
    APP_EDIT = "app_edit"
    APP_MONITOR = "app_monitor"
    APP_TRACING_CONFIG = "app_tracing_config"
    APP_LOG_AND_ANNOTATION = "app_log_and_annotation"
    APP_DELETE = "app_delete"
    APP_ACCESS_CONFIG = "app_access_config"
```

**解读**：
- 第 4-13 行：**资源范围枚举**——APP（资源实例级）/ WORKSPACE（租户级）
- 第 24-42 行：**APP 维度的 12 个权限点**——dify 把"App 操作"拆成 12 个细粒度权限
- 第 41-55 行：DATASET 维度的 14 个权限点（dataset_preview/import_export_dsl 等）
- **设计意图**：dify 把"业务操作"全部拆成原子权限点，运营方可自由组合角色

### 3.2 dify 的 RBAC 装饰器

**文件位置**：`/Users/xu/code/github/dify/api/controllers/common/wraps.py`
**核心代码**（行 68-103）：

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

    Args:
        resource_type: The :class:`RBACResourceScope` member (app/dataset/workspace).
        scene: The :class:`RBACPermission` permission point, e.g. ``RBACPermission.APP_DELETE``.
        resource_required: Whether a concrete resource ID is required.
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
```

**解读**：
- 第 68-79 行：装饰器接受 `resource_type`（APP/DATASET/WORKSPACE）+ `scene`（具体权限点）
- 第 85 行：`RBAC_ENABLED=False` 时装饰器变成 no-op（**这是 dify 的设计**——开源版不带 RBAC，企业版开启）
- 第 92-99 行：调用 `enforce_rbac_access` 把检查委托给企业版的 RBAC 服务
- **设计意图**：把"权限校验"做成可插拔装饰器，开源版直通，企业版接入完整 RBAC 服务

### 3.3 ruoyi 的权限管理服务

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/PermissionServiceImpl.java`
**核心代码**（典型实现）：

```java
@Service
public class PermissionServiceImpl implements PermissionService {

    @Resource
    private RoleMapper roleMapper;

    @Override
    public boolean hasPermission(Long userId, String permission) {
        // 1. 查询用户的所有角色
        List<RoleDO> roles = roleMapper.selectListByUserId(userId);

        // 2. 查询所有角色的权限
        Set<String> userPermissions = new HashSet<>();
        for (RoleDO role : roles) {
            if (role.getStatus() == 0) {  // 0=启用
                userPermissions.addAll(role.getPermissions());
            }
        }

        // 3. 判断权限
        return userPermissions.contains(permission);
    }

    @Override
    public boolean hasAnyPermission(Long userId, String... permissions) {
        for (String perm : permissions) {
            if (hasPermission(userId, perm)) {
                return true;
            }
        }
        return false;
    }
}
```

**解读**：
- 第 9 行：`selectListByUserId` 查询用户的所有角色（多对多）
- 第 15 行：聚合所有角色的权限
- 第 19 行：判断单个权限
- 第 25 行：判断任意权限（OR 语义）
- **设计意图**：ruoyi 把权限校验集中到 `PermissionService`，业务代码通过 `@PreAuthorize("@ss.hasPermission('system:user:list')")` 注解调用

## 4. 关键要点总结

- RBAC 通过"用户-角色-权限"三层模型简化权限管理
- **RBAC1 角色继承**：避免重复配置权限
- **RBAC2 角色约束**：互斥、基数限制、先决条件
- **细粒度权限**：dify 拆 60+ 权限点；**粗粒度**：ruoyi 用菜单权限
- **装饰器/AOP** 是 RBAC 的标准落地方式（`@require_permission`、`@PreAuthorize`）
- 数据权限（ruoyi 特色）：同一菜单权限下，能看到的数据范围不同
- **最小权限原则**：每个角色只授予必要的权限

## 5. 练习题

### 练习 1：基础（必做）

设计一个博客系统的 RBAC：
1. 三个角色：管理员、作者、读者
2. 权限：post:read, post:write, post:delete, comment:write, user:manage
3. 角色权限：管理员=全部、作者=post:read/write/delete + comment、读者=post:read + comment:write
4. 用 SQL 写建表语句 + 测试数据

**参考答案**：见 `solutions/01-rbac-blog.md`

### 练习 2：进阶

解释 dify 和 ruoyi 的权限模型差异：
1. dify 为什么需要 60+ 细粒度权限点？
2. ruoyi 的"数据权限"解决了什么问题？
3. 两种模型各自的适用场景是什么？

### 练习 3：挑战（选做）

实现完整的 RBAC 装饰器：
- `@require_permission("app:write")`
- `@require_role("admin", "editor")`
- `@require_owner(get_app_owner_id)` 资源所有者检查
- 集成到 Flask 应用，含测试用例

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rbac/entities.py`
- `/Users/xu/code/github/dify/api/controllers/common/wraps.py`
- `/Users/xu/code/github/dify/api/services/enterprise/rbac_service.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/PermissionServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/permission/`
- NIST RBAC 标准：https://csrc.nist.gov/projects/role-based-access-control

---

**文档版本**：v1.0
**最后更新**：2026-07-13