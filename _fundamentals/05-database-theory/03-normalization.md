# 1.3 函数依赖与范式：1NF / 2NF / 3NF / BCNF

> 范式（Normal Form）是衡量关系模式"好坏"的标准。规范化可以减少冗余、避免更新异常。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解函数依赖（FD）的概念
- 区分 1NF、2NF、3NF、BCNF 的区别
- 判断一个关系符合哪个范式
- 在 dify/ruoyi 中识别范式应用

## 📚 前置知识

- 01-relational-model.md
- 主键、外键概念

## 1. 核心概念

### 1.1 函数依赖（Functional Dependency）

记号：`X → Y` 表示"X 函数决定 Y"（即 X 相同则 Y 相同）。

**举例**：在学生表 `(学号, 姓名, 学院, 院长)` 中：
- `学号 → 姓名`
- `学号 → 学院`
- `学院 → 院长`（每个学院只有一个院长）

### 1.2 四大范式

| 范式 | 要求 | 主要消除的问题 |
|------|------|---------------|
| 1NF | 属性不可分（原子性） | 重复字段、多值字段 |
| 2NF | 1NF + 消除部分函数依赖 | 部分依赖 |
| 3NF | 2NF + 消除传递函数依赖 | 传递依赖 |
| BCNF | 3NF + 每个决定因素都是候选键 | 主属性对候选键的部分依赖 |

### 1.3 异常问题

未规范化的表会出现三类异常：
- **插入异常**：无法插入某些信息（因为缺主键）
- **更新异常**：修改一处需要改多处（数据冗余）
- **删除异常**：删除信息时连带丢失其他信息

### 1.4 范式递进关系

```
1NF ⊃ 2NF ⊃ 3NF ⊃ BCNF
```
满足 BCNF 必然满足 3NF，反之不一定。

## 2. 代码示例

### 2.1 反例：未规范化的表

```python
# ❌ 不符合 1NF：电话字段有多个值
unnormalized = [
    {"id": 1, "name": "Alice", "phones": "123-4567, 234-5678"},  # 违反原子性
]
```

### 2.2 符合 1NF 但不符合 2NF

```python
# 表: enrollment(学号, 课程号, 姓名, 学分)
# 主键: (学号, 课程号)
# 函数依赖: (学号, 课程号) → 学分; 学号 → 姓名
# 问题: 姓名只依赖于学号（部分依赖）→ 不符合 2NF

# ✅ 拆分为两张表
students = [
    {"学号": 1, "姓名": "Alice"},     # 学号 → 姓名
]
courses = [
    {"课程号": 101, "学分": 3},        # 课程号 → 学分
]
enrollments = [
    {"学号": 1, "课程号": 101},        # 联接表
]
```

### 2.3 符合 2NF 但不符合 3NF

```python
# 表: students(学号, 姓名, 学院, 院长)
# 学号 → 学院 → 院长 (传递依赖)
# ✅ 拆分
students_v2 = [
    {"学号": 1, "姓名": "Alice", "学院": "CS"},
]
departments = [
    {"学院": "CS", "院长": "Dr. Smith"},
]
```

### 2.4 用 Python 判定范式

```python
def is_3nf(relation: list[dict], fds: list[tuple[set, set]]) -> bool:
    """简化版 3NF 判定"""
    # 找候选键（简化处理：假设第一个是主键）
    keys = [set(k) for k, _ in fds if k]
    for x, y in fds:
        # 检查 X → Y：Y 中每个属性是否被任意候选键蕴含
        if not (y <= x or any(k <= x for k in keys)):
            return False
    return True
```

## 3. dify 仓库源码解读

### 3.1 dify 模型符合 3NF 设计

**文件位置**：`/Users/xu/code/github/dify/api/models/account.py`
**核心代码**（行 1-50）：

```python
class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))

class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))

class TenantAccountJoin(Base):
    """账户-租户多对多关联表（符合 BCNF）。"""
    __tablename__ = "tenant_account_joins"
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    role: Mapped[str] = mapped_column(String(16))
    current: Mapped[bool] = mapped_column(Boolean, default=False)
```

**解读**：
- 拆分成 3 张表：`Account`、`Tenant`、`TenantAccountJoin`，每张表只描述一个实体
- `TenantAccountJoin` 只包含外键和角色——符合 BCNF（消除冗余）
- **设计意图**：账户和租户是多对多关系，必须用关联表；属性互不依赖

## 4. 关键要点总结

- 范式是为了减少冗余、避免更新异常
- 1NF → 2NF → 3NF → BCNF，要求逐步严格
- 实际工程中通常达到 3NF 即可，不必追求 BCNF（影响性能）
- dify 模型拆分清晰，达到 3NF/BCNF

## 5. 练习题

### 练习 1：基础
订单表 `orders(id, user_id, user_name, product_id, product_name, qty)` 有哪些函数依赖？是否符合 3NF？如何拆分？

### 练习 2：进阶
阅读 `dify/api/models/dataset.py`，分析 Document 模型的范式级别。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/account.py`
- 《数据库系统概念》第 8 章：规范化
- https://en.wikipedia.org/wiki/Database_normalization

---

**文档版本**：v1.0
**最后更新**：2026-07-13