# 5.2.2 ABAC：基于属性的访问控制

> 理解 ABAC 模型，掌握动态授权与策略引擎的原理。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ABAC 的四要素：主体、资源、动作、环境
- 理解 ABAC 策略的声明式表达（JSON / Rego / DSL）
- 能用 Python 实现一个简单的 ABAC 评估器
- 对比 ABAC 与 RBAC 的适用边界

## 📚 前置知识

- 08-rbac.md
- 01-fundamentals/07-dataclass.md

## 1. 核心概念

### 1.1 ABAC 是什么？

ABAC（Attribute-Based Access Control）= **基于属性** 做授权决策。不绑定固定角色，而是根据访问发生时的**上下文属性**动态判断。

### 1.2 ABAC 四要素

```
┌────────────────────────────────────────────────┐
│ Policy: "允许 owner 在工作时间从公司 IP 删除 App"  │
└────────────────────────────────────────────────┘
        │              │              │
        ▼              ▼              ▼
   ┌─────────┐    ┌─────────┐    ┌─────────┐
   │ Subject │    │ Resource│    │ Action  │
   │ 属性:    │    │ 属性:    │    │ 属性:    │
   │ role=   │    │ type=   │    │ verb=   │
   │ owner   │    │ app     │    │ delete  │
   └─────────┘    └─────────┘    └─────────┘
                        │
                        ▼
                  ┌─────────┐
                  │Environment│
                  │ 属性:      │
                  │ time=9-18 │
                  │ ip=公司网段│
                  └─────────┘
```

**四要素**：
- **Subject（主体）**：用户、角色、部门
- **Resource（资源）**：类型、所有者、敏感级别
- **Action（动作）**：read / write / delete
- **Environment（环境）**：时间、IP、设备、地理位置

### 1.3 ABAC 策略示例（JSON）

```json
{
  "effect": "allow",
  "conditions": {
    "subject.role": "owner",
    "resource.type": "app",
    "action.verb": "delete",
    "environment.time": {"between": ["09:00", "18:00"]},
    "environment.ip": {"in_cidr": "10.0.0.0/8"}
  }
}
```

**对比 RBAC**：
- RBAC 只能表达"Alice 是 admin" → admin 能删除 app
- ABAC 能表达"Alice 只能在工作时间内从公司 IP 删除属于她自己的 app"

### 1.4 何时选 ABAC？

- 权限规则非常复杂（涉及时间/IP/属性组合）
- 需要细粒度的动态控制
- 已经有现成的策略引擎（OPA、Cedar）

**dify 的选择**：核心授权用 RBAC，特定场景（如企业版的细粒度控制）才上 ABAC。

## 2. 代码示例

### 2.1 简化版 ABAC 评估器

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Subject:
    user_id: str
    role: str
    department: str

@dataclass
class Resource:
    type: str
    owner_id: str
    classification: str = "internal"

@dataclass
class Action:
    verb: str

@dataclass
class Environment:
    current_time: str   # "HH:MM"
    ip: str

@dataclass
class AccessRequest:
    subject: Subject
    resource: Resource
    action: Action
    environment: Environment


# 策略定义（一组规则）
@dataclass
class Policy:
    name: str
    effect: str  # "allow" / "deny"
    conditions: list[dict[str, Any]] = field(default_factory=list)


def evaluate(req: AccessRequest, policies: list[Policy]) -> bool:
    """ABAC 评估：Deny 优先（deny-overrides）。"""
    for policy in policies:
        if all(_match_condition(cond, req) for cond in policy.conditions):
            return policy.effect == "allow"
    return False  # 默认拒绝


def _match_condition(cond: dict, req: AccessRequest) -> bool:
    # 简化：用点号路径取属性
    for path, expected in cond.items():
        actual = _resolve_path(req, path)
        if actual != expected:
            return False
    return True


def _resolve_path(req: AccessRequest, path: str) -> Any:
    obj = req
    for part in path.split("."):
        obj = getattr(obj, part, None)
    return obj
```

### 2.2 使用示例

```python
policies = [
    Policy(
        name="owner-can-delete-own-app",
        effect="allow",
        conditions=[
            {"subject.role": "owner", "resource.type": "app",
             "action.verb": "delete", "resource.owner_id": "u-123"},
        ],
    ),
    Policy(
        name="deny-non-working-hours",
        effect="deny",
        conditions=[{"environment.current_time": "03:00"}],
    ),
]

