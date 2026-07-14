# 05 数据库设计：三大范式

> 数据库范式是表设计的理论基础。ruoyi 的表设计虽然部分反范式（如冗余 tenant_id），但仍遵循范式精神。

## 🎯 学习目标

完成本文档后，你将能够：
- 说出三大范式（1NF / 2NF / 3NF）的核心要求
- 识别常见的设计反范式场景
- 理解反范式与性能的权衡
- 评估 ruoyi 的表设计是否合理

## 📚 前置知识

- 01-mysql-basics.md

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

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的反范式：每个表都冗余 tenant_id

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/sql/mysql/ruoyi-vue-pro.sql`
**核心代码**（system_role 建表）：

```sql
CREATE TABLE `system_role` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(30) NOT NULL,
  `code` varchar(100) NOT NULL,
  ...
  `tenant_id` bigint NOT NULL DEFAULT '0' COMMENT '租户编号',
  ...
  PRIMARY KEY (`id`),
  KEY `idx_tenant_id` (`tenant_id`)
) ENGINE=InnoDB COMMENT='角色信息表';
```

**解读**：
- **反范式设计**：tenant_id 应该在租户表，理论上需要 JOIN tenant 表查询租户名
- **为什么冗余**：几乎每条 SQL 都要按 tenant_id 过滤（多租户隔离），冗余字段可以避免 JOIN 提升性能
- **代价**：写入时需保证 tenant_id 一致（通过 `TenantContextHolder` 自动设置）

### 3.2 ruoyi 的多对多中间表设计

**文件位置**：同文件，`system_role_menu` 表

```sql
CREATE TABLE `system_role_menu` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `role_id` bigint NOT NULL,
  `menu_id` bigint NOT NULL,
  `creator` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `updater` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` bit(1) NOT NULL DEFAULT b'0',
  `tenant_id` bigint NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_role_id` (`role_id`),
  KEY `idx_menu_id` (`menu_id`)
) ENGINE=InnoDB COMMENT='角色和菜单关联表';
```

**解读**：
- **符合 3NF**：角色名/菜单名都不冗余，只存外键
- **冗余字段**：`creator/create_time/updater/update_time/deleted/tenant_id` —— 这些是「通用审计字段」，每个表都冗余是 ORM 框架的设计需要（`BaseDO` 自动填充）
- **设计意图**：业务数据严格遵循 3NF；审计字段和租户字段作为通用规范冗余

## 4. 关键要点总结

- 三大范式核心是「**减少数据冗余**」
- 反范式核心是「**性能优化**」（冗余换查询性能）
- 设计原则：先遵循范式，再针对热点查询反范式
- ruoyi 的设计哲学：业务数据遵循 3NF；审计字段/租户字段冗余以支持通用能力

## 5. 练习题

### 练习 1：基础（必做）

判断以下表是否符合 3NF，如不符合，请拆分：
```sql
CREATE TABLE student_score (
    student_id BIGINT,
    student_name VARCHAR(50),  -- 违规：传递依赖
    course_id BIGINT,
    course_name VARCHAR(50),   -- 违规：传递依赖
    score DECIMAL(5,2),
    teacher_name VARCHAR(50),  -- 违规：传递依赖
    PRIMARY KEY (student_id, course_id)
);
```

### 练习 2：进阶

阅读 ruoyi 的 `system_user`、`system_role`、`system_role_menu` 三张表，分析哪些字段是冗余的、为什么这么设计。

### 练习 3：挑战（选做）

设计一个「文章系统」的数据库（含文章、作者、分类、标签、评论），要求：
1. 严格遵循 3NF
2. 列出至少 2 处可以反范式的优化点
3. 写出「查询某分类下点赞数最多的 10 篇文章」的 SQL

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/sql/mysql/ruoyi-vue-pro.sql`
- 《数据库系统概念》第三范式章节
- 范式与反范式：https://www.cnblogs.com/xiaoxiong/articles/6045292.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13