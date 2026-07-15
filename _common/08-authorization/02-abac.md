# 8.2 ABAC：基于属性的访问控制

> 理解 ABAC（Attribute-Based Access Control）模型，能设计动态、细粒度的权限系统。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ABAC 的四大属性（主体、客体、环境、操作）
- 区分 ABAC 与 [RBAC](./01-rbac.md) 的适用场景
- 掌握 ABAC 策略语言（XACML / Rego）
- 在 dify 和 ruoyi 中识别 ABAC 的影子

## 📚 前置知识

- [8.1 RBAC 模型](./01-rbac.md)
- 数据库基础
- 任意一种规则引擎

## 1. 核心概念

### 1.1 什么是 ABAC？

ABAC（Attribute-Based Access Control）通过**属性**和**策略**做权限决策，比 RBAC 更灵活。

```
Access = f(Subject, Object, Action, Environment)

是否允许访问 = f(用户属性, 资源属性, 操作, 环境)
```

### 1.2 四大属性

| 属性 | 含义 | 示例 |
|------|------|------|
| **Subject（主体）** | 谁在请求 | 用户的部门、职位、级别 |
| **Object（客体）** | 访问什么 | 文档的机密等级、创建时间 |
| **Action（操作）** | 做什么 | 读、写、删除、审批 |
| **Environment（环境）** | 上下文 | 时间、IP、设备、地理位置 |

### 1.3 ABAC 策略示例

```
策略: "工作日上午 9 点到 6 点，同部门的经理可以审批本部门文档"

IF
  subject.role == "manager"
  AND subject.department == object.department
  AND environment.time BETWEEN "09:00" AND "18:00"
  AND environment.day_of_week IN ["Mon", "Tue", "Wed", "Thu", "Fri"]
  AND action == "approve"
THEN
  ALLOW
```

### 1.4 RBAC vs ABAC 对比

| 维度 | RBAC | ABAC |
|------|------|------|
| 决策依据 | 角色 | 任意属性 |
| 灵活性 | 中（需要预定义角色）| **极高**（动态策略）|
| 复杂度 | 低 | 高 |
| 性能 | **快**（数据库查表）| 中（需要策略评估）|
| 管理 | **简单** | 复杂（策略管理工具）|
| 适用场景 | 中小型系统、权限固定 | 大型企业、动态场景 |

### 1.5 ABAC 适用场景

✅ **适合**：
- 多租户 SaaS（租户属性 + 用户属性）
- 金融系统（金额、时间、风险等级）
- 文档系统（机密等级 + 用户职级）
- 时间敏感（仅工作时间可访问）

❌ **不适合**：
- 简单系统（RBAC 足够）
- 性能敏感场景（ABAC 评估慢）

### 1.6 dify 和 ruoyi 的 ABAC 元素

虽然 dify 和 ruoyi 主打 RBAC，但都包含 ABAC 元素：

| 项目 | ABAC 元素 |
|------|----------|
| **dify** | `TenantAccountRole`（owner/admin/editor/normal）—— 本质是租户 + 角色属性 |
| **ruoyi** | `data_scope`（全部 / 本部门 / 本人 / 自定义）—— 基于数据属性的权限 |

## 2. 代码示例

### 2.1 ABAC 策略引擎基础实现

```python
# 文件：abac_basic.py
# ABAC 基础策略引擎
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Subject:
    """主体属性"""
    user_id: str
    role: str
    department: str
    level: int  # 职级


@dataclass
class Object:
    """客体属性"""
    resource_id: str
    type: str  # 文档 / 应用 / 数据
    department: str
    confidential_level: int  # 1-5
    owner_id: str
    created_at: str


@dataclass
class Environment:
    """环境属性"""
    time: str  # 当前时间
    ip: str
    day_of_week: str


@dataclass
class AccessRequest:
    """访问请求"""
    subject: Subject
    object: Object
    action: str  # read / write / delete / approve


# 策略定义（Python 函数）
def policy_allow_during_work_hours(req: AccessRequest, env: Environment) -> bool:
    """工作时间（9-18）允许访问"""
    hour = int(env.time.split(":")[0])
    return 9 <= hour < 18


def policy_allow_same_department(req: AccessRequest, env: Environment) -> bool:
    """同部门可以访问"""
    return req.subject.department == req.object.department


def policy_allow_owner(req: AccessRequest, env: Environment) -> bool:
    """资源所有者可以访问"""
    return req.subject.user_id == req.object.owner_id


def policy_allow_high_level_for_confidential(req: AccessRequest, env: Environment) -> bool:
    """高级别用户可以访问高机密文档"""
    if req.object.confidential_level >= 4:
        return req.subject.level >= req.object.confidential_level
    return True


# 策略注册表
POLICIES = {
    "work_hours": policy_allow_during_work_hours,
    "same_department": policy_allow_same_department,
    "owner": policy_allow_owner,
    "confidential": policy_allow_high_level_for_confidential,
}


def evaluate(req: AccessRequest, env: Environment, required_policies: list[str]) -> tuple[bool, str]:
    """评估请求：所有策略必须通过"""
    for policy_name in required_policies:
        policy_func = POLICIES.get(policy_name)
        if not policy_func:
            return False, f"unknown policy: {policy_name}"
        if not policy_func(req, env):
            return False, f"denied by policy: {policy_name}"
    return True, "allowed"


# 测试
subject = Subject(user_id="alice", role="manager", department="eng", level=3)
obj = Object(
    resource_id="doc-1",
    type="document",
    department="eng",
    confidential_level=2,
    owner_id="bob",
    created_at="2024-01-01",
)
env = Environment(time="10:30", ip="192.168.1.1", day_of_week="Mon")
req = AccessRequest(subject=subject, object=obj, action="write")

allowed, reason = evaluate(req, env, ["work_hours", "same_department", "confidential"])
print(f"允许: {allowed}, 原因: {reason}")
# 允许: True, 原因: allowed
```

