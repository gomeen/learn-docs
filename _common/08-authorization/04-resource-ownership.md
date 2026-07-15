# 8.4 资源所有权与租户隔离

> 理解"资源所有权"作为权限校验的第一道防线，掌握多租户隔离的核心模式。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解"资源所有权"作为最基础的权限控制
- 掌握 Owner / Tenant 双层隔离模型
- 识别 dify 和 ruoyi 中的资源所有权设计
- 实现租户隔离避免数据串租

## 📚 前置知识

- [8.1 RBAC](./01-rbac.md)
- [8.3 ACL](./03-acl.md)
- 数据库基础
- 多租户详解见 [05-multi-tenant](./05-multi-tenant.md)

## 1. 核心概念

### 1.1 什么是资源所有权？

资源所有权（Resource Ownership）：资源的**创建者/拥有者**对该资源拥有最高权限。

```
用户 Alice 创建文档 doc-1
   ↓
Alice 自动拥有 doc-1 的所有权限（读、写、删除、分享）
   ↓
其他用户访问 doc-1 → 必须通过 ACL/RBAC 校验
```

**为什么需要所有权**：
- 创建者自然应该能管理自己创建的资源
- 提供"超级用户"逃生通道（绕过 ACL）
- 简化权限模型：默认 Owner = 全部权限

### 1.2 所有权 vs ACL vs RBAC

| 维度 | 所有权 | [ACL](./03-acl.md) | [RBAC](./01-rbac.md) |
|------|--------|-----|------|
| 粒度 | 单资源 | 单资源 | 角色级 |
| 默认权限 | **Owner 全权** | 按 ACL 条目 | 按角色配置 |
| 适用 | **通用** | 细粒度共享 | 功能权限 |
| 实现 | 数据库加 `owner_id` 字段 | 单独 ACL 表 | 角色-权限表 |

**最佳实践**：三者组合
- Owner 自动全权
- ACL 处理"特定共享"（把文档分享给某人）
- RBAC 处理"通用权限"（管理员能看所有）

### 1.3 什么是租户隔离？

租户隔离（Tenant Isolation）：多租户 SaaS 中，每个租户只能看到/操作自己的数据。

```
租户 A 的用户 alice 创建文档 doc-1
租户 B 的用户 bob 创建文档 doc-2

Alice 不能访问 doc-2（即使 RBAC 允许）
Bob 不能访问 doc-1（即使 RBAC 允许）
```

### 1.4 租户隔离的三种实现方式

#### 1.4.1 应用层过滤（每查询带 tenant_id）

```python
# 文件: app.py
# ✅ 应用层过滤：每条查询都带 tenant_id
documents = db.query("SELECT * FROM documents WHERE tenant_id = ?", current_tenant_id)
```

**优点**：单库、单部署，简单
**缺点**：必须**每个查询都加**，容易遗漏 → 数据泄露

#### 1.4.2 数据库视图 / Schema 隔离

```sql
-- 每个租户一个 schema
CREATE SCHEMA tenant_a;
CREATE SCHEMA tenant_b;

-- tenant_a 下的表
CREATE TABLE tenant_a.documents (...);
CREATE TABLE tenant_b.documents (...);
```

**优点**：物理隔离，更安全
**缺点**：维护成本高，难做跨租户分析

#### 1.4.3 数据库级隔离（每租户独立数据库）

```
postgres://primary/tenant_a_db
postgres://primary/tenant_b_db
```

**优点**：最强隔离
**缺点**：成本高，迁移复杂

### 1.5 dify 和 ruoyi 的资源所有权

| 项目 | 所有权模型 | 租户隔离 |
|------|----------|---------|
| **dify** | 每个资源有 `tenant_id` + `created_by` | 应用层强制 |
| **ruoyi** | 实体有 `creator` + `dept_id` | 拦截器强制 |

## 2. 代码示例

### 2.1 资源所有权基础检查

```python
# 文件：ownership_check.py
# 资源所有权基础检查

# 模拟数据库
DOCUMENTS = {
    1: {"title": "doc1", "owner_id": 100, "tenant_id": "t1"},
    2: {"title": "doc2", "owner_id": 200, "tenant_id": "t1"},
    3: {"title": "doc3", "owner_id": 300, "tenant_id": "t2"},
}


class DocumentService:
    """文档服务：实现所有权检查"""

    def get_document(self, doc_id: int, current_user: dict) -> dict | None:
        """获取文档（强制租户隔离）"""
        doc = DOCUMENTS.get(doc_id)
        if not doc:
            return None

        # ✅ 第一道防线：租户隔离
        if doc["tenant_id"] != current_user["tenant_id"]:
            return None  # 不抛异常，避免泄露文档存在性

        return doc

    def update_document(self, doc_id: int, current_user: dict, new_data: dict) -> bool:
        """更新文档（需要所有权或 ACL）"""
        doc = self.get_document(doc_id, current_user)
        if not doc:
            raise PermissionError("document not found")

        # ✅ 第二道防线：所有权检查
        if doc["owner_id"] != current_user["user_id"]:
            # 这里可以再检查 ACL/RBAC
            if not self._check_acl(doc_id, current_user["user_id"], "write"):
                raise PermissionError("no write permission")

        # 执行更新
        doc.update(new_data)
        return True

    def delete_document(self, doc_id: int, current_user: dict) -> bool:
        """删除文档（仅所有者或管理员）"""
        doc = self.get_document(doc_id, current_user)
        if not doc:
            raise PermissionError("document not found")

        # 删除权限比更新更严格：通常只允许所有者
        if doc["owner_id"] != current_user["user_id"]:
            if "admin" not in current_user.get("roles", []):
                raise PermissionError("only owner or admin can delete")

        del DOCUMENTS[doc_id]
        return True
```

