# 1.2 关系代数：选择 / 投影 / 联接 / 除

> 关系代数是 SQL 的理论基础。理解关系代数能让你写出更高效的查询。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 5 个基本关系代数运算：并、差、积、选择、投影
- 掌握 4 个扩展运算：联接、自然联接、除、交
- 把 SQL 查询翻译为关系代数表达式
- 在 dify / ruoyi 中识别出关系代数运算

## 📚 前置知识

- 01-relational-model.md
- SQL 基础（WHERE、SELECT、JOIN）

## 1. 核心概念

### 1.1 五种基本运算

| 运算 | 符号 | SQL 对应 | 说明 |
|------|------|---------|------|
| 选择 | σ | WHERE | 按条件过滤行 |
| 投影 | π | SELECT 列 | 选取指定列 |
| 笛卡尔积 | × | FROM 多表（无连接条件） | 两两组合 |
| 并 | ∪ | UNION | 合并去重 |
| 差 | − | EXCEPT | 集合差 |

### 1.2 重要扩展运算

| 运算 | 定义 | SQL 对应 |
|------|------|---------|
| 联接（θ-join） | σ_条件(R × S) | INNER JOIN ... ON |
| 自然联接 | R ⋈ S | NATURAL JOIN |
| 除 | R ÷ S | NOT EXISTS 子查询 |
| 重命名 | ρ | 表别名 |

### 1.3 关系代数与 SQL 的对应

```
π_name(σ_age>18(users))   →   SELECT name FROM users WHERE age > 18
users ⋈ orders            →   users JOIN orders ON users.id = orders.user_id
π_user_id(orders) - π_user_id(users)   →   SELECT user_id FROM orders EXCEPT SELECT id FROM users
```

## 2. 代码示例

### 2.1 用 Python 实现关系代数运算

```python
from typing import Callable, Any

# 模拟关系（表）
users = [
    {"id": 1, "name": "Alice", "age": 30, "dept_id": 10},
    {"id": 2, "name": "Bob",   "age": 25, "dept_id": 20},
    {"id": 3, "name": "Carol", "age": 35, "dept_id": 10},
]

orders = [
    {"id": 101, "user_id": 1, "amount": 100},
    {"id": 102, "user_id": 1, "amount": 200},
    {"id": 103, "user_id": 2, "amount": 50},
]

depts = [
    {"dept_id": 10, "dept_name": "Engineering"},
    {"dept_id": 20, "dept_name": "Sales"},
]

# ===== 1. 选择 σ = WHERE =====
def select(relation: list[dict], condition: Callable[[dict], bool]) -> list[dict]:
    """σ_condition(R)：按条件过滤行"""
    return [t for t in relation if condition(t)]

result = select(users, lambda t: t["age"] > 25)
# [{'id': 1, ...}, {'id': 3, ...}]  -- Alice 和 Carol

# ===== 2. 投影 π = SELECT 列 =====
def project(relation: list[dict], columns: list[str]) -> list[dict]:
    """π_A1,A2(R)：选取指定列（同时去重）"""
    seen = set()
    result = []
    for t in relation:
        key = tuple(t[c] for c in columns)
        if key not in seen:
            seen.add(key)
            result.append({c: t[c] for c in columns})
    return result

result = project(users, ["name", "age"])
# [{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}, {'name': 'Carol', 'age': 35}]

# ===== 3. 笛卡尔积 × =====
def cartesian(R: list[dict], S: list[dict]) -> list[dict]:
    """R × S：两两组合"""
    return [{**r, **s} for r in R for s in S]

# ===== 4. 自然联接 ⋈ =====
def natural_join(R: list[dict], S: list[dict]) -> list[dict]:
    """R ⋈ S：按同名列自动联接"""
    common = set(R[0].keys()) & set(S[0].keys())
    result = []
    for r in R:
        for s in S:
            if all(r[k] == s[k] for k in common):
                merged = {**r, **{k: v for k, v in s.items() if k not in common}}
                result.append(merged)
    return result

joined = natural_join(users, depts)
# 联接后得到 users 的 name/age + depts 的 dept_name
```

### 2.2 复杂查询：嵌套关系代数

```python
# 找出"所有下过单的用户"——用关系代数表达
# π_users.name ( users ⋈ (π_user_id(orders)) )

users_who_ordered = project(
    natural_join(users, project(orders, ["user_id"])),
    ["id", "name"]
)
```

## 3. dify 仓库源码解读

### 3.1 SQLAlchemy 查询：选择 + 投影 + 联接

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 50-80）：

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.account import Account, Tenant, TenantAccountJoin

def get_user_tenants(user_id: str) -> list[Tenant]:
    """获取用户所属的所有租户——关系代数：π(σ(join))"""
    with Session(db.engine) as session:
        stmt = (
            select(Tenant)                                    # π（投影到 Tenant）
            .join(TenantAccountJoin,                         # ⋈（联接）
                  Tenant.id == TenantAccountJoin.tenant_id)
            .where(TenantAccountJoin.account_id == user_id)  # σ（选择）
        )
        return list(session.scalars(stmt).all())
```

**解读**：
- 第 13-15 行：`select().join().where()` ——这就是 σ⋈π 的链式表达
- 第 11 行：SQLAlchemy 自动生成 SQL `SELECT tenants.* FROM tenants JOIN tenant_account_joins ON ... WHERE ...`
- **关键设计**：用 Python 方法链替代 SQL 字符串，更安全（防 SQL 注入）

## 4. 关键要点总结

- 关系代数是 SQL 的数学基础，5 个基本运算 + 4 个扩展运算
- `SELECT` ≈ 投影（π），`WHERE` ≈ 选择（σ），`JOIN` ≈ 联接（⋈）
- 关系代数运算可以嵌套组合成复杂查询
- dify 用 SQLAlchemy 的链式调用表达关系代数

## 5. 练习题

### 练习 1：基础
把以下 SQL 翻译为关系代数：`SELECT name FROM users WHERE age > 25`

### 练习 2：进阶
阅读 `dify/api/services/dataset_service.py`，找出一个同时使用选择、投影、联接的查询，并用关系代数表达。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/account_service.py`
- `/Users/xu/code/github/dify/api/models/account.py`
- 《数据库系统概念》第 2 章：关系代数

---

**文档版本**：v1.0
**最后更新**：2026-07-13