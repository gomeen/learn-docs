# 2.1.3 仓储模式（Repository Pattern）

> 理解 Repository 模式如何在 dify 中抽象数据访问。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 Repository 模式的核心思想：把数据访问封装到"集合"语义后
- 在 dify 中找到 `WorkflowExecutionRepository` 的接口和两种实现
- 理解 Protocol 接口 + Factory 动态加载的实现方式
- 通过 Repository 模式支持 dify 的 multi-tenancy 隔离

## 📚 前置知识

- 02-backend/01-ddd-concepts.md（DDD 聚合根概念）
- 02-backend/02-layered-architecture.md（分层架构）
- Python Protocol 类型（详见 01-fundamentals 系列）
- SQLAlchemy ORM 基础

## 1. 核心概念

### 1.1 什么是 Repository 模式？

Repository 模式把数据访问封装成"内存中的集合"：

```python
# 业务代码视角：
users = user_repository.find_all()
# 就像操作 List 一样，但底层可能是 SQL、NoSQL、远程 API
```

**核心思想**：
- 用面向对象的方式访问数据（`find_by_id`、`save`、`delete`）
- 隔离业务逻辑与持久化技术
- 让单元测试可以用内存对象替换真实数据库

### 1.2 Repository vs DAO

| 维度 | DAO | Repository |
|------|-----|------------|
| 抽象层级 | 贴近 SQL | 贴近领域对象 |
| 方法名 | `getById`、`insert` | `find_by_id`、`save` |
| 返回值 | 表行（ORM 对象） | 聚合根（领域对象） |
| 业务语义 | 无 | 有（如 `find_active_users()`） |

### 1.3 dify 的特殊设计：Protocol + Factory

dify 的 Repository 有两个特点：
1. **接口用 Protocol 声明**（结构化子类型，不需要继承）
2. **实现类通过配置动态加载**（类似 Django 的 `DATABASES`）

```python
# Domain 层定义接口
class WorkflowExecutionRepository(Protocol):
    def save(self, execution: WorkflowExecution): ...

# 通过 dify_config 决定使用哪个实现
CORE_WORKFLOW_EXECUTION_REPOSITORY = "core.repositories.sqlalchemy_workflow_execution_repository.SQLAlchemyWorkflowExecutionRepository"
```

这样设计的好处：
- 不需要写 `if/else` 选择实现
- 切换实现只改配置（环境变量）
- 便于单测时注入 Mock

### 1.4 multi-tenancy 隔离

dify 是 SaaS 产品，所有 Repository 方法都需要带 `tenant_id` 过滤，否则会跨租户泄漏数据：

```python
# ✅ 正确的 Repository 方法
def find_runs(self, tenant_id: str, app_id: str) -> list[WorkflowRun]:
    return self.session.query(WorkflowRun).filter_by(
        tenant_id=tenant_id,  # 多租户过滤
        app_id=app_id,
    ).all()
```

## 2. 代码示例

### 2.1 基础 Repository

```python
from typing import Protocol
from abc import abstractmethod
from sqlalchemy.orm import Session

# === 领域对象 ===
@dataclass
class Article:
    id: int
    title: str
    content: str
    author_id: int

# === Repository 接口（Domain 层） ===
class ArticleRepository(Protocol):
    def find_by_id(self, article_id: int) -> Article | None: ...
    def find_by_author(self, author_id: int) -> list[Article]: ...
    def save(self, article: Article) -> None: ...
    def delete(self, article_id: int) -> None: ...

# === SQLAlchemy 实现 ===
class SqlArticleRepository:
    def __init__(self, session: Session):
        self._session = session

    def find_by_id(self, article_id: int) -> Article | None:
        row = self._session.execute(
            select(ArticleRow).where(ArticleRow.id == article_id)
        ).scalar_one_or_none()
        return self._to_domain(row) if row else None

    def find_by_author(self, author_id: int) -> list[Article]:
        rows = self._session.execute(
            select(ArticleRow).where(ArticleRow.author_id == author_id)
        ).scalars().all()
        return [self._to_domain(r) for r in rows]

    def save(self, article: Article) -> None:
        row = ArticleRow(id=article.id, title=article.title, ...)
        self._session.merge(row)
        self._session.commit()

    def _to_domain(self, row: ArticleRow) -> Article:
        return Article(id=row.id, title=row.title, content=row.content, author_id=row.author_id)


# === 使用 ===
repo: ArticleRepository = SqlArticleRepository(session)
article = repo.find_by_id(1)
```

