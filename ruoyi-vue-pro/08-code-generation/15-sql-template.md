# 3.4 ruoyi 的 SQL 模板

> 学习 ruoyi 生成的 SQL 脚本：菜单 SQL、H2 测试建表 SQL。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释生成 SQL 的两个文件：`sql.vm` 和 `h2.vm`
- 理解菜单 SQL 的结构和 6 类操作权限
- 理解不同数据库（MySQL/Oracle/PG/...）的语法差异
- 自己执行生成的菜单 SQL 把新模块接入后台

## 📚 前置知识

- Velocity / Java 模板（详见 [Velocity](./12-velocity.md)、[Java 模板](./13-java-template.md)）
- 基本的 SQL 语法（INSERT）
- ruoyi 菜单 / 角色表（详见 [菜单](../07-business-modules/09-menu.md)、[角色](../07-business-modules/08-role.md)）

## 1. 核心概念

### 1.1 SQL 模板只有 2 个

```
codegen/sql/
├── sql.vm   # 主菜单 SQL（多数据库兼容）
└── h2.vm    # H2 测试库建表 SQL
```

### 1.2 生成什么 SQL？

`sql.vm` 生成**菜单 + 权限点**的 INSERT 语句（不是建表 DDL）。例如对 `system_dict_type` 表：

```sql
-- 1. 插入父菜单（如果有）
INSERT INTO system_menu (name, permission, type, ...) VALUES ('字典管理', '', 1, ...);
SET @parentId = LAST_INSERT_ID();

-- 2. 插入子菜单（按钮）
INSERT INTO system_menu (name, permission, type, parent_id) VALUES
  ('字典查询', 'system:dict-type:query', 2, @parentId),
  ('字典创建', 'system:dict-type:create', 2, @parentId),
  ('字典更新', 'system:dict-type:update', 2, @parentId),
  ('字典删除', 'system:dict-type:delete', 2, @parentId),
  ('字典导出', 'system:dict-type:export', 2, @parentId);
```

### 1.3 6 个权限点

| 权限 | HTTP 接口 | 用途 |
|------|----------|------|
| `:query` | GET `/page` | 列表查询 |
| `:create` | POST `/create` | 新建 |
| `:update` | PUT `/update` | 更新 |
| `:delete` | DELETE `/delete` | 删除 |
| `:export` | GET `/export-excel` | 导出 |
| `:import` | POST `/import` | 导入（仅当 importEnable=true） |

## 2. 代码示例

### 2.1 在 Navicat 中执行生成的 SQL

```sql
-- 把生成器输出的 SQL 粘到查询窗口
-- 1. 执行
-- 2. 重启后台服务（让菜单缓存生效）
-- 3. 用 admin 账号登录，应该能看到"字典管理"菜单
```

## 3. 关键要点总结

- `sql.vm` 生成**菜单 + 权限** INSERT，**不是建表 DDL**
- `h2.vm` 生成 H2 测试库建表 SQL（用于单元测试）
- 6 个权限点：query / create / update / delete / export / import（最后 1 个可选）
- 多数据库通过 `#if ($dbType.name() == '...')` 分发
- MySQL 用 `LAST_INSERT_ID()`、Oracle 用 `RETURNING id INTO`、SQL Server 用 `SCOPE_IDENTITY()`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
