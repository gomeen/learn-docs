# 8.3 ACL：访问控制列表

> 理解 ACL（Access Control List）的简单直接模型，掌握文件系统与数据库的 ACL 应用。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ACL 的核心思想：把权限直接挂在资源上
- 区分 ACL 与 RBAC 的适用场景
- 在 Linux 文件系统、数据库中识别 ACL
- 在 dify 和 ruoyi 中找到 ACL 的影子

## 📚 前置知识

- 8.1 RBAC
- Linux 文件权限基础
- 数据库基础

## 1. 核心概念

### 1.1 什么是 ACL？

ACL（Access Control List，访问控制列表）把**权限直接挂在资源**上，每条规则说明"谁对资源有什么权限"。

```
资源: /etc/passwd
   │
   └── ACL:
       user:root → rwx
       group:admin → r--
       user:alice → r--
       others → ---
```

### 1.2 ACL vs RBAC

| 维度 | ACL | RBAC |
|------|-----|------|
| 权限挂载 | 资源 | 角色 |
| 查询方向 | 资源 → 用户 | 用户 → 角色 → 权限 |
| 适用规模 | **小规模、细粒度** | 中大规模 |
| 性能 | 快（直接查资源 ACL） | 快（查角色权限） |
| 管理 | **复杂**（每个资源单独配）| **简单**（角色复用）|
| 灵活性 | **极高**（每资源独立）| 中（受角色限制）|

### 1.3 ACL 的典型应用

#### 1.3.1 Linux 文件系统

```bash
# 查看文件 ACL
getfacl /etc/passwd

# 输出：
# user::rwx
# group::r--
# user:alice:r--   # alice 用户只读
# group:dev:r--    # dev 组只读
# mask::r--
# other::---

# 设置 ACL：给 bob 添加读权限
setfacl -m u:bob:r /etc/passwd
```

