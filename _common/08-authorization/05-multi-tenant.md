# 8.5 多租户架构：SAAS 模式 / 字段级隔离 / 数据库级隔离

> 理解 SaaS 多租户的完整架构，掌握三种隔离方案的设计与权衡。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 SaaS 多租户的核心挑战与三种主流隔离模式
- 区分共享数据库、共享 Schema、独立数据库三种方案的优劣
- 在 dify 和 ruoyi 中识别多租户实现
- 为自己的 SaaS 产品选择合适的隔离方案

## 📚 前置知识

- [8.4 资源所有权与租户隔离](./04-resource-ownership.md)
- 数据库基础
- SaaS 基础概念；权限模型亦见 [RBAC](./01-rbac.md)

## 1. 核心概念

### 1.1 什么是多租户？

多租户（Multi-Tenancy）：一个软件实例服务多个客户（租户），每个租户的数据相互隔离。

```
                    ┌─────────────────────┐
                    │  SaaS 应用实例       │
                    │                     │
  Tenant A ────────→  用户 Alice           │
                    │  App-1               │
                    │                     │
  Tenant B ────────→  用户 Bob             │
                    │  App-2               │
                    │                     │
  Tenant C ────────→  用户 Charlie         │
                    │  App-3               │
                    └─────────────────────┘
```

### 1.2 多租户的三大挑战

| 挑战 | 说明 |
|------|------|
| **数据隔离** | 租户 A 绝对不能访问租户 B 的数据 |
| **性能隔离** | 租户 A 的重查询不能影响租户 B 的响应 |
| **定制化** | 不同租户可能有不同功能/配置 |

### 1.3 三种主流隔离模式

#### 模式 A：共享数据库 + 共享 Schema（最常见）

```
┌──────────────────────────────────────┐
│  单一数据库                          │
│  ┌────────────────────────────────┐  │
│  │  documents 表                  │  │
│  │  ┌────┬──────────┬──────────┐  │  │
│  │  │ id │tenant_id │ content  │  │  │
│  │  ├────┼──────────┼──────────┤  │  │
│  │  │ 1  │ t1       │ ...      │  │  │
│  │  │ 2  │ t1       │ ...      │  │  │
│  │  │ 3  │ t2       │ ...      │  │  │
│  │  │ 4  │ t2       │ ...      │  │  │
│  │  └────┴──────────┴──────────┘  │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

**实现**：所有表带 `tenant_id` 列，应用层强制过滤

**优点**：
- 成本最低（一个数据库）
- 运维简单
- 跨租户分析容易

**缺点**：
- 隔离性最弱（一个 SQL 错误可能泄露数据）
- 性能隔离差（重查询影响所有人）

#### 模式 B：共享数据库 + 独立 Schema

```
┌──────────────────────────────────────┐
│  单一数据库                          │
│  ┌──────────┬──────────┬──────────┐  │
│  │ tenant_a │ tenant_b │ tenant_c │  │
│  │ schema   │ schema   │ schema   │  │
│  │          │          │          │  │
│  │ documents│ documents│ documents│  │
│  │ users    │ users    │ users    │  │
│  └──────────┴──────────┴──────────┘  │
└──────────────────────────────────────┘
```

**实现**：每租户一个 schema，连接时切换 search_path

**优点**：
- 中等隔离
- 跨租户分析仍可（DB Link）
- 迁移灵活（单租户迁移到独立 DB）

**缺点**：
- Schema 数量上限（PostgreSQL 通常 1000-10000）
- 维护复杂

#### 模式 C：独立数据库

```
┌──────────┐ ┌──────────┐ ┌──────────┐
│ tenant_a │ │ tenant_b │ │ tenant_c │
│   DB     │ │   DB     │ │   DB     │
│          │ │          │ │          │
│ documents│ │ documents│ │ documents│
│ users    │ │ users    │ │ users    │
└──────────┘ └──────────┘ └──────────┘
```

**实现**：每租户独立连接串（动态切换）

**优点**：
- 隔离性最强
- 性能隔离最好
- 独立备份、迁移

**缺点**：
- 成本高（多数据库）
- 跨租户分析复杂
- 运维负担重

### 1.4 三种模式对比

| 维度 | 共享 Schema | 独立 Schema | 独立数据库 |
|------|----------|-----------|----------|
| 隔离性 | 弱 | 中 | **强** |
| 成本 | **低** | 中 | 高 |
| 性能隔离 | 差 | 中 | **好** |
| 跨租户分析 | 容易 | 中等 | 难 |
| 运维复杂度 | **低** | 中 | 高 |
| 适用规模 | 小到中 | 中到大 | 大企业 |
| 典型用户 | Slack（早期）、Notion | GitHub Enterprise | 大型企业 SaaS |

### 1.5 dify 和 ruoyi 的多租户实现

| 项目 | 多租户模式 | 实现位置 |
|------|----------|---------|
| **dify** | 模式 A（共享 Schema，tenant_id 字段）| `tenant_id` 列 + 强制注入 |
| **ruoyi** | 模式 A + 拦截器（`TenantContextHolder`）| ThreadLocal + 拦截器 |

两者都采用**共享数据库 + 共享 Schema + tenant_id 字段**，通过应用层强制隔离。

## 2. 代码示例

### 2.1 模式 A：共享 Schema（应用层隔离）

```python
# 文件：shared_schema.py
# 多租户共享 Schema：每张表带 tenant_id
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(String, primary_key=True)
    name = Column(String)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    # 关键：每张表都带 tenant_id 列，并建索引
    title = Column(String)
    content = Column(String)
    owner_id = Column(String)


