# 5.2.3 ACL：访问控制列表

> 理解 ACL 模型，掌握 Linux 文件权限到 API 资源授权的映射。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ACL 的核心结构（主体、资源、操作）
- 理解 ACL 与 RBAC 的核心差异
- 能用 Python 实现一个 ACL 检查器
- 在 dify 中识别 ACL 模式的应用场景

## 📚 前置知识

- 08-rbac.md
- Linux 文件权限基础（rwx）

## 1. 核心概念

### 1.1 ACL 是什么？

ACL（Access Control List）= **每个资源维护一张"谁能对它做什么"的清单**。

```
/etc/passwd 的 ACL:
  - alice: read, write
  - bob: read
  - others: none

app-123 的 ACL:
  - alice: owner
  - bob: editor
  - carol: viewer
```

### 1.2 ACL vs RBAC

| 维度 | ACL | RBAC |
|------|-----|------|
| 权限绑定 | 资源 → 用户 | 角色 → 用户 |
| 适合规模 | 少量资源、少量用户 | 大量用户、角色分明 |
| 复杂度 | O(资源 × 用户) | O(角色 × 权限) |
| 例 | Linux 文件权限 | 企业员工系统 |
| 缺点 | 资源多了维护成本高 | 角色多了也爆炸 |

### 1.3 dify 中的 ACL 模式

dify **没有显式 ACL 表**，但很多地方**借鉴了 ACL 的思想**：

1. **资源所有权检查**：用户是 App 的 owner → 拥有所有权限（`_is_resource_owned_by_current_user`）
2. **Tenant 隔离**：每个资源绑定 `tenant_id`，跨 tenant 直接 404
3. **API Key 绑定**：`ApiToken` 记录 `app_id` + `tenant_id`，只对该 app 有效

## 2. 代码示例

### 2.1 简化版 ACL 实现

```python
from enum import Enum

class Permission(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    SHARE = "share"

class ACE:  # Access Control Entry
    """ACL 中的一条记录。"""
    def __init__(self, subject: str, perms: set[Permission]):
        self.subject = subject
        self.perms = perms

class Resource:
    def __init__(self, name: str, owner: str, aces: list[ACE] = None):
        self.name = name
        self.owner = owner
        self.aces = aces or []

    def check(self, user: str, perm: Permission) -> bool:
        # 1. owner 自动拥有所有权限
        if user == self.owner:
            return True
        # 2. 检查 ACE 列表
        for ace in self.aces:
            if ace.subject == user and perm in ace.perms:
                return True
        return False


# 创建资源：app-123，alice 是 owner，bob 是 editor
app = Resource(
    name="app-123",
    owner="alice",
    aces=[ACE("bob", {Permission.READ, Permission.WRITE})],
)

print(app.check("alice", Permission.DELETE))  # True (owner)
print(app.check("bob", Permission.WRITE))    # True (ACE)
print(app.check("bob", Permission.DELETE))    # False
print(app.check("carol", Permission.READ))   # False
```

### 2.2 常见错误：忽略 owner 默认权限

```python
# ❌ 错误：owner 也要在 ACE 列表里手动加权限
app = Resource("app", owner="alice", aces=[ACE("alice", {Permission.READ})])
app.check("alice", Permission.DELETE)  # 竟然是 False！

# ✅ 正确：owner 隐式拥有所有权限（owner 优先）
```

## 3. dify 仓库源码解读

### 3.1 资源所有权检查（ACL 模式）

**文件位置**：`/Users/xu/code/github/dify/api/controllers/common/wraps.py`
**核心代码**（行 109-132）：

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
    if resource_type == RBACResourceScope.DATASET:
        with sessionmaker(db.engine).begin() as session:
            resource = session.scalar(
                select(Dataset).where(Dataset.id == resource_id, Dataset.tenant_id == tenant_id)
            )
        if resource is None:
            return False
        return resource.created_by == account_id
    return False
```

**解读**：
- 第 4-11 行：APP 类型资源的 owner 检查：查 DB 比对 `created_by == account_id`
- 第 12-19 行：DATASET 资源同样模式：查 DB 比对 owner
- 第 20 行：WORKSPACE 类型暂未实现 owner 短路（返回 False → 走完整 RBAC 检查）
- **ACL 模式**：每个资源（app/dataset）通过 `created_by` 字段绑定 owner，类似 ACL 中的"owner 自动拥有所有权限"
- **设计意图**：owner 是最直接的权限来源，避免把"全部权限"显式塞进 RBAC 策略

### 3.2 资源获取时按 tenant 过滤（行级 ACL）

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
- 第 3-5 行：**同时用 `id` 和 `tenant_id` 过滤**，tenant_id 不匹配直接查不到
- 第 7-8 行：查不到时返回 **404 而不是 403**——避免泄漏"这个资源存在但你无权访问"的信息
- **ACL 模式**：tenant_id 是隐式的 ACL 维度，所有资源查询都按 tenant 隔离
- **设计意图**：用 404 掩盖存在性，防止枚举攻击（attacker 探测哪些 ID 存在）

## 4. 关键要点总结

- ACL = 每个资源维护"谁能做什么"的清单
- **Owner 自动拥有所有权限** 是 ACL 的常见简化
- dify 用 `created_by` 字段实现"资源所有权"，本质是 ACL 思想
- **404 vs 403**：dify 在跨租户访问时返回 404 而非 403，避免资源枚举
- ACL vs RBAC：ACL 灵活但管理成本高，RBAC 抽象但牺牲粒度；现代系统通常两者结合

## 5. 练习题

### 练习 1：基础（必做）

实现一个简化版 ACL `DocumentACL`：每个文档有 owner + ACE 列表，支持 `check(user, perm)` 和 `grant(user, perm)` 两个方法。

### 练习 2：进阶

阅读 `api/controllers/console/apikey.py:57-66`，解释为什么跨租户访问返回 **404 而不是 403**？从安全角度看，这种设计有什么好处？

### 练习 3：挑战（选做）

设计一个支持"权限继承"的 ACL：`/projects/p1/docs/d1` 自动继承 `/projects/p1` 的 ACE 列表（但显式 deny 仍优先）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/common/wraps.py`
- `/Users/xu/code/github/dify/api/controllers/console/apikey.py`
- POSIX ACL：https://man7.org/linux/man-pages/man5/acl.5.html
- AWS S3 ACL：https://docs.aws.amazon.com/AmazonS3/latest/userguide/acls.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13