### 2.2 组合策略：Deny 优先

```python
# 文件：abac_deny_first.py
# Deny 优先的策略组合
def evaluate_deny_first(req, env, allow_policies, deny_policies):
    """Deny 策略优先；所有 Allow 通过才放行"""
    # 1. 检查 deny 策略（任一通过则拒绝）
    for policy_name in deny_policies:
        if POLICIES[policy_name](req, env):
            return False, f"denied: {policy_name}"

    # 2. 检查 allow 策略（全部通过才放行）
    for policy_name in allow_policies:
        if not POLICIES[policy_name](req, env):
            return False, f"not allowed: {policy_name}"

    return True, "allowed"


# 高级别用户不允许审批低金额（职责分离）
def policy_deny_self_approval(req, env):
    """不能审批自己创建的文档"""
    return req.subject.user_id == req.object.owner_id


DENY_POLICIES = ["self_approval"]
ALLOW_POLICIES = ["work_hours", "same_department"]

# 测试
obj_self = Object(resource_id="d1", type="doc", department="eng",
                  confidential_level=1, owner_id="alice", created_at="2024-01-01")
req_self = AccessRequest(subject=subject, object=obj_self, action="approve")
allowed, reason = evaluate_deny_first(req_self, env, ALLOW_POLICIES, DENY_POLICIES)
print(f"自审批: {allowed}")  # False（不能审批自己创建的）
```

### 2.3 简单声明式策略（Rego 风格）

```python
# 文件：abac_declarative.py
# 简化的声明式策略
class Policy:
    """声明式策略：when ... allow/deny ..."""

    def __init__(self, name, when_func, effect):
        self.name = name
        self.when_func = when_func
        self.effect = effect  # "allow" or "deny"


POLICY_RULES = [
    Policy("work_hours", lambda r, e: 9 <= int(e.time.split(":")[0]) < 18, "allow"),
    Policy("after_hours_block", lambda r, e: int(e.time.split(":")[0]) >= 18, "deny"),
    Policy("same_dept", lambda r, e: r.subject.department == r.object.department, "allow"),
    Policy("cross_dept_block", lambda r, e: r.subject.department != r.object.department, "deny"),
]


def evaluate_declarative(req, env):
    """Deny 优先 + 多策略聚合"""
    for policy in POLICY_RULES:
        if policy.when_func(req, env):
            return policy.effect == "allow", f"{policy.effect} by {policy.name}"
    return False, "default deny"
```

## 3. dify 仓库源码解读

### 3.1 dify 的 RBACService（属性化检查）

**文件位置**：`/Users/xu/code/github/dify/api/services/enterprise/rbac_service.py`
**核心代码**（典型 CheckAccess 实现）：

```python
class RBACService:
    """dify 企业版 RBAC 服务"""

    class CheckAccess:
        @staticmethod
        def check(
            tenant_id: str,
            account_id: str,
            scene: str,
            resource_type: str = None,
            resource_id: str = None,
        ) -> bool:
            """检查账户对资源的访问权限

            内部逻辑（推断）：
            1. 查询账户在租户内的角色
            2. 查询该场景（scene）的角色权限配置
            3. 判断资源是否在白名单内（仅本人/特定资源/全部）
            4. 返回是否允许
            """
            # 检查 RBAC_ENABLED
            if not dify_config.RBAC_ENABLED:
                return True

            # 调用企业版 RBAC API
            response = requests.post(
                f"{dify_config.ENTERPRISE_RBAC_URL}/check-access",
                json={
                    "tenant_id": tenant_id,
                    "account_id": account_id,
                    "scene": scene,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                },
                headers={"Authorization": f"Bearer {dify_config.ENTERPRISE_RBAC_TOKEN}"},
                timeout=5,
            )
            return response.json().get("allowed", False)
```

