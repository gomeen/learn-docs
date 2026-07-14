# 01 MySQL 基础：CRUD / JOIN / 索引

> MySQL 是 ruoyi-vue-pro 默认数据库，掌握 CRUD 与 JOIN 是后续学习 MyBatis Plus 的基础。

## 🎯 学习目标

完成本文档后，你将能够：
- 熟练编写 MySQL 的 CRUD 语句
- 理解 INNER JOIN / LEFT JOIN 的差异
- 掌握索引的基本概念（B-Tree、主键、唯一索引、普通索引）
- 能阅读 ruoyi SQL 初始化脚本中的建表语句

## 📚 前置知识

- 基本的 SQL 概念（SELECT、WHERE、INSERT）
- Java 基础（阅读示例代码）

## 1. 核心概念

### 1.1 CRUD 四种操作

| 操作 | SQL 关键字 | 说明 |
|------|-----------|------|
| 创建 | `INSERT` | 插入一行或多行 |
| 查询 | `SELECT` | 支持条件、排序、分组 |
| 更新 | `UPDATE` | 修改现有记录 |
| 删除 | `DELETE` | 物理删除（注意与逻辑删除的区别） |

### 1.2 JOIN 类型对比

```
INNER JOIN：只返回两表匹配的行（A ∩ B）
LEFT JOIN ：返回左表全部 + 右表匹配（无匹配则为 NULL）
RIGHT JOIN：与 LEFT 相反（实际很少用）
```

### 1.3 索引的核心作用

- **B-Tree 索引**（最常见）：加速等值查询和范围查询（`=`、`>`、`<`、`BETWEEN`）
- **主键索引**：唯一且非空，每张表只能有一个
- **唯一索引**：值不可重复，可有多个
- **普通索引**：纯加速，无约束

## 2. 代码示例

### 2.1 基础 CRUD

```sql
-- 1. 插入
INSERT INTO system_role(name, code, sort, status, type)
VALUES ('管理员', 'admin', 1, 0, 1);

-- 2. 条件查询
SELECT id, name, code FROM system_role
WHERE status = 0 AND deleted = FALSE
ORDER BY sort ASC;

-- 3. 更新
UPDATE system_role SET name = '超级管理员' WHERE id = 1;

-- 4. 删除（物理删除）
DELETE FROM system_role WHERE id = 999;
```

### 2.2 JOIN 查询示例

```sql
-- 查询用户及其角色（INNER JOIN：只返回有角色的用户）
SELECT u.id, u.username, r.name AS role_name
FROM system_user u
INNER JOIN system_user_role ur ON u.id = ur.user_id
INNER JOIN system_role r ON ur.role_id = r.id
WHERE u.deleted = FALSE;

-- LEFT JOIN：返回所有用户，无角色则显示 NULL
SELECT u.id, u.username, r.name AS role_name
FROM system_user u
LEFT JOIN system_user_role ur ON u.id = ur.user_id
LEFT JOIN system_role r ON ur.role_id = r.id;
```

### 2.3 创建索引

```sql
-- 单列索引
CREATE INDEX idx_username ON system_user(username);

-- 联合索引（最左前缀原则：先按 username 查，再按 status 查可命中）
CREATE INDEX idx_username_status ON system_user(username, status);

-- 唯一索引
CREATE UNIQUE INDEX uk_email ON system_user(email);
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 核心业务表：system_role

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/sql/mysql/ruoyi-vue-pro.sql`
**核心代码**（system_role 建表语句）：

```sql
CREATE TABLE `system_role` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '角色ID',
  `name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '角色名称',
  `code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '角色权限字符串',
  `sort` int NOT NULL COMMENT '显示顺序',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '角色状态（0正常 1停用）',
  `type` tinyint NOT NULL DEFAULT '2' COMMENT '角色类型（1系统角色 2自定义）',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  `creator` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updater` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted` bit(1) NOT NULL DEFAULT b'0' COMMENT '是否删除',
  `tenant_id` bigint NOT NULL DEFAULT '0' COMMENT '租户编号',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_code` (`code`) USING BTREE,
  KEY `idx_tenant_id` (`tenant_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色信息表';
```

**解读**：
- 第 1-13 行：列定义使用 `utf8mb4` 字符集，能存 emoji 和复杂中文
- 第 14 行：`creator/updater` 使用 `varchar(64)` 而不是 BIGINT，原因见 `BaseDO.java` 注释「未来可能会存在非数值的情况」
- 第 17-19 行：索引设计——主键 + 业务索引 `idx_code`（按角色编码查找）+ 租户索引 `idx_tenant_id`（多租户隔离）
- **关键设计**：`deleted bit(1) NOT NULL DEFAULT b'0'` —— MyBatis Plus 逻辑删除字段

### 3.2 角色-菜单关联表

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/sql/mysql/ruoyi-vue-pro.sql`

```sql
CREATE TABLE `system_role_menu` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增编号',
  `role_id` bigint NOT NULL COMMENT '角色ID',
  `menu_id` bigint NOT NULL COMMENT '菜单ID',
  `creator` varchar(64) DEFAULT '',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updater` varchar(64) DEFAULT '',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` bit(1) NOT NULL DEFAULT b'0',
  `tenant_id` bigint NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_role_id` (`role_id`) USING BTREE,
  KEY `idx_menu_id` (`menu_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色和菜单关联表';
```

**解读**：
- **典型多对多中间表**：role_id + menu_id 复合唯一
- **双外键索引**：`idx_role_id`、`idx_menu_id` 分别加速「按角色查菜单」「按菜单查角色」两个方向的查询

## 4. 关键要点总结

- CRUD 是最基础的操作，复杂 SQL 都是其组合
- JOIN 中最常用的是 `INNER JOIN` 和 `LEFT JOIN`
- 索引不是越多越好：每多一个索引，写入会变慢，占用存储
- 联合索引遵循**最左前缀原则**
- ruoyi 表设计遵循「每张业务表都有 `creator/create_time/updater/update_time/deleted/tenant_id`」规范

## 5. 练习题

### 练习 1：基础（必做）

编写 SQL：查询 `system_user` 表中所有 username 包含 "admin" 的用户，按 id 降序排列，只返回前 10 条。

**参考答案**：见 `solutions/01-mysql-basics-solution.md`

### 练习 2：进阶

阅读 `ruoyi-vue-pro.sql`，找出所有以 `idx_` 开头的索引，说明它们各自的查询场景。

### 练习 3：挑战（选做）

设计一张「商品-订单」表的 SQL DDL：商品、订单、订单项三张表，并写出「查询某用户最近 30 天购买的所有商品名称和数量」的 SQL（要求用到 JOIN 和 GROUP BY）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/sql/mysql/ruoyi-vue-pro.sql`
- MySQL 官方文档：https://dev.mysql.com/doc/refman/8.0/en/
- 极客时间 - MySQL 实战 45 讲

---

**文档版本**：v1.0
**最后更新**：2026-07-13