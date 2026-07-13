# 3.2.1 三大范式与反范式

> 通过规范化消除更新异常，再针对明确的读性能与一致性成本做受控反范式。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释第一、第二、第三范式
- 识别插入、更新和删除异常
- 区分规范化关系与反范式快照/计数
- 分析 dify 的应用、配置和关联表设计

## 📚 前置知识

- [3.1.2 多表查询](./02-sql-join.md)
- 函数依赖的基本直觉

## 1. 核心概念

### 1.1 三大范式

- **1NF**：每个字段保持原子值，不在一个字符串中塞重复组。
- **2NF**：在 1NF 基础上，非主属性完全依赖整个候选键。
- **3NF**：在 2NF 基础上，非主属性不经由另一个非主属性传递依赖主键。

把“应用”和“应用模型配置”拆开，可让配置独立演进；把“应用-数据集”拆为关联表，可表达多对多而不重复名称等属性。

### 1.2 反范式何时合理

反范式通过复制数据减少连接，例如保存 `dialogue_count`、运行时快照或冗余状态。它必须回答：谁是事实源、何时同步、失败如何修复、旧值能否接受。

### 1.3 判断方法

先从一致性和写路径出发做规范化，再用真实慢查询证明需要冗余。缓存、物化视图、批量聚合可能比直接复制业务字段更容易维护。

## 2. 代码示例

### 2.1 把重复订单表拆成规范化结构

```sql
CREATE TABLE customers (
    id BIGINT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL
);

CREATE TABLE products (
    id BIGINT PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    current_price NUMERIC(12, 2) NOT NULL
);

CREATE TABLE orders (
    id BIGINT PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_items (
    order_id BIGINT NOT NULL REFERENCES orders(id),
    product_id BIGINT NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL,
    PRIMARY KEY (order_id, product_id)
);
```

**说明**：客户与商品事实只保存一次；`unit_price` 是有意的订单快照，防止商品现价变化改写历史订单。

## 3. dify 仓库源码解读

### 3.1 应用实体与配置实体分离

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
- `App` 保存应用身份、租户、模式和功能开关等核心事实。
- `app_model_config_id` 只保存关联标识，不把所有配置字段重复塞入应用表。
- 拆分降低大量可选配置字段对核心应用记录的影响。

### 3.2 应用与数据集的关联表

**文件位置**：`/Users/xu/code/github/dify/api/models/dataset.py`  
**核心代码**（行 1117-1136）：

```python
class AppDatasetJoin(TypeBase):
    __tablename__ = "app_dataset_joins"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="app_dataset_join_pkey"),
        sa.Index("app_dataset_join_app_dataset_idx", "dataset_id", "app_id"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID,
        primary_key=True,
        nullable=False,
        insert_default=lambda: str(uuid4()),
        default_factory=lambda: str(uuid4()),
        init=False,
    )
    app_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    dataset_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=sa.func.current_timestamp(), init=False
    )
```

**解读**：
- `AppDatasetJoin` 只保存应用、数据集和创建时间，职责单一。
- 一条关联一行，避免在应用表中保存逗号分隔的数据集 ID。
- 组合索引支持从数据集和应用两个维度定位绑定关系。

## 4. 关键要点总结

- 范式解决的是依赖与更新异常，不是表越多越好
- 多对多关系应使用关联表
- 反范式需要明确事实源、同步机制和修复手段
- 历史快照是常见且合理的受控冗余

## 5. 练习题

### 练习 1：基础（必做）

找出一张同时重复客户姓名和邮箱的订单表中的更新异常。

### 练习 2：进阶

把“文章 + 逗号分隔标签”改造成第三范式结构。

### 练习 3：挑战（选做）

在 dify 中找到一个计数或快照字段，分析它的事实源和失同步风险。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/model.py`
- `/Users/xu/code/github/dify/api/models/dataset.py`
- PostgreSQL 表定义：https://www.postgresql.org/docs/current/ddl.html

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