### 2.2 SQLAlchemy 租户隔离拦截器

```python
# 文件：tenant_isolation.py
# SQLAlchemy 拦截器自动加 tenant_id 过滤
from sqlalchemy import event
from sqlalchemy.orm import Session, Query


class TenantIsolatedSession(Session):
    """自动加 tenant_id 过滤的 Session"""

    def __init__(self, *args, tenant_id: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant_id = tenant_id

    def query(self, *entities, **kwargs):
        # 重写 query 自动加 tenant_id 过滤
        q = super().query(*entities, **kwargs)
        # 监听 query 编译
        return q


# 用事件监听器实现
@event.listens_for(Query, "before_compile", retval=True)
def add_tenant_filter(query):
    """在 SQL 编译前自动加 WHERE tenant_id = ?"""
    # 检查是否有 TenantMixin
    for entity in query.column_descriptions:
        if entity["entity"] and hasattr(entity["entity"], "tenant_id"):
            query = query.filter(entity["entity"].tenant_id == current_tenant_id)
    return query
```

### 2.3 Tenant Context（线程级租户）

```python
# 文件：tenant_context.py
# 线程级租户上下文
import contextvars
from contextlib import contextmanager


# 用 contextvars 在异步环境中也安全
current_tenant_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_tenant_id"
)


def set_tenant(tenant_id: str):
    """设置当前租户"""
    return current_tenant_id.set(tenant_id)


def get_tenant() -> str:
    """获取当前租户"""
    return current_tenant_id.get()


@contextmanager
def tenant_scope(tenant_id: str):
    """租户作用域（with 语句）"""
    token = set_tenant(tenant_id)
    try:
        yield
    finally:
        current_tenant_id.reset(token)


# 在 Web 框架中使用
@app.before_request
def setup_tenant():
    """每个请求设置租户"""
    tenant_id = resolve_tenant_from_request()  # 从 Header / JWT 解析
    set_tenant(tenant_id)


# 在 Service 中自动注入
def list_documents(session: Session):
    """查询文档：自动加租户过滤"""
    return session.query(Document).filter(
        Document.tenant_id == get_tenant()  # ✅ 自动用当前租户
    ).all()
```

### 2.4 防止跨租户访问（防御性编程）

```python
# 文件：cross_tenant_defense.py
# 防御性编程：防止跨租户访问

def safe_get_document(doc_id: int, current_user: dict):
    """安全的文档获取（多层校验）"""
    doc = db.query(Document).filter_by(id=doc_id).first()

    if not doc:
        return None

    # ✅ 第一道：租户隔离
    if doc.tenant_id != current_user["tenant_id"]:
        # 记录异常日志（可能是攻击）
        logger.warning(
            f"cross-tenant access attempt: user={current_user['user_id']} "
            f"tenant={current_user['tenant_id']} doc_tenant={doc.tenant_id}"
        )
        # ✅ 不抛 403（避免泄露文档存在性），统一返回 404
        raise NotFoundError()

    # ✅ 第二道：所有权或 ACL 检查
    if doc.owner_id != current_user["user_id"]:
        if not has_acl_permission(doc.id, current_user["user_id"], "read"):
            raise PermissionError("no read permission")

    return doc
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Tenant Context（多租户核心）

**文件位置**：`/Users/xu/code/github/dify/api/libs/login.py`
**核心代码**（行 39-49）：

```python
def current_account_with_tenant() -> tuple[Account, str]:
    """
    Resolve the underlying account for the current user proxy and ensure tenant context exists.
    Allows tests to supply plain Account mocks without the LocalProxy helper.
    """
    user = _resolve_current_user()

    if not isinstance(user, Account):
        raise ValueError("current_user must be an Account instance")
    assert user.current_tenant_id is not None, "The tenant information should be loaded."
    return user, user.current_tenant_id
```

**解读**：
- 第 47 行：返回 `(Account, tenant_id)` 元组——**所有业务代码同时拿到用户和租户**
- 第 48 行：**强制断言租户已加载**——任何业务接口都不允许"无租户上下文"
- **设计意图**：dify 通过类型签名强制每个业务接口接受租户参数，**编译期/调用期防止遗漏**

### 3.2 dify 的 TenantAccountRole（用户-租户多对多）

**文件位置**：`/Users/xu/code/github/dify/api/models/account.py`
**核心代码**（典型模型定义）：

```python
class TenantAccountJoin(db.Model):
    """用户-租户关联表"""
    __tablename__ = "tenant_account_joins"

    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    account_id = Column(UUID, ForeignKey("accounts.id"), nullable=False)
    role = Column(String(16), nullable=False)  # owner/admin/editor/normal
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "account_id", name="uk_tenant_account"),
    )


