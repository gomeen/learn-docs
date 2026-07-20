# 3.1.1 SQL 基础语法：SELECT / INSERT / UPDATE / DELETE

> 用 CRUD 四类语句完成关系数据的读取、创建、修改与删除，并理解安全写入的边界。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 SELECT、INSERT、UPDATE、DELETE 的基本结构
- 使用 WHERE、ORDER BY、LIMIT 精确限定数据范围
- 理解参数绑定、受影响行数和事务对写操作的重要性
- 能看懂 dify 模型定义与聚合查询中的 SQL 意图

## 📚 前置知识

- Python 基础语法
- 关系表、行、列的基本概念
- 可选：本地 PostgreSQL 或 SQLite 环境

## 1. 核心概念

### 1.1 CRUD 与集合思维

SQL 描述“想要什么数据”，数据库优化器决定“怎样取得”。四类语句分别对应 CRUD：`SELECT` 读取、`INSERT` 创建、`UPDATE` 更新、`DELETE` 删除。SQL 面向的是**行集合**，不是逐行循环。

| 操作 | 基本结构 | 最容易犯的错误 |
|---|---|---|
| 查询 | `SELECT ... FROM ... WHERE ...` | `SELECT *` 读取无用列 |
| 插入 | `INSERT INTO ... (...) VALUES (...)` | 列与值顺序不一致 |
| 更新 | `UPDATE ... SET ... WHERE ...` | 漏写 `WHERE` |
| 删除 | `DELETE FROM ... WHERE ...` | 未确认影响范围 |

### 1.2 条件、排序与分页

`WHERE` 在排序前过滤行，`ORDER BY` 决定稳定顺序，`LIMIT` 限制返回量。分页必须提供稳定排序；仅按可能重复的时间排序，会在翻页时重复或遗漏数据，通常要追加主键作为第二排序键。

### 1.3 安全写操作

值应通过驱动参数绑定，而不是字符串拼接（SQL 注入风险详见 [SQL 注入](../../_common/05-web-security/03-sql-injection.md)）。生产写操作还应检查影响行数，并在事务里把相关变更作为一个整体提交（事务语义详见 [事务与隔离级别](04-sql-transaction.md)）。执行 `UPDATE`/`DELETE` 前，可先把相同的 `WHERE` 放入 `SELECT` 验证目标集合。

## 2. 代码示例

### 2.1 在一张任务表上练习 CRUD

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO tasks (id, title) VALUES
    (1, 'read SQL chapter'),
    (2, 'write exercises');

SELECT id, title, status
FROM tasks
WHERE status = 'pending'
ORDER BY created_at, id
LIMIT 10;

UPDATE tasks
SET status = 'done'
WHERE id = 1 AND status = 'pending';

DELETE FROM tasks
WHERE id = 2 AND status = 'pending';
```

**说明**：脚本可直接在 SQLite 或 PostgreSQL 中执行。两个写语句都带条件，查询也显式选择列并提供稳定排序。

## 3. dify 仓库源码解读

### 3.1 应用表的声明式结构

**文件位置**：`/Users/xu/code/github/dify/api/models/model.py`  
**核心代码**（行 397-424）：

```python
class App(Base):
    __tablename__ = "apps"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="app_pkey"),
        sa.Index("app_tenant_id_idx", "tenant_id"),
        sa.Index("app_tenant_maintainer_idx", "tenant_id", "maintainer"),
    )

    if TYPE_CHECKING:
        # Response-only attributes attached by app list/detail enrichers.
        access_mode: str | None
        has_draft_trigger: bool
        is_starred: bool

    id: Mapped[str] = mapped_column(StringUUID, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(StringUUID)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(LongText, default=sa.text("''"))
    mode: Mapped[AppMode] = mapped_column(EnumText(AppMode, length=255))
    icon_type: Mapped[IconType | None] = mapped_column(EnumText(IconType, length=255))
    icon = mapped_column(String(255))
    icon_background: Mapped[str | None] = mapped_column(String(255))
    app_model_config_id = mapped_column(StringUUID, nullable=True)
    workflow_id = mapped_column(StringUUID, nullable=True)
    status: Mapped[AppStatus] = mapped_column(
        EnumText(AppStatus, length=255), server_default=sa.text("'normal'"), default=AppStatus.NORMAL
    )
    enable_site: Mapped[bool] = mapped_column(sa.Boolean)
```

**解读**：
- 第 397-403 行把 `App` 映射到 `apps`，并声明主键和常用索引（索引设计详见 [索引原理](03-sql-index.md)；ORM 映射详见 [SQLAlchemy 映射](../../dify/03-database/02-sqlalchemy-mapping.md)）。
- 第 411-424 行的列定义对应 SQL 表中的列、类型和默认约束。
- ORM 隐藏了 SQL 字符串，但最终 CRUD 仍围绕这张表执行。

### 3.2 用 SELECT + COUNT 聚合数据

**文件位置**：`/Users/xu/code/github/dify/api/models/dataset.py`  
**核心代码**（行 214-230）：

```python
    @property
    def total_documents(self):
        return db.session.scalar(select(func.count(Document.id)).where(Document.dataset_id == self.id)) or 0

    @property
    def total_available_documents(self):
        return (
            db.session.scalar(
                select(func.count(Document.id)).where(
                    Document.dataset_id == self.id,
                    Document.indexing_status == "completed",
                    Document.enabled == True,
                    Document.archived == False,
                )
            )
            or 0
        )
```

**解读**：
- 第 215 行通过 `select(func.count(...))` 表达 `SELECT COUNT(...)`。
- 第 221-226 行把多个条件组合为 `WHERE ... AND ...`。
- `scalar(...) or 0` 把单值查询结果转换成业务层需要的整数。

## 4. 关键要点总结

- SQL CRUD 操作作用于行集合，`WHERE` 决定安全边界
- 读取时显式选列，分页时使用稳定排序
- 写入使用参数绑定、事务和影响行数检查
- SQLAlchemy 表达式最终仍会编译成 SQL

## 5. 练习题

### 练习 1：基础（必做）

创建 `notes` 表，插入 3 行，再查询最近的 2 行。

### 练习 2：进阶

为任务表增加 `priority`，写一条只更新未完成任务的语句，并说明漏写 `WHERE` 的后果。

### 练习 3：挑战（选做）

找到 dify 中一个 `select(func.count(...))` 查询，手写它等价的 SQL。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/model.py`
- `/Users/xu/code/github/dify/api/models/dataset.py`
- PostgreSQL SQL 命令：https://www.postgresql.org/docs/current/sql-commands.html
- PostgreSQL SELECT：https://www.postgresql.org/docs/current/sql-select.html

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