### 2.2 内存实现（用于测试）

```python
class InMemoryArticleRepository:
    def __init__(self):
        self._articles: dict[int, Article] = {}

    def find_by_id(self, article_id: int) -> Article | None:
        return self._articles.get(article_id)

    def find_by_author(self, author_id: int) -> list[Article]:
        return [a for a in self._articles.values() if a.author_id == author_id]

    def save(self, article: Article) -> None:
        self._articles[article.id] = article

    def delete(self, article_id: int) -> None:
        self._articles.pop(article_id, None)


# 测试时直接注入
def test_find_articles():
    repo = InMemoryArticleRepository()
    repo.save(Article(id=1, title="t", content="c", author_id=100))
    assert repo.find_by_author(100)[0].title == "t"
```

### 2.3 常见错误：Repository 返回 ORM 对象

```python
# ❌ 错误：返回 ORM 对象，把持久化细节泄漏到上层
class BadRepository:
    def find_by_id(self, article_id: int):
        return self._session.query(ArticleRow).filter_by(id=article_id).first()
    # Service 层拿到 ORM 对象，可能直接 session.add() 污染事务

# ✅ 正确：返回纯领域对象（dataclass / Pydantic）
class GoodRepository:
    def find_by_id(self, article_id: int) -> Article | None:
        row = self._session.query(ArticleRow).filter_by(id=article_id).first()
        return Article(row.id, row.title, ...) if row else None
```

## 3. dify 仓库源码解读

### 3.1 Protocol 接口定义

**文件位置**：`/Users/xu/code/github/dify/api/core/repositories/factory.py`
**核心代码**（行 23-46）：

```python
@dataclass
class OrderConfig:
    """Configuration for ordering node execution instances."""
    order_by: list[str]
    order_direction: Literal["asc", "desc"] | None = None


class WorkflowExecutionRepository(Protocol):
    def save(self, execution: WorkflowExecution): ...


class WorkflowNodeExecutionRepository(Protocol):
    def save(self, execution: WorkflowNodeExecution): ...

    def save_execution_data(self, execution: WorkflowNodeExecution): ...

    def get_by_workflow_execution(
        self,
        workflow_execution_id: str,
        order_config: OrderConfig | None = None,
    ) -> Sequence[WorkflowNodeExecution]: ...
```

**解读**：
- 第 4 行：`OrderConfig` 是排序配置的值对象（不可变）
- 第 11 行：`WorkflowExecutionRepository` 接口——只有 `save` 方法
- 第 14 行：`WorkflowNodeExecutionRepository` 接口——更复杂，包含查询和保存
- 第 16 行：`save_execution_data` 分离保存执行数据和保存执行状态（区分轻量和重量数据）

### 3.2 Factory 动态加载实现

**文件位置**：`/Users/xu/code/github/dify/api/core/repositories/factory.py`
**核心代码**（行 53-96）：

```python
class DifyCoreRepositoryFactory:
    """根据配置动态创建 Repository 实例（依赖倒置）。"""

    @classmethod
    def create_workflow_execution_repository(
        cls,
        session_factory: sessionmaker | Engine,
        user: Account | EndUser,
        app_id: str,
        triggered_from: WorkflowRunTriggeredFrom,
    ) -> WorkflowExecutionRepository:
        class_path = dify_config.CORE_WORKFLOW_EXECUTION_REPOSITORY

        try:
            repository_class = import_string(class_path)
            return repository_class(
                session_factory=session_factory,
                user=user,
                app_id=app_id,
                triggered_from=triggered_from,
            )
        except (ImportError, Exception) as e:
            raise RepositoryImportError(
                f"Failed to create WorkflowExecutionRepository from '{class_path}': {e}"
            ) from e
```

