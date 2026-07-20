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
| 删除 | `DELETE` | 物理删除（注意与逻辑删除的区别；逻辑删除见 [15-logic-delete](./18-logic-delete.md)） |

### 1.2 JOIN 类型对比

```
INNER JOIN：只返回两表匹配的行（A ∩ B）
LEFT JOIN ：返回左表全部 + 右表匹配（无匹配则为 NULL）
RIGHT JOIN：与 LEFT 相反（实际很少用）
```

### 1.3 索引的核心作用

> 📌 **Sighting**：B+Tree、最左前缀、索引失效见 [03-mysql-index](./03-mysql-index.md)。此处只建立「索引能加速查询」的直觉。

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

## 3. 关键要点总结

- CRUD 是最基础的操作，复杂 SQL 都是其组合
- JOIN 中最常用的是 `INNER JOIN` 和 `LEFT JOIN`
- 索引不是越多越好：每多一个索引，写入会变慢，占用存储
- 联合索引遵循**最左前缀原则**
- ruoyi 表设计遵循「每张业务表都有 `creator/create_time/updater/update_time/deleted/tenant_id`」规范

---

**文档版本**：v1.0
**最后更新**：2026-07-13