#### 1.3.2 AWS S3 存储

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::123:user/alice"},
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-bucket/*"
    }
  ]
}
```

#### 1.3.3 网络防火墙

```
规则 1: 允许 192.168.1.0/24 访问 80 端口
规则 2: 拒绝 10.0.0.0/8 访问 22 端口
规则 3: 允许任何 IP 访问 443 端口
```

### 1.4 ACL 在数据库中的实现

#### 模式 A：资源 ID → 权限列表

```sql
-- 文档表的 ACL
CREATE TABLE document_acls (
    document_id BIGINT,
    user_id BIGINT,
    permission VARCHAR(20),  -- read / write / delete
    PRIMARY KEY (document_id, user_id, permission)
);

-- 查询用户对文档的权限
SELECT permission FROM document_acls
WHERE document_id = 123 AND user_id = 456;
```

#### 模式 B：JSON 列存 ACL

```sql
-- 文档表加 ACL 字段
ALTER TABLE documents ADD COLUMN acl JSONB;

-- 示例数据
UPDATE documents SET acl = '[
    {"user_id": 456, "permission": "read"},
    {"user_id": 789, "permission": "write"}
]'::jsonb WHERE id = 123;
```

### 1.5 dify 和 ruoyi 中的 ACL

| 项目 | ACL 元素 |
|------|---------|
| **dify** | App/Dataset 的访问白名单（用户列表）|
| **ruoyi** | 资源权限（自定义角色直接绑定菜单/按钮）|

## 2. 代码示例

### 2.1 基础 ACL 数据库设计

```sql
-- 文件: acl_schema.sql
-- 经典 ACL 三张表

-- 资源表
CREATE TABLE documents (
    id BIGINT PRIMARY KEY,
    title VARCHAR(200),
    owner_id BIGINT NOT NULL,           -- 创建者
    is_public BOOLEAN DEFAULT FALSE,   -- 是否公开
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ACL 表（核心）
CREATE TABLE document_acls (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    principal_type VARCHAR(20) NOT NULL,  -- 'user' / 'role' / 'group'
    principal_id BIGINT NOT NULL,
    permission VARCHAR(20) NOT NULL,      -- 'read' / 'write' / 'delete' / 'share'
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by BIGINT,
    UNIQUE (document_id, principal_type, principal_id, permission)
);

CREATE INDEX idx_acl_lookup ON document_acls(document_id, principal_type, principal_id);
```

### 2.2 Python ACL 权限检查

```python
# 文件：acl_check.py
# ACL 权限检查实现
import enum
from typing import Optional


class Permission(str, enum.Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    SHARE = "share"


# 模拟数据库
DOCUMENTS = {
    1: {"title": "项目计划", "owner_id": 100, "is_public": False},
    2: {"title": "公开文档", "owner_id": 100, "is_public": True},
}

# document_id -> [(principal, permission), ...]
DOCUMENT_ACLS = {
    1: [
        (("user", 200), Permission.READ),
        (("user", 200), Permission.WRITE),
        (("role", 1), Permission.READ),  # 管理员角色
    ],
}


def check_acl(
    user_id: int,
    user_role_ids: list[int],
    document_id: int,
    required: Permission,
) -> bool:
    """检查用户对文档的权限

    顺序：
    1. 公开资源 → read 权限允许
    2. 资源所有者 → 所有权限
    3. 检查 ACL 列表（user 级 → role 级）
    """
    doc = DOCUMENTS.get(document_id)
    if not doc:
        return False

    # 1. 公开资源（仅 read）
    if doc["is_public"] and required == Permission.READ:
        return True

    # 2. 资源所有者
    if doc["owner_id"] == user_id:
        return True

    # 3. 检查 ACL
    acls = DOCUMENT_ACLS.get(document_id, [])
    for (principal_type, principal_id), perm in acls:
        if perm != required:
            continue
        if principal_type == "user" and principal_id == user_id:
            return True
        if principal_type == "role" and principal_id in user_role_ids:
            return True

    return False


# 测试
print(check_acl(user_id=200, user_role_ids=[], document_id=1, required=Permission.READ))
# True（user 200 在 ACL 中）
print(check_acl(user_id=999, user_role_ids=[1], document_id=1, required=Permission.READ))
# True（role 1 在 ACL 中）
print(check_acl(user_id=999, user_role_ids=[], document_id=1, required=Permission.DELETE))
# False（无权限）
print(check_acl(user_id=100, user_role_ids=[], document_id=1, required=Permission.DELETE))
# True（资源所有者）
```

### 2.3 ACL 授予与撤销

```python
# 文件：acl_grant_revoke.py
# ACL 授权与撤销
def grant_permission(
    document_id: int,
    principal_type: str,
    principal_id: int,
    permission: Permission,
    granted_by: int,
) -> None:
    """授予权限"""
    # 1. 检查授权者权限（只有 owner 或 share 权限能授权）
    doc = DOCUMENTS[document_id]
    if doc["owner_id"] != granted_by:
        if not check_acl(granted_by, [], document_id, Permission.SHARE):
            raise PermissionError("no share permission")

    # 2. 添加 ACL
    DOCUMENT_ACLS.setdefault(document_id, []).append(
        ((principal_type, principal_id), permission)
    )


def revoke_permission(
    document_id: int,
    principal_type: str,
    principal_id: int,
    permission: Permission,
    revoked_by: int,
) -> None:
    """撤销权限"""
    doc = DOCUMENTS[document_id]
    if doc["owner_id"] != revoked_by:
        raise PermissionError("only owner can revoke")

    acls = DOCUMENT_ACLS.get(document_id, [])
    DOCUMENT_ACLS[document_id] = [
        acl for acl in acls if acl != ((principal_type, principal_id), permission)
    ]
```

### 2.4 ACL 性能优化（缓存 + 反向索引）

```python
# 文件：acl_cached.py
# 带缓存的 ACL 检查
from functools import lru_cache


@lru_cache(maxsize=10000)
def check_acl_cached(user_id: int, document_id: int, permission: str) -> bool:
    """缓存的 ACL 检查"""
    # 当 ACL 变更时调用 check_acl_cached.cache_clear() 失效缓存
    return check_acl(user_id, [], document_id, Permission(permission))


def get_user_documents(user_id: int) -> list[int]:
    """反向索引：用户能访问的所有文档

    ACL 表通常是"文档 → 用户"的方向，但业务经常需要"用户 → 文档"
    用反向索引（user_documents 表）优化
    """
    docs = []
    for doc_id, doc in DOCUMENTS.items():
        if doc["is_public"]:
            docs.append(doc_id)
            continue
        if doc["owner_id"] == user_id:
            docs.append(doc_id)
            continue
        # 检查 ACL
        for (ptype, pid), _ in DOCUMENT_ACLS.get(doc_id, []):
            if ptype == "user" and pid == user_id:
                docs.append(doc_id)
                break
    return docs
```

## 3. dify 仓库源码解读

### 3.1 dify 的 ACL：Dataset 白名单

**文件位置**：`/Users/xu/code/github/dify/api/services/dataset_service.py`（典型 ACL 实现）
**核心代码**（典型 ACL 查询）：

```python
def check_dataset_permission(dataset_id: str, user_id: str, permission: str) -> bool:
    """检查用户对数据集的权限"""
    # 1. 检查是否是所有者
    dataset = db.session.query(Dataset).filter_by(id=dataset_id).first()
    if not dataset:
        return False
    if dataset.created_by == user_id:
        return True  # 所有者有所有权限

    # 2. 检查 ACL（用户级）
    user_acl = db.session.query(DatasetAcl).filter_by(
        dataset_id=dataset_id,
        principal_type="user",
        principal_id=user_id,
    ).first()
    if user_acl and permission in user_acl.permissions:
        return True

    # 3. 检查 ACL（角色级）
    user_role_ids = get_user_role_ids(user_id)
    role_acl = db.session.query(DatasetAcl).filter(
        DatasetAcl.dataset_id == dataset_id,
        DatasetAcl.principal_type == "role",
        DatasetAcl.principal_id.in_(user_role_ids),
    ).all()
    if role_acl and permission in [r.permission for r in role_acl]:
        return True

    return False
```

**解读**：
- 第 1-7 行：所有者直接通过（**Owner 拥有所有权限**是 ACL 的经典模式）
- 第 10-14 行：**用户级 ACL** —— 直接给特定用户授权
- 第 17-23 行：**角色级 ACL** —— 给角色授权，再匹配用户的角色
- **设计意图**：dify 把"数据集访问控制"做成"两阶段 ACL"——先看 Owner，再看 ACL 表

### 3.2 ruoyi 的资源权限（菜单/按钮级 ACL）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/PermissionServiceImpl.java`
**核心代码**（典型菜单 ACL）：

```java
@Service
public class PermissionServiceImpl implements PermissionService {

    @Override
    public Set<String> getUserMenuPermissions(Long userId) {
        // 1. 查询用户的所有角色
        List<RoleDO> roles = roleMapper.selectListByUserId(userId);

        // 2. 聚合菜单权限
        Set<String> menuPermissions = new HashSet<>();
        for (RoleDO role : roles) {
            if (role.getStatus() == 0) {
                // 每个角色关联多个菜单
                List<MenuDO> menus = menuMapper.selectListByRoleId(role.getId());
                for (MenuDO menu : menus) {
                    menuPermissions.add(menu.getPermission());  // 例如 "system:user:list"
                }
            }
        }
        return menuPermissions;
    }
}
```

**菜单的 ACL 结构**：

```sql
-- 角色-菜单 ACL 表
CREATE TABLE system_role_menu (
    role_id BIGINT,
    menu_id BIGINT,
    PRIMARY KEY (role_id, menu_id)
);

-- 菜单表（每菜单对应一个权限标识）
CREATE TABLE system_menu (
    id BIGINT PRIMARY KEY,
    name VARCHAR(50),
    permission VARCHAR(100),  -- 例如 "system:user:list"
    type CHAR(1),             -- M=目录, C=菜单, F=按钮
    parent_id BIGINT
);
```

**解读**：
- 第 9-19 行：聚合用户所有角色的菜单权限
- **本质是 ACL**：`system_role_menu` 表把"权限（菜单）"挂在"角色"上，每个菜单就是 ACL 的一条规则
- **菜单/按钮权限**是 ruoyi 的核心：通过不同角色挂不同菜单，控制前端按钮可见性 + 后端接口权限
- **设计意图**：把"权限点"做成细粒度菜单/按钮，运营方通过勾选菜单配置角色

## 4. 关键要点总结

- ACL 把权限挂在**资源**上（Owner + 多个 ACL 条目）
- **Owner 自动拥有所有权限**（ACL 经典模式）
- 适用场景：资源数量有限、需要细粒度单资源权限
- **不适合大规模资源**（每个资源都要配 ACL）
- **混合模式**：ACL 处理"特殊访问"，RBAC 处理"通用权限"
- dify 用 ACL 控制 Dataset/App 访问，ruoyi 用 ACL 控制菜单/按钮
- **Linux 文件、AWS S3、网络防火墙**都是经典 ACL 应用

## 5. 练习题

### 练习 1：基础（必做）

实现一个 ACL 系统：
1. 三张表：documents / users / document_acls
2. 函数 `check_acl(user_id, doc_id, permission)` 检查权限
3. 函数 `grant(doc_id, user_id, permission, granted_by)` 授予权限
4. 函数 `revoke(doc_id, user_id, permission, revoked_by)` 撤销权限
5. 单元测试覆盖正常和异常情况

**参考答案**：见 `solutions/03-acl-system.md`

### 练习 2：进阶

ACL 和 RBAC 各自的优劣是什么？给三个真实业务场景，分别说明该用 ACL、RBAC、还是 ACL+RBAC 混合。

### 练习 3：挑战（选做）

为 dify 实现一个"文档分享 ACL"功能：
- 用户可把自己的 App 分享给指定用户（read/write 权限）
- 实现分享链接（带 token，过期 24 小时）
- 实现 `revoke` 主动撤销分享
- 用 Redis 缓存常用 ACL 检查结果

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/dataset_service.py`（典型 ACL 实现）
- `/Users/xu/code/github/dify/api/services/app_service.py`（App 权限）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/PermissionServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/dataobject/permission/`
- Linux ACL 文档：https://www.redhat.com/sysadmin/linux-access-control-lists
- AWS S3 ACL 文档：https://docs.aws.amazon.com/AmazonS3/latest/userguide/acls.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13