# 3.3.8 dify 多租户查询的 tenant_id 过滤实践

> 把租户作用域作为每条共享表查询的必备不变量，防止对象 ID 泄露导致跨租户越权。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解共享表多租户模型与 tenant_id 作用域
- 在 CRUD 和 JOIN 中传播租户条件
- 设计租户复合索引与组合唯一键
- 审查 dify 查询的跨租户安全边界

## 📚 前置知识

- [3.3.2 select() 查询 API](./03-sqlalchemy-query.md)
- 后端多租户全链路（详见 [多租户架构](../02-backend/18-multi-tenancy.md)）
- 资源所有权：[`../05-auth-and-security/01-resource-ownership.md`（dify 项目视角）](../05-auth-and-security/01-resource-ownership.md)

## 1. 核心概念

### 1.1 tenant_id 是安全边界

共享 schema 中，多租户记录共处一表。仅凭资源 UUID 查询不安全。CRUD 都应匹配 `tenant_id`，关联查询还要确保两侧租户一致。

### 1.2 从入口到存储传播

租户 ID 应来自已认证上下文，而不是请求体。Controller 解析身份，Service 传递作用域，Repository 落实到 SQL。后台任务也必须显式携带 tenant_id。

### 1.3 索引与约束

高频查询常以 `(tenant_id, resource_id/status/created_at)` 建复合索引（复合索引与最左前缀详见 [索引原理](../../_common/21-sql/03-sql-index.md)）。业务唯一性通常也限定在租户内，如 `UNIQUE (tenant_id, name)`。

## 2. 代码示例

### 2.1 封装强制租户作用域的仓储

仓储模式把过滤封装在数据访问层（详见 [仓储模式](../../_common/22-architecture/03-repository-pattern.md)）；此处用 `@dataclass` 承载查询上下文（详见 [dataclass](../01-fundamentals/26-dataclasses.md)）。

```python
from dataclasses import dataclass
from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

class Base(DeclarativeBase):
    pass

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(80))

@dataclass(frozen=True)
class ProjectRepository:
    session: Session
    tenant_id: str

    def get(self, project_id: int) -> Project | None:
        stmt = select(Project).where(
            Project.id == project_id,
            Project.tenant_id == self.tenant_id,
        )
        return self.session.scalar(stmt)

engine = create_engine("sqlite://")
Base.metadata.create_all(engine)
with Session(engine) as session:
    print(ProjectRepository(session, "tenant-a").get(1))
```

**说明**：仓储构造时绑定租户，调用 `get` 无法忘记 tenant_id。写操作应沿用同一作用域。

## 3. 关键要点总结

- tenant_id 是授权不变量，不只是性能过滤
- 所有 CRUD、JOIN 和后台任务都要传播租户作用域
- 关联两侧应同时验证租户
- 复合索引与唯一约束通常以 tenant_id 开头

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
