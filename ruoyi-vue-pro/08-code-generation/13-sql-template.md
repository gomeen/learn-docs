# 3.4 ruoyi 的 SQL 模板

> 学习 ruoyi 生成的 SQL 脚本：菜单 SQL、H2 测试建表 SQL。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释生成 SQL 的两个文件：`sql.vm` 和 `h2.vm`
- 理解菜单 SQL 的结构和 6 类操作权限
- 理解不同数据库（MySQL/Oracle/PG/...）的语法差异
- 自己执行生成的菜单 SQL 把新模块接入后台

## 📚 前置知识

- 阅读过 `10-velocity.md`、`11-java-template.md`
- 基本的 SQL 语法（INSERT）
- 了解 ruoyi 菜单表 `system_menu` / 角色表 `system_role_menu`

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

## 3. ruoyi 仓库源码解读

### 3.1 sql.vm 多数据库分发

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/sql/sql.vm`
**关键代码**（行 1-30，简化）：

```velocity
#set ($functionNames = ['查询', '创建', '更新', '删除', '导出'])
#if ($importEnable)
#set ($functionNames = ['查询', '创建', '更新', '删除', '导出', '导入'])
#end
#set ($functionOps = ['query', 'create', 'update', 'delete', 'export'])
#if ($importEnable)
#set ($functionOps = ['query', 'create', 'update', 'delete', 'export', 'import'])
#end

## ======================= MySQL / OceanBase =======================
#if ($dbType.name() == 'MYSQL' || $dbType.name() == 'OCEAN_BASE')
## 父菜单
INSERT INTO system_menu (name, permission, type, sort, parent_id, path, icon, component, status, component_name)
VALUES ('${table.classComment}', '', 1, ${...}, ${table.parentMenuId}, '${simpleClassName_strikeCase}', 'list', '${sceneEnum.basePackage}/${table.businessName}/index', 0, '${table.className}');
SET @parentId = LAST_INSERT_ID();

## 按钮菜单
INSERT INTO system_menu (name, permission, type, sort, parent_id, path, icon, component, status, component_name)
VALUES
#foreach($funcName in $functionNames)
#if($foreach.index > 0),#end
  ('${table.classComment}${funcName}', '${permissionPrefix}:$functionOps[$foreach.index]', 2, $foreach.index, @parentId, '', '', '', 0, '')
#end;

## ======================= Oracle / DM =======================
#elseif ($dbType.name() == 'ORACLE' || $dbType.name() == 'DM')
-- Oracle 用 sequence，语法不同
INSERT INTO system_menu (...) VALUES (...) RETURNING id INTO parentId;

## ======================= PostgreSQL / Kingbase =======================
#elseif ($dbType.name() == 'POSTGRE_SQL' || $dbType.name() == 'KINGBASE_ES')
INSERT INTO system_menu (...) VALUES (...) RETURNING id INTO parentId;

## ======================= SQL Server =======================
#elseif ($dbType.name() == 'SQL_SERVER')
INSERT INTO system_menu (...) VALUES (...); SET @parentId = SCOPE_IDENTITY();
#end
```

**关键占位符**：
- `${table.classComment}` → "字典类型"
- `${table.parentMenuId}` → 用户配置父菜单 ID
- `${simpleClassName_strikeCase}` → `dict-type`（菜单路径）
- `${sceneEnum.basePackage}` → `admin`（前端路由目录）
- `${permissionPrefix}` → `system:dict-type`
- `$foreach.index` → 当前循环索引（0-based）
- `$foreach.count` → 当前循环计数（1-based）

### 3.2 h2.vm 测试库建表

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/sql/h2.vm`
**完整代码**：

```velocity
-- 将该建表 SQL 语句，添加到 yudao-module-${table.moduleName} 模块的 test/resources/sql/create_tables.sql 文件中
-- 注意：必须在导入表结构之前，先删除该表
DROP TABLE IF EXISTS "${table.tableName.toLowerCase()}";

CREATE TABLE IF NOT EXISTS "${table.tableName.toLowerCase()}" (
#foreach($column in $columns)
#if($column.primaryKey)
  "$column.columnName" $column.dataType NOT NULL PRIMARY KEY#if($foreach.hasNext || $table.subTables),#end

#elseif($column.createOperation || $column.updateOperation || $column.listOperation)
  "$column.columnName" $column.dataType#if(!$column.nullable) NOT NULL#end DEFAULT NULL#if($foreach.hasNext || $table.subTables),#end

#else
  "$column.columnName" $column.dataType DEFAULT NULL#if($foreach.hasNext || $table.subTables),#end
#end
#end
);

-- 添加注释
COMMENT ON COLUMN "${table.tableName.toLowerCase()}".id IS '编号';
-- ... 其他字段注释
```

**解读**：
- H2 SQL 用了 `"字段名"`（双引号）—— 区分大小写
- `DROP TABLE IF EXISTS` 确保可重复执行
- 给主键加 `PRIMARY KEY` 约束
- 字符串字段通常 `DEFAULT NULL`，数字字段可以 `DEFAULT 0`
- 这个 SQL 会被 ServiceTest 用到，所以 H2 表结构必须和 MySQL 兼容

### 3.3 CodegenEngine 中 SQL 模板的注册

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/inner/CodegenEngine.java` 行 96-98

```java
// SQL
.put("codegen/sql/sql.vm", "sql/sql.sql")
.put("codegen/sql/h2.vm", "sql/h2.sql")
```

**解读**：
- 注意路径是 `"codegen/sql/sql.vm"`（没有 `java/` 前缀）—— 模板路径自定义
- 生成文件命名为 `sql.sql` / `h2.sql`（不带 `.vm`）
- `h2.vm` 仅在 `unitTestEnable=true` 时生成（行 593）

## 4. 关键要点总结

- `sql.vm` 生成**菜单 + 权限** INSERT，**不是建表 DDL**
- `h2.vm` 生成 H2 测试库建表 SQL（用于单元测试）
- 6 个权限点：query / create / update / delete / export / import（最后 1 个可选）
- 多数据库通过 `#if ($dbType.name() == '...')` 分发
- MySQL 用 `LAST_INSERT_ID()`、Oracle 用 `RETURNING id INTO`、SQL Server 用 `SCOPE_IDENTITY()`

## 5. 练习题

### 练习 1：基础（必做）

打开 `sql.vm`，列出它分发的**所有数据库类型**（至少 4 种）。

### 练习 2：进阶

对表 `system_dict_type`（`module=system, className=DictType, businessName=dict, parentMenuId=100`），写出生成的"查询"按钮的 INSERT 语句完整 SQL。

### 练习 3：挑战（选做）

如果想新增"打印"权限点（`print`），需要修改 SQL 模板 + Java Controller 模板。列出所有需要修改的位置。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/sql/sql.vm`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/sql/h2.vm`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/inner/CodegenEngine.java`
- 官方文档：https://doc.iocoder.cn/codegen/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
