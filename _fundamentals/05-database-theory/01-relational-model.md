# 1.1 关系模型：表 / 元组 / 属性 / 域

> 关系模型是关系数据库（MySQL、PostgreSQL）的理论基础，由 Edgar F. Codd 在 1970 年提出。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解关系模型的数学定义（关系 = 集合 × 域）
- 区分"关系（Relation）"与日常说的"表（Table）"
- 理解元组、属性、域、主键、外键等核心术语
- 能看懂 dify 和 ruoyi 的数据模型定义（`models/*.py` 与 `Mapper.xml`）

## 📚 前置知识

- Python 基础语法
- SQL 基础（SELECT、INSERT）

## 1. 核心概念

### 1.1 关系模型的三大要素

**结构（Structure）**：数据如何组织——表（Relation）
**操作（Operations）**：能做什么——关系代数（选择、投影、联接等）
**完整性（Integrity）**：数据如何约束——主键、外键、CHECK

### 1.2 核心术语对照表

| 数学术语 | SQL 术语 | 通俗理解 |
|---------|---------|---------|
| 关系（Relation） | 表（Table） | 二维表 |
| 元组（Tuple） | 行（Row）/ 记录（Record） | 一条数据 |
| 属性（Attribute） | 列（Column）/ 字段（Field） | 一个字段 |
| 域（Domain） | 数据类型 + 取值范围 | 字段允许的值集合 |
| 候选键（Candidate Key） | 唯一索引 | 能唯一标识元组的属性组 |
| 主键（Primary Key） | 主键 | 被选定的候选键 |
| 外键（Foreign Key） | 外键 | 引用其他关系的属性 |

### 1.3 关系的数学定义

关系 R 是 **域 D1, D2, ..., Dn** 的笛卡尔积的**子集**：
- 关系 R ⊆ D1 × D2 × ... × Dn
- 元组 t ∈ R 是 D1 × ... × Dn 中的一个元素
- 关系是集合（无序、不重复）

### 1.4 关系 vs 表：关键区别

| 维度 | 关系（数学） | 表（SQL 实现） |
|------|-------------|---------------|
| 行的顺序 | 无序 | 通常有序（[聚簇索引](./12-clustered-index.md)） |
| 行的重复 | 不允许 | 物理上允许（SQL 不强制） |
| 属性的顺序 | 无序 | 通常有序 |
| 空值（NULL） | 不允许 | 允许 |

**结论**：SQL 表是关系模型的"超集"，引入了 NULL、顺序等额外特性。

## 2. 代码示例

### 2.1 用 Python 模拟关系模型

```python
from typing import Any

# 定义域（Domain）
class Domain:
    """域 = 数据类型 + 取值约束"""

    def __init__(self, name: str, type_: type, constraint=None):
        self.name = name
        self.type = type_
        self.constraint = constraint

    def validate(self, value: Any) -> bool:
        if not isinstance(value, self.type):
            return False
        if self.constraint and not self.constraint(value):
            return False
        return True


# 定义属性（Attribute）
class Attribute:
    def __init__(self, name: str, domain: Domain):
        self.name = name
        self.domain = domain


# 定义关系（Relation）
class Relation:
    """关系 = 表头（属性集合）+ 表体（元组集合）"""

    def __init__(self, name: str, attributes: list[Attribute]):
        self.name = name
        self.attributes = {a.name: a for a in attributes}
        self.tuples: list[dict] = []  # 元组集合（数学上无序无重复）

    def insert(self, row: dict) -> None:
        # 1. 检查所有属性值是否在合法域内
        for attr_name, value in row.items():
            domain = self.attributes[attr_name].domain
            if not domain.validate(value):
                raise ValueError(f"值 {value} 违反域 {domain.name}")
        self.tuples.append(row)


# ===== 使用示例 =====
# 定义域
name_domain = Domain("name", str, lambda x: 0 < len(x) <= 50)
age_domain = Domain("age", int, lambda x: 0 <= x <= 150)

# 定义表头（关系模式）
user_relation = Relation(
    "users",
    [
        Attribute("id", Domain("id", int, lambda x: x > 0)),
        Attribute("name", name_domain),
        Attribute("age", age_domain),
    ],
)

# 插入元组
user_relation.insert({"id": 1, "name": "Alice", "age": 30})
user_relation.insert({"id": 2, "name": "Bob", "age": 25})
print(user_relation.tuples)
```

## 3. dify 仓库源码解读

### 3.1 SQLAlchemy 模型：关系的 Python 实现

**文件位置**：`/Users/xu/code/github/dify/api/models/account.py`
**核心代码**（行 1-40）：

```python
from sqlalchemy import CHAR, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

class Account(Base):
    """账户关系（关系模式）。

    每个 Mapped[str] 字段就是一个"属性"，对应一个域。
    """
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255))
    password: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(16), default="pending")
```

**解读**：
- 第 8 行：`__tablename__ = "accounts"`——关系名（表名）
- 第 10 行：`id` 是主键（候选键中被选定的那个）
- 第 11 行：`String(255)` 是**域**：类型 + 长度约束
- 第 12 行：`nullable=False` 是**完整性约束**（非空）
- 整体上：这是用 Python 类描述关系模型"表头"的典型做法

## 4. 关键要点总结

- 关系模型基于集合论与一阶谓词逻辑
- 关系是"集合的集合"——表是行的集合，行是字段值的元组
- 域定义了属性的合法取值范围（类型 + 约束）
- SQL 表 ≠ 严格的关系：表允许重复行、NULL、有序
- dify 用 SQLAlchemy 的 `Mapped[T]` 类型注解表达"属性 + 域"

## 5. 练习题

### 练习 1：基础
给定学生表 `students(id, name, age, grade)`，用 Python 字典表示 3 条元组，并定义每个属性的域。

### 练习 2：进阶
阅读 `dify/api/models/workflow.py`，找出 Workflow 关系的所有属性及其域（字段类型）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/account.py`
- `/Users/xu/code/github/dify/api/models/base.py`
- 《数据库系统概念》（Silberschatz）第 2 章：关系模型
- Codd 1970 论文："A Relational Model of Data for Large Shared Data Banks"

---

**文档版本**：v1.0
**最后更新**：2026-07-13