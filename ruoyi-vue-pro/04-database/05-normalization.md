# 05 数据库设计：三大范式

> 数据库范式是表设计的理论基础。ruoyi 的表设计虽然部分反范式（如冗余 tenant_id），但仍遵循范式精神。

## 🎯 学习目标

完成本文档后，你将能够：
- 说出三大范式（1NF / 2NF / 3NF）的核心要求
- 识别常见的设计反范式场景
- 理解反范式与性能的权衡
- 评估 ruoyi 的表设计是否合理

## 📚 前置知识

- [01-mysql-basics.md](./01-mysql-basics.md)
- 多租户冗余字段设计见 [多租户](../../_common/08-authorization/05-multi-tenant.md)

## 1. 核心概念

### 1.1 第一范式（1NF）

**要求**：每列都是不可分的原子值。

```
❌ 违反 1NF：
address 列存储 "上海市浦东新区张江路 100 号"

✅ 符合 1NF（拆分）：
province = "上海"
city = "上海"
detail = "浦东新区张江路 100 号"
```

### 1.2 第二范式（2NF）

**要求**：在 1NF 基础上，非主键列必须完全依赖于主键（不能只依赖主键的一部分）。

```
❌ 违反 2NF（联合主键 (order_id, product_id)）：
order_detail 表：
- order_id
- product_id
- product_name      ← 只依赖 product_id，不依赖 order_id
- order_date        ← 只依赖 order_id，不依赖 product_id

✅ 符合 2NF（拆分）：
订单表(order_id, order_date, ...)
商品表(product_id, product_name, ...)
订单项表(order_id, product_id, quantity)
```

### 1.3 第三范式（3NF）

**要求**：在 2NF 基础上，非主键列不能传递依赖于主键。

```
❌ 违反 3NF：
student 表：id, name, dept_id, dept_name
              └──────┘    └──────┘
              直接依赖    通过 dept_id 间接依赖 id（传递依赖）

✅ 符合 3NF：
student 表：id, name, dept_id
department 表：dept_id, dept_name
```

### 1.4 反范式设计（性能优化）

```
反范式：故意冗余字段，避免 JOIN

示例：
订单表冗余用户名（user_name）→ 列表查询无需 JOIN user 表
tradeoff：写入时需同步更新冗余字段，可能有短暂不一致
```

## 2. 代码示例

### 2.1 三大范式实例：电商订单系统

```sql
-- ✅ 符合 3NF 的设计

-- 用户表
CREATE TABLE user (
    id BIGINT PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);

-- 商品表
CREATE TABLE product (
    id BIGINT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL
);

-- 订单表（不冗余商品名/价格）
CREATE TABLE orders (
    id BIGINT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- 订单项（联合主键）
CREATE TABLE order_item (
    order_id BIGINT,
    product_id BIGINT,
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL, -- 快照价格（反范式）
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES product(id)
);
```

**说明**：
- 完全符合 1NF/2NF/3NF
- `order_item.unit_price` 是反范式：商品价格会变，但订单历史价格必须保留

### 2.2 反范式实例：冗余用户名

```sql
-- ❌ 严格 3NF：列表查询要 JOIN
CREATE TABLE orders_strict (
    id BIGINT PRIMARY KEY,
    user_id BIGINT NOT NULL
);

-- 查询「用户 x 的所有订单及用户名」
SELECT o.*, u.name FROM orders_strict o
INNER JOIN user u ON o.user_id = u.id;

-- ✅ 反范式：列表查询无需 JOIN（性能更优）
CREATE TABLE orders_denormalized (
    id BIGINT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    user_name VARCHAR(50) NOT NULL, -- 冗余字段
    total_amount DECIMAL(10,2) NOT NULL
);

-- 查询同上，但无需 JOIN
SELECT * FROM orders_denormalized WHERE user_id = ?;
```

## 3. 关键要点总结

- 三大范式核心是「**减少数据冗余**」
- 反范式核心是「**性能优化**」（冗余换查询性能）
- 设计原则：先遵循范式，再针对热点查询反范式
- ruoyi 的设计哲学：业务数据遵循 3NF；审计字段/租户字段冗余以支持通用能力

---

**文档版本**：v1.0
**最后更新**：2026-07-13
