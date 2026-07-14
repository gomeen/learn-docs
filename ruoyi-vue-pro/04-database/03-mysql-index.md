# 03 MySQL 索引原理与优化

> 索引是 MySQL 性能的核心。理解 B+Tree 索引的工作机制，是看懂 ruoyi 表设计的关键。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 B+Tree 索引的底层结构
- 掌握聚簇索引与二级索引的区别
- 掌握联合索引的「最左前缀原则」
- 知道哪些场景会导致索引失效

## 📚 前置知识

- 01-mysql-basics.md
- B-Tree / B+Tree 数据结构（基础）

## 1. 核心概念

### 1.1 什么是索引？

索引是数据的「目录」，帮助 MySQL 快速定位数据，避免全表扫描（Full Table Scan）。

### 1.2 B+Tree 索引结构

```
            ┌─────────────┐
            │ 50  |  100  │   ← 非叶子节点：只存索引键 + 指针
            └──┬───┬──────┘
        ┌──────┘   └─────┐
   ┌────┴────┐      ┌────┴────┐
   │30  40 50│      │60 80 100│   ← 叶子节点：存索引键 + 数据指针
   └─────────┘      └─────────┘
```

- 叶子节点之间用**双向链表**连接，便于范围查询
- 数据存储在叶子节点 → 同层节点可一次 IO 读取多个

### 1.3 聚簇索引 vs 二级索引

| 类型 | 存储内容 | 数量 |
|------|---------|------|
| 聚簇索引（Clustered） | 索引键 + 完整行数据 | 每表 1 个（主键） |
| 二级索引（Secondary） | 索引键 + 主键值 | 多个 |

- **聚簇索引**：InnoDB 表数据按主键组织，所以主键查询最快
- **二级索引查询**：先找到主键值 → 回表（再查聚簇索引）→ 得到完整行

### 1.4 最左前缀原则

联合索引 `(a, b, c)` 相当于建立了：
- `a`
- `a, b`
- `a, b, c`

但**无法命中** `b` 或 `b, c`（没有 a 开头）。

## 2. 代码示例

### 2.1 创建索引

```sql
-- 主键索引（创建表时）
CREATE TABLE user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT
);

-- 唯一索引
CREATE UNIQUE INDEX uk_email ON user(email);

-- 普通联合索引（最常用）
CREATE INDEX idx_name_status ON user(name, status);

-- 删除索引
DROP INDEX idx_name_status ON user;
```

### 2.2 EXPLAIN 分析 SQL

```sql
EXPLAIN SELECT * FROM system_user
WHERE username = 'admin' AND status = 0;
```

关键字段说明：
- `type`：访问类型（system > const > eq_ref > ref > range > index > ALL）
- `key`：实际使用的索引名
- `rows`：预估扫描行数
- `Extra`：额外信息（如 `Using index` 表示覆盖索引，无需回表）

### 2.3 索引失效的常见情况

```sql
-- ❌ 索引失效：LIKE 以 % 开头
SELECT * FROM user WHERE username LIKE '%admin%';

-- ✅ 走索引：LIKE 前缀匹配
SELECT * FROM user WHERE username LIKE 'admin%';

-- ❌ 索引失效：函数操作
SELECT * FROM user WHERE UPPER(username) = 'ADMIN';

-- ❌ 索引失效：类型转换（username 是 varchar，传数字会全表扫描）
SELECT * FROM user WHERE username = 123;

-- ❌ 索引失效：OR 条件（除非两边都有索引）
SELECT * FROM user WHERE username = 'admin' OR email = 'a@b.com';
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 表的索引设计

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/sql/mysql/ruoyi-vue-pro.sql`
**核心代码**（system_user 建表，节选）：

```sql
CREATE TABLE `system_user` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username` varchar(30) NOT NULL COMMENT '用户账号',
  `password` varchar(100) NOT NULL DEFAULT '' COMMENT '密码',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '状态（0正常 1停用）',
  `email` varchar(50) DEFAULT '' COMMENT '邮箱',
  `mobile` varchar(11) DEFAULT '' COMMENT '手机号码',
  ...
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_username` (`tenant_id`,`username`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_mobile` (`mobile`) USING BTREE,
  KEY `idx_tenant_id` (`tenant_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户信息表';
```

**解读**：
- 第 13 行：`UNIQUE KEY uk_username (tenant_id, username)` —— **联合唯一索引**，保证「同一租户下用户名唯一」（多租户设计的典型模式）
- 第 14-16 行：单列索引（按状态、手机号查询）
- 第 17 行：`idx_tenant_id` —— 多租户隔离的必备索引
- **设计意图**：所有查询都能命中索引，没有全表扫描风险

### 3.2 role_menu 关联表的索引

```sql
CREATE TABLE `system_role_menu` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `role_id` bigint NOT NULL,
  `menu_id` bigint NOT NULL,
  ...
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_role_id` (`role_id`) USING BTREE,
  KEY `idx_menu_id` (`menu_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**解读**：
- **双外键索引**：`role_id` 和 `menu_id` 各自有索引，因为查询场景通常是：
  - 给定 role_id，查询所有菜单（`SELECT * WHERE role_id = ?`）
  - 给定 menu_id，查询所有角色（`SELECT * WHERE menu_id = ?`）
- 这种设计让两个方向的查询都走索引，不会全表扫描

## 4. 关键要点总结

- 索引是空间换时间：写慢查快
- **最左前缀原则**：联合索引必须从最左列开始用
- 主键推荐用**自增 BIGINT**：避免页分裂
- InnoDB 必须有主键（若无显式主键，会选一个非空唯一索引，否则生成隐藏 row_id）
- 索引失效场景：LIKE '%xxx'、函数、类型转换、OR、NOT IN

## 5. 练习题

### 练习 1：基础（必做）

给定表 `system_user(username, email, status, deleted)`，为以下查询设计最佳索引：
```sql
SELECT * FROM system_user WHERE username = ? AND status = ?;
SELECT * FROM system_user WHERE email = ?;
SELECT * FROM system_user WHERE status = ?;
```

### 练习 2：进阶

阅读 `ruoyi-vue-pro.sql`，统计：哪张表的索引数量最多？它的索引都是什么类型？这张表的典型查询场景是什么？

### 练习 3：挑战（选做）

执行 `EXPLAIN SELECT * FROM system_user WHERE username = 'admin';`，记录 `type/key/rows/Extra` 字段值。然后尝试 `EXPLAIN SELECT * FROM system_user WHERE SUBSTRING(username, 1, 5) = 'admin';`，对比两次结果，说明索引是否生效。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/sql/mysql/ruoyi-vue-pro.sql`
- MySQL InnoDB 索引：https://dev.mysql.com/doc/refman/8.0/en/innodb-indexes.html
- 《高性能 MySQL》索引章节
- 极客时间 - MySQL 实战 45 讲（索引章节）

---

**文档版本**：v1.0
**最后更新**：2026-07-13