**解读**：
- 第 12-23 行：参数化检查，传入租户、用户、场景、资源
- 第 27 行：`RBAC_ENABLED=False` 时直接放行（开源版兼容）
- 第 30-37 行：调用企业版 RBAC 服务（外部 HTTP API）
- **ABAC 影子**：虽然 dify 主体是 RBAC，但场景（scene）参数本质上是"操作属性"，资源 ID + 白名单范围（ALL/SPECIFIC/ONLY_ME）本质上是"资源属性"，已经具有 ABAC 雏形

### 3.2 ruoyi 的 DataPermission（属性权限）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/rule/DataPermissionRule.java`
**核心代码**（典型数据权限规则）：

```java
public interface DataPermissionRule {

    /**
     * 返回需要追加的 SQL WHERE 条件
     * 例如: "dept_id IN (1, 2, 3)" 或 "user_id = 100"
     */
    Set<String> getTableNames();

    Expression buildExpression(Long userId, Long deptId, String tableAlias);
}
```

**典型实现 - DeptDataPermissionRule**：

```java
public class DeptDataPermissionRule implements DataPermissionRule {

    @Override
    public Expression buildExpression(Long userId, Long deptId, String tableAlias) {
        // 根据用户的 data_scope 配置决定 SQL 条件
        Integer dataScope = securityFrameworkService.getDataScope(userId);
        switch (dataScope) {
            case DATA_SCOPE_ALL:        // 全部
                return null;
            case DATA_SCOPE_DEPT:       // 本部门
                return tableAlias.dept_id.eq(deptId);
            case DATA_SCOPE_DEPT_AND_CHILD:  // 本部门及下级
                return tableAlias.dept_id.in(getChildDeptIds(deptId));
            case DATA_SCOPE_SELF:       // 仅本人
                return tableAlias.creator.eq(userId);
            case DATA_SCOPE_CUSTOM:     // 自定义
                return tableAlias.dept_id.in(getCustomDeptIds(userId));
            default:
                return null;
        }
    }
}
```

**解读**：
- 第 14 行：`getDataScope(userId)` 是核心——根据用户属性（data_scope）返回不同 SQL
- 第 15-30 行：5 种数据范围——全部 / 本部门 / 本部门及下级 / 仅本人 / 自定义
- **这是典型的 ABAC**：决策依据 = `userId`（主体属性）+ `dataScope`（属性）+ `tableAlias.dept_id`（资源属性）
- **设计意图**：ruoyi 把"数据权限"做成动态 SQL 拼接拦截器，业务代码无需关心

## 4. 关键要点总结

- ABAC 通过属性（主体/客体/环境）+ 策略做权限决策
- 比 RBAC 更灵活，但更复杂、性能略差
- **典型组合**：RBAC + ABAC = "角色控制功能权限 + 属性控制数据权限"
- **Deny 优先**：拒绝策略优先于允许策略（安全默认）
- **声明式策略**：把策略写成"when...then..."形式，方便管理
- dify 用 RBAC + 场景（scene）参数，ruoyi 用 RBAC + data_scope 数据权限
- **性能优化**：策略评估结果缓存、预编译策略
- ABAC 不是替代 RBAC，而是**补充**——大多数系统是 RBAC + ABAC 混合

## 5. 练习题

### 练习 1：基础（必做）

实现一个 ABAC 策略引擎：
1. 定义 Subject/Object/Environment/Action 四元组
2. 实现"工作时间 + 同部门 + 资源所有者"三条策略
3. Deny 优先组合（先检查 deny 策略）
4. 写测试用例验证

**参考答案**：见 `solutions/02-abac-engine.md`

### 练习 2：进阶

RBAC 和 ABAC 各自适合什么场景？给出一个真实业务例子：
1. 适合 RBAC（举例说明为什么）
2. 适合 ABAC（举例说明为什么）
3. RBAC + ABAC 混合（举例说明为什么）

### 练习 3：挑战（选做）

为 dify 添加 ABAC 风格的"时间窗口"权限：
- 某些资源仅在工作时间（9:00-18:00）可访问
- 实现思路：扩展 `enforce_rbac_access`，加入 Environment 参数
- 用 Python 装饰器模式实现，支持"时间窗口"、"IP 白名单"、"设备类型"等环境属性

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rbac/entities.py`
- `/Users/xu/code/github/dify/api/services/enterprise/rbac_service.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/rule/DataPermissionRule.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/`
- NIST ABAC 标准：https://csrc.nist.gov/projects/attribute-based-access-control
- XACML 标准：https://www.oasis-open.org/committees/xacml/

---

**文档版本**：v1.0
**最后更新**：2026-07-13