class TenantAccountRole(str, enum.Enum):
    """用户在租户内的角色"""
    OWNER = "owner"     # 所有者
    ADMIN = "admin"     # 管理员
    EDITOR = "editor"   # 编辑
    NORMAL = "normal"   # 普通成员


class Tenant(db.Model):
    """租户表"""
    __tablename__ = "tenants"

    id = Column(UUID, primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(16), default="normal")
```

**解读**：
- 第 13 行：`UniqueConstraint("tenant_id", "account_id")`——同一用户在同一租户只能有一个角色
- 第 17-22 行：**用户在租户内有 4 种角色**（owner/admin/editor/normal）
- **核心模型**：dify 的所有资源都通过 `tenant_id` 关联到 `tenants` 表，实现多租户隔离
- **设计意图**：dify 把"用户-租户多对多"显式建模，**用户可以在多个租户内有不同角色**

### 3.3 ruoyi 的 TenantSecurityInterceptor（拦截器强制隔离）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/security/TenantSecurityWebFilter.java`
**核心代码**（典型过滤器）：

```java
/**
 * 多租户安全过滤器：解析请求中的租户 ID
 */
public class TenantSecurityWebFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain chain) {
        // 1. 解析租户 ID（从 Header / JWT / Path）
        String tenantId = WebFrameworkUtils.getTenantId(request);

        // 2. 设置到上下文（线程级）
        if (tenantId != null) {
            TenantContextHolder.setTenantId(Long.parseLong(tenantId));
        }

        try {
            chain.doFilter(request, response);
        } finally {
            // 3. 清理上下文（防止内存泄漏）
            TenantContextHolder.clear();
        }
    }
}
```

**对应的 TenantContextHolder**：
```java
public class TenantContextHolder {
    private static final ThreadLocal<Long> TENANT_ID = new ThreadLocal<>();

    public static void setTenantId(Long tenantId) {
        TENANT_ID.set(tenantId);
    }

    public static Long getTenantId() {
        return TENANT_ID.get();
    }

    public static void clear() {
        TENANT_ID.remove();
    }
}
```

**解读**：
- 第 7 行：从请求中提取租户 ID（多种方式：Header `X-Tenant-Id` / JWT claims / URL Path）
- 第 10-12 行：存到 `TenantContextHolder`（**ThreadLocal**）
- 第 17 行：请求结束后清理，防止内存泄漏
- **设计意图**：ruoyi 通过 Filter + ThreadLocal 自动注入租户，业务代码用 `TenantContextHolder.getTenantId()` 直接取，**避免每个方法都传 tenant_id**

## 4. 关键要点总结

- **资源所有权**：Owner 自动拥有该资源的所有权限（最简单也最可靠）
- **租户隔离**：每条查询都带 `tenant_id`，避免数据串租
- 三种租户隔离方案：应用层过滤（简单）→ Schema 隔离（中等）→ 数据库级隔离（最强）
- dify 用 `current_account_with_tenant()` 强制注入租户
- ruoyi 用 `TenantContextHolder` + 拦截器自动注入
- **防御性编程**：跨租户访问时返回 404（不暴露存在性），同时记录日志告警
- **租户隔离失败的代价**：致命，可能导致法律诉讼和用户流失
- 多租户 SaaS 必须做**租户隔离测试**：专门用 A 租户身份尝试访问 B 租户数据

## 5. 练习题

### 练习 1：基础（必做）

实现一个 Flask 多租户文档系统：
1. 文档模型包含 `tenant_id` 和 `owner_id`
2. 所有查询自动加 tenant_id 过滤
3. `get_document(doc_id, user)` 自动校验所有权
4. 写测试：A 租户的用户不能访问 B 租户的文档

**参考答案**：见 `solutions/04-multi-tenant.md`

### 练习 2：进阶

解释 dify 和 ruoyi 的多租户实现差异：
1. dify 的 `current_account_with_tenant()` 与 ruoyi 的 `TenantContextHolder` 有什么本质区别？
2. dify 为什么用 `(user, tenant_id)` 元组返回？好处是什么？
3. ruoyi 的 ThreadLocal 在异步任务中有什么问题？如何解决？

### 练习 3：挑战（选做）

为 dify 添加"跨租户访问日志"：
- 用 dify 的 `enforce_rbac_access` 拦截所有 RBAC 检查
- 当发现 tenant_id 不匹配时，记录到 RateLimitLog 表
- 提供管理后台查询这些异常访问日志
- 加告警：单用户 1 小时内超过 5 次跨租户访问 → 邮件告警

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/login.py`
- `/Users/xu/code/github/dify/api/models/account.py`（TenantAccountJoin）
- `/Users/xu/code/github/dify/api/services/account_service.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/security/`
- 《数据密集型应用系统设计》第 7 章（多租户存储）

---

**文档版本**：v1.0
**最后更新**：2026-07-13