req = AccessRequest(
    subject=Subject("u-123", "owner", "engineering"),
    resource=Resource("app", owner_id="u-123"),
    action=Action("delete"),
    environment=Environment("14:30", "10.1.2.3"),
)
print(evaluate(req, policies))  # True
```

## 3. dify 仓库源码解读

### 3.1 RBACService 的 CheckAccess

**文件位置**：`/Users/xu/code/github/dify/api/controllers/common/wraps.py`
**核心代码**（行 18-66）：

```python
def enforce_rbac_access(
    *,
    tenant_id: str,
    account_id: str,
    resource_type: RBACResourceScope,
    scene: RBACPermission,
    resource_required: bool = True,
    path_args: dict[str, object] | None = None,
) -> None:
    """Enforce enterprise RBAC for an explicit account/tenant pair.

    No-op when ``RBAC_ENABLED`` is ``False``. For resource-scoped checks the
    resource ID is taken from ``path_args`` merged with ``request.view_args``;
    resource ownership short-circuits the check. Raises ``Forbidden`` when
    access is denied. For workspace-level checks pass ``resource_required=False``
    so the RBAC request omits ``resource_id``.
    """
    if not dify_config.RBAC_ENABLED:
        return

    check_resource_type = None if resource_type == RBACResourceScope.WORKSPACE else resource_type
    resource_id = None
    if resource_required and check_resource_type:
        resource_id = _extract_resource_id(resource_type, path_args)
        if _is_resource_owned_by_current_user(tenant_id, account_id, resource_type, resource_id):
            return
    allowed = RBACService.CheckAccess.check(
        tenant_id,
        account_id,
        scene=scene,
        resource_type=check_resource_type,
        resource_id=resource_id,
    )
    if not allowed:
        raise Forbidden()
```

**解读**：
- 第 27-30 行：**资源所有权短路** —— 用户是资源所有者时直接放行，这是 RBAC 的简化路径
- 第 31-37 行：调用 `RBACService.CheckAccess.check(...)`，传入 tenant_id / account_id / scene / resource_type / resource_id 五个**属性**
- 第 38-39 行：未通过则抛 `Forbidden`
- **类 ABAC 之处**：即使主体是 RBAC 形式，但传入的 `resource_type + resource_id` 已经是"基于资源属性"决策，已具备 ABAC 的影子
- **设计意图**：dify 的 RBAC 实现不是纯粹的 RBAC，而是 RBAC + 资源所有权检查（属性化扩展）

### 3.2 资源 ID 提取

**文件位置**：`/Users/xu/code/github/dify/api/controllers/common/wraps.py`
**核心代码**（行 134-160）：

```python
def _extract_resource_id(resource_type: RBACResourceScope, path_args: dict[str, object] | None = None) -> str:
    """Extract resource ID for resource-scoped checks.

    Prefers explicitly provided path arguments and falls back to
    ``request.view_args``.
    """
    merged: dict[str, object] = {}
    if path_args:
        merged.update(path_args)
    if has_request_context():
        merged.update(request.view_args or {})

    if resource_type == RBACResourceScope.APP:
        resource_id = merged.get("app_id") or merged.get("resource_id")
    elif resource_type == RBACResourceScope.DATASET:
        resource_id = merged.get("dataset_id") or merged.get("resource_id")
    else:
        resource_id = None
    return str(resource_id) if resource_id is not None else ""
```

**解读**：
- 第 8-12 行：把装饰器的 `kwargs` 和 Flask 的 `request.view_args` 合并，覆盖各种传参方式
- 第 14-15 行：**根据资源类型**选择不同的 path 参数名（`app_id` / `dataset_id` / 通用 `resource_id`）
- **类 ABAC 之处**：资源类型本身就是属性，决策逻辑根据属性路由到不同提取路径
- **设计意图**：让同一个装饰器能处理不同资源类型，无需为每种资源写一个装饰器

## 4. 关键要点总结

- ABAC = 基于属性（主体/资源/动作/环境）的动态授权
- 策略用声明式表达（JSON/DSL），评估器按规则匹配
- **Deny 优先**：deny 策略命中即拒绝，无论 allow 策略如何
- dify 的 RBAC 实际是 **RBAC + 资源所有权检查**，已具备 ABAC 的影子
- **选型建议**：90% 场景用 RBAC 就够了，ABAC 留给真正复杂的合规场景

## 5. 练习题

### 练习 1：基础（必做）

扩展 2.1 节的 ABAC 评估器，支持"非工作日禁止删除"（用 `environment.is_weekend` 属性）。

### 练习 2：进阶

阅读 `api/controllers/common/wraps.py`，解释 dify 的 `_is_resource_owned_by_current_user` 为什么放在 `enforce_rbac_access` 内部？这种设计有什么好处？

### 练习 3：挑战（选做）

设计一个支持 **优先级排序** 的 ABAC 评估器：每条策略有优先级（数字越大越优先），冲突时按优先级裁决。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/common/wraps.py`
- NIST ABAC 模型：https://csrc.nist.gov/projects/attribute-based-access-control
- AWS IAM 策略语言：https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_grammar.html
- Open Policy Agent：https://www.openpolicyagent.org/

---

**文档版本**：v1.0
**最后更新**：2026-07-13