**解读**：
- 第 14 行：`class_path = dify_config.CORE_WORKFLOW_EXECUTION_REPOSITORY` 从配置读取
- 第 16 行：`import_string` 是 Django 风格的动态导入（`module.path.ClassName`）
- 第 17-21 行：通过工厂方法创建实例，调用方只看到 `WorkflowExecutionRepository` 接口
- **配置示例**（在 `configs/dify_config.py`）：
  - 默认：`"core.repositories.sqlalchemy_workflow_execution_repository.SQLAlchemyWorkflowExecutionRepository"`
  - 可替换为 Celery 实现：`"core.repositories.celery_workflow_execution_repository.CeleryWorkflowExecutionRepository"`

### 3.3 SQLAlchemy 实现

**文件位置**：`/Users/xu/code/github/dify/api/core/repositories/sqlalchemy_workflow_execution_repository.py`
**核心代码**（行 28-50）：

```python
class SQLAlchemyWorkflowExecutionRepository(WorkflowExecutionRepository):
    """SQLAlchemy implementation of the WorkflowExecutionRepository interface.

    This implementation supports multi-tenancy by filtering operations based on tenant_id.
    Each method creates its own session, handles the transaction, and commits changes
    to the database. This prevents long-running connections in the workflow core.
    """

    def __init__(
        self,
        session_factory: sessionmaker | Engine,
        user: Account | EndUser,
        app_id: str | None,
        triggered_from: WorkflowRunTriggeredFrom | None,
    ):
        """
        Initialize the repository with a SQLAlchemy sessionmaker or engine and context information.

        Args:
            session_factory: 允许注入 sessionmaker 或 Engine（依赖注入友好）
            user: 当前用户对象（Account 或 EndUser）
            app_id: 应用 ID（用于多租户隔离）
            triggered_from: 触发来源（debugger、API、trigger 等）
        """
```

**解读**：
- 第 1 行：实现类显式声明 `WorkflowExecutionRepository`（满足 Protocol）
- 第 7-8 行：注释明确说明该实现支持 multi-tenancy 隔离
- 第 17 行：构造函数接受 `sessionmaker` 或 `Engine`（**依赖注入**：方便测试）
- 第 20 行：构造函数保存 `user`、`app_id`、`triggered_from`——这些是上下文信息，每次操作都自动带上

## 4. 关键要点总结

- Repository 把数据访问封装成"集合"语义：`find_by_id`、`save`、`delete`
- **Protocol 接口** + **Factory 动态加载**是 dify 的核心抽象方式
- Repository 返回**领域对象**，不返回 ORM 行（避免持久化泄漏）
- dify 所有 Repository 都支持 **multi-tenancy**：`tenant_id` 必须作为过滤条件
- 测试时可注入 `InMemoryRepository`（dify 测试中有专门的 `factories` 目录生成测试数据）

## 5. 练习题

### 练习 1：基础（必做）

定义一个 `ConversationRepository` Protocol，要求包含：
- `find_by_id(conversation_id: str) -> Conversation | None`
- `list_by_user(user_id: str, limit: int) -> list[Conversation]`
- `save(conversation: Conversation) -> None`

然后用 SQLAlchemy 实现 `SqlConversationRepository`。

### 练习 2：进阶

阅读 `api/core/repositories/celery_workflow_execution_repository.py`：
1. 它与 SQLAlchemy 实现的区别是什么？
2. 为什么要保留 Celery 实现？什么场景下用 Celery 实现？

### 练习 3：挑战（选做）

设计一个 `DatasetRepository`，要求：
- 接口定义在 Domain 层（Protocol）
- SQLAlchemy 实现放在 `core/repositories/`
- 实现多租户过滤：`find_datasets(tenant_id: str)`
- 实现 `find_by_id_with_documents(dataset_id)`，自动加载关联文档

写完后解释为什么 `find_by_id_with_documents` 应该返回 `Dataset` 领域对象而不是 `DatasetRow` ORM 对象。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/repositories/factory.py` — Protocol + Factory
- `/Users/xu/code/github/dify/api/core/repositories/sqlalchemy_workflow_execution_repository.py` — SQL 实现
- `/Users/xu/code/github/dify/api/core/repositories/celery_workflow_execution_repository.py` — Celery 实现
- `/Users/xu/code/github/dify/api/configs/dify_config.py` — `CORE_WORKFLOW_EXECUTION_REPOSITORY` 配置
- Martin Fowler《企业应用架构模式》Repository 章节

---

**文档版本**：v1.0
**最后更新**：2026-07-13