# 应用层强制隔离（关键！）
def get_documents(session, current_user):
    """查询文档：自动加 tenant_id 过滤"""
    return session.query(Document).filter(
        Document.tenant_id == current_user["tenant_id"]  # ✅ 强制
    ).all()


def get_document(session, doc_id, current_user):
    """获取单个文档：双重校验"""
    doc = session.query(Document).filter_by(id=doc_id).first()
    if not doc:
        return None
    if doc.tenant_id != current_user["tenant_id"]:
        # ✅ 跨租户访问：记录日志但不抛 403
        logger.warning(f"cross-tenant access: user={current_user['user_id']} doc={doc_id}")
        return None
    return doc
```

### 2.2 模式 B：Schema 隔离（动态 search_path）

```python
# 文件：schema_isolation.py
# PostgreSQL Schema 隔离实现
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine("postgresql://user:pass@primary/app_db")
Session = sessionmaker(bind=engine)


def get_session_for_tenant(tenant_id: str):
    """获取租户的 Session（自动切换 schema）"""
    session = Session()
    # ✅ 关键：切换 search_path
    session.execute(text(f'SET search_path TO "tenant_{tenant_id}", public'))
    return session


# 部署时为每个租户创建独立 schema
def setup_tenant_schema(tenant_id: str):
    """初始化租户 schema"""
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "tenant_{tenant_id}"'))
        # 创建表（从模板复制）
        conn.execute(text(f'''
            CREATE TABLE "tenant_{tenant_id}".documents (
                LIKE public.documents_template INCLUDING ALL
            )
        '''))
```

### 2.3 模式 C：独立数据库（动态连接）

```python
# 文件：db_isolation.py
# 多租户独立数据库（动态连接）
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class TenantDBRouter:
    """租户数据库路由器"""

    def __init__(self):
        self._engines: dict[str, object] = {}

    def get_engine(self, tenant_id: str):
        """获取租户专用引擎（带缓存）"""
        if tenant_id in self._engines:
            return self._engines[tenant_id]

        # 根据 tenant_id 动态选择连接
        connection_url = self._resolve_connection(tenant_id)
        engine = create_engine(connection_url, pool_size=10)
        self._engines[tenant_id] = engine
        return engine

    def _resolve_connection(self, tenant_id: str) -> str:
        """根据租户 ID 解析连接（实际从配置中心取）"""
        # 可以从 Nacos / Consul 取
        return f"postgresql://user:pass@primary-{tenant_id}.internal/app_db"


router = TenantDBRouter()


def query_documents(tenant_id: str, user_id: str):
    """查询租户文档（连接到租户专用数据库）"""
    engine = router.get_engine(tenant_id)
    with sessionmaker(bind=engine)() as session:
        return session.query(Document).filter_by(owner_id=user_id).all()
```

### 2.4 自动化隔离测试

```python
# 文件：isolation_test.py
# 自动化测试：防止租户数据串租
import pytest


class TestTenantIsolation:
    """租户隔离测试套件"""

    def test_user_cannot_access_other_tenant_documents(self, client):
        """测试：A 租户用户不能访问 B 租户文档"""
        # 1. B 租户创建文档
        with client.session_transaction() as sess:
            sess["user_id"] = "bob"
            sess["tenant_id"] = "tenant_b"

        resp = client.post("/api/documents", json={"title": "secret"})
        doc_id = resp.json["id"]

        # 2. 切换到 A 租户用户
        with client.session_transaction() as sess:
            sess["user_id"] = "alice"
            sess["tenant_id"] = "tenant_a"

        # 3. A 租户用户尝试访问 B 租户文档
        resp = client.get(f"/api/documents/{doc_id}")
        assert resp.status_code == 404  # ✅ 应该是 404（不暴露存在性）

    def test_list_only_shows_own_tenant(self, client):
        """测试：列表只显示当前租户数据"""
        # A 租户
        with client.session_transaction() as sess:
            sess["user_id"] = "alice"
            sess["tenant_id"] = "tenant_a"

        resp = client.get("/api/documents")
        docs = resp.json["items"]
        # ✅ 所有返回的文档必须属于 tenant_a
        for doc in docs:
            assert doc["tenant_id"] == "tenant_a"
```

## 3. dify 仓库源码解读

### 3.1 dify 的多租户架构（Tenant 中心化）

**文件位置**：`/Users/xu/code/github/dify/api/models/account.py`
**核心代码**（典型 Tenant 模型）：

```python
class Tenant(db.Model):
    """租户表：多租户隔离的基础"""
    __tablename__ = "tenants"

    id = Column(UUID, primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(16), default="normal")

    # 关联：用户-租户多对多
    account_joins = relationship(
        "TenantAccountJoin",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )


class TenantAccountJoin(db.Model):
    """用户-租户关联表（用户在租户内的角色）"""
    __tablename__ = "tenant_account_joins"

    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False, index=True)
    account_id = Column(UUID, ForeignKey("accounts.id"), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # owner/admin/editor/normal
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "account_id", name="uk_tenant_account"),
    )
```

**所有资源的 tenant_id 示例**（apps 表）：
```python
class App(db.Model):
    __tablename__ = "apps"
    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False, index=True)
    # ↑↑↑ 关键：每张业务表都带 tenant_id
    name = Column(String(255))
    # ...
```

**解读**：
- 第 12-16 行：`account_joins` 是反向关系——一个租户可以包含多个用户
- 第 25-30 行：`(tenant_id, account_id)` 唯一约束——用户在同一租户只有一个角色
- 第 31 行：**所有业务表都带 `tenant_id` 并建索引**——这是模式 A 的标准实现
- **设计意图**：dify 通过"显式 tenant_id 列 + 应用层强制"实现多租户，所有 Service 层方法都接收 `tenant_id` 参数

### 3.2 ruoyi 的多租户拦截器

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/aop/TenantIgnore.java`
**核心代码**（典型注解）：

```java
/**
 * 多租户忽略注解：标记不需要租户隔离的方法
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface TenantIgnore {
}
```

**TenantIgnoreInterceptor**：
```java
public class TenantIgnoreInterceptor implements MethodInterceptor {
    @Override
    public Object invoke(MethodInvocation invocation) throws Throwable {
        // 检查方法是否有 @TenantIgnore
        Method method = invocation.getMethod();
        if (method.isAnnotationPresent(TenantIgnore.class)) {
            // 跳过租户检查（用于登录、注册等）
            return invocation.proceed();
        }

        // 执行租户上下文检查
        Long tenantId = TenantContextHolder.getTenantId();
        if (tenantId == null) {
            throw new ServiceException("tenant context missing");
        }

        return invocation.proceed();
    }
}
```

**解读**：
- 第 6-9 行：`@TenantIgnore` 注解——某些方法（登录、注册、健康检查）不需要租户上下文
- 第 21 行：缺失租户上下文直接报错（**fail-fast 原则**）
- **设计意图**：ruoyi 通过 AOP 拦截器**强制**所有业务方法必须有租户上下文，避免遗漏

## 4. 关键要点总结

- 多租户 SaaS 有三种主流模式：共享 Schema、独立 Schema、独立数据库
- **绝大多数 SaaS 用模式 A**（共享 Schema + tenant_id）——简单、便宜
- **租户隔离的关键**：`tenant_id` 必须强制出现在所有业务查询
- **强制手段**：
  - dify：函数签名 `(user, tenant_id)` 元组
  - ruoyi：ThreadLocal + AOP 拦截器
- **跨租户访问处理**：返回 404（不暴露存在性）+ 记录日志
- **租户隔离测试**：必须写自动化测试，防止回归
- **进阶**：当租户规模变大时，可以从模式 A 演进到模式 C（独立数据库）

## 5. 练习题

### 练习 1：基础（必做）

设计一个多租户博客系统：
1. 三张表：tenants / users / posts（都带 tenant_id）
2. 所有查询自动加 tenant_id 过滤
3. 单元测试：用户 A 不能访问租户 B 的文章

**参考答案**：见 `solutions/05-multitenant-blog.md`

### 练习 2：进阶

对比三种多租户模式的适用场景：
1. 什么规模/行业适合共享 Schema？
2. 哪些场景必须用独立 Schema 或独立数据库？
3. 模式 A 演进到模式 C 的迁移路径是什么？

### 练习 3：挑战（选做）

实现"租户隔离扫描器"：
- 扫描 dify `api/services/` 下的所有 SQLAlchemy 查询
- 找出所有 `session.query(...)` 没带 `tenant_id` 过滤的代码
- 输出报告（按文件分组）
- 提示：用 AST 解析 Python 代码

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/account.py`
- `/Users/xu/code/github/dify/api/services/account_service.py`
- `/Users/xu/code/github/dify/api/libs/login.py`（租户上下文解析）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/aop/TenantIgnore.java`
- 《SaaS 架构设计》：Dan Ciruli
- Microsoft 多租户架构指南：https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/overview

---

**文档版本**：v1.0
**最后更新**：2026-07-13