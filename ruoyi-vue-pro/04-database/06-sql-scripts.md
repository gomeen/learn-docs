# 06 ruoyi 的 SQL 初始化脚本

> 理解 ruoyi-vue-pro 的初始化 SQL 脚本结构，能帮助你快速搭建数据库环境并理解表设计意图。

## 🎯 学习目标

完成本文档后，你将能够：
- 找到 ruoyi 的 SQL 初始化脚本
- 理解多数据库适配（MySQL、PostgreSQL、Oracle 等）
- 掌握 Quartz 调度表结构
- 能本地初始化 ruoyi 数据库

## 📚 前置知识

- [01-mysql-basics.md](./01-mysql-basics.md)
- SQL DDL 基本语法
- 结构迁移工具见 [07-flyway](./07-flyway.md)

## 1. 核心概念

### 1.1 ruoyi SQL 脚本目录结构

```
sql/
├── db2/                 # IBM DB2
├── dm/                  # 达梦数据库
├── highgo/              # 瀚高数据库
├── kingbase/            # 人大金仓
├── mysql/               # MySQL（最常用）
│   ├── ruoyi-vue-pro.sql  # 主脚本（含所有业务表）
│   └── quartz.sql         # Quartz 调度表
├── opengauss/           # openGauss
├── oracle/              # Oracle
├── postgresql/          # PostgreSQL
├── sqlserver/           # SQL Server
└── tools/               # 工具脚本（如 Redis Lua）
```

### 1.2 多数据库适配策略

ruoyi 通过：
1. 提供每种数据库的独立 SQL 脚本
2. MyBatis Plus 注解（如 `@KeySequence`）兼容不同数据库的自增主键
3. `JdbcUtils.getDbType()` 运行时判断当前数据库类型

### 1.3 Quartz 调度表的作用

Quartz 是 Spring 默认的定时任务调度框架，需要在数据库中持久化：
- 任务定义（QRTZ_JOB_DETAILS）
- 触发器（QRTZ_TRIGGERS）
- 调度历史（QRTZ_FIRED_TRIGGERS）

## 2. 代码示例

### 2.1 MySQL 初始化流程

```bash
# 1. 创建数据库
mysql -u root -p -e "CREATE DATABASE ruoyi-vue-pro DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 2. 导入业务表
mysql -u root -p ruoyi-vue-pro < sql/mysql/ruoyi-vue-pro.sql

# 3. 导入 Quartz 表
mysql -u root -p ruoyi-vue-pro < sql/mysql/quartz.sql

# 4. 验证
mysql -u root -p ruoyi-vue-pro -e "SHOW TABLES;" | head
```

### 2.2 Quartz 表结构

```sql
-- 任务详情表：存储 JobDetail 配置
CREATE TABLE QRTZ_JOB_DETAILS (
    SCHED_NAME        VARCHAR(120) NOT NULL,
    JOB_NAME          VARCHAR(200) NOT NULL,
    JOB_GROUP         VARCHAR(200) NOT NULL,
    DESCRIPTION       VARCHAR(250) NULL,
    JOB_CLASS_NAME    VARCHAR(250) NOT NULL,  -- Job 类全限定名
    IS_DURABLE        VARCHAR(1)   NOT NULL,
    IS_NONCONCURRENT  VARCHAR(1)   NOT NULL,
    IS_UPDATE_DATA    VARCHAR(1)   NOT NULL,
    REQUESTS_RECOVERY VARCHAR(1)   NOT NULL,
    JOB_DATA          BLOB NULL,
    PRIMARY KEY (SCHED_NAME, JOB_NAME, JOB_GROUP)
);

-- 触发器表
CREATE TABLE QRTZ_TRIGGERS (
    SCHED_NAME    VARCHAR(120) NOT NULL,
    TRIGGER_NAME  VARCHAR(200) NOT NULL,
    TRIGGER_GROUP VARCHAR(200) NOT NULL,
    JOB_NAME      VARCHAR(200) NOT NULL,
    JOB_GROUP     VARCHAR(200) NOT NULL,
    ...
    PRIMARY KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP),
    FOREIGN KEY (SCHED_NAME, JOB_NAME, JOB_GROUP)
        REFERENCES QRTZ_JOB_DETAILS(SCHED_NAME, JOB_NAME, JOB_GROUP)
);
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 主脚本：system_menu 菜单表

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/sql/mysql/ruoyi-vue-pro.sql`
**核心代码**（system_menu 建表节选）：

```sql
CREATE TABLE `system_menu` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '菜单ID',
  `name` varchar(50) NOT NULL COMMENT '菜单名称',
  `permission` varchar(100) DEFAULT '' COMMENT '权限标识',
  `type` tinyint DEFAULT NULL COMMENT '菜单类型（M目录 C菜单 F按钮）',
  `sort` int DEFAULT '0' COMMENT '显示顺序',
  `parent_id` bigint DEFAULT '0' COMMENT '父菜单ID',
  `path` varchar(200) DEFAULT '' COMMENT '路由地址',
  `icon` varchar(100) DEFAULT '#' COMMENT '菜单图标',
  `component` varchar(255) DEFAULT NULL COMMENT '组件路径',
  `status` tinyint DEFAULT '1' COMMENT '菜单状态（0显示 1隐藏）',
  `creator` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `updater` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` bit(1) NOT NULL DEFAULT b'0',
  `tenant_id` bigint NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_parent_id` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='菜单权限表';
```

**解读**：
- **菜单类型枚举**：`type` 字段使用 `tinyint`，对应 `M目录/C菜单/F按钮`（前端路由权限常用分类）
- **树形结构**：`parent_id` 字段实现父子层级，配合 `idx_parent_id` 索引加速查询
- **关键字段**：`permission` 用于 Spring Security `@PreAuthorize("hasAuthority('system:user:list')")` 权限控制

### 3.2 多数据库适配：Oracle 脚本示例

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/sql/oracle/`

Oracle 与 MySQL 的差异（节选）：

```sql
-- Oracle 中使用 NUMBER 而不是 BIGINT
CREATE TABLE SYSTEM_ROLE (
    ID NUMBER(20) NOT NULL,
    NAME VARCHAR2(30) NOT NULL,
    STATUS NUMBER(3) DEFAULT 1,
    CREATE_TIME DATE DEFAULT SYSDATE,
    CONSTRAINT PK_SYSTEM_ROLE PRIMARY KEY (ID)
);

-- Oracle 中序列代替 AUTO_INCREMENT
CREATE SEQUENCE SYSTEM_ROLE_SEQ START WITH 1 INCREMENT BY 1;
-- 配合 MyBatis Plus 的 @KeySequence("system_role_seq") 使用
```

**解读**：
- **类型差异**：Oracle 没有 `BIGINT`，用 `NUMBER(20)` 替代
- **自增差异**：Oracle 没有 `AUTO_INCREMENT`，需要「序列 + 触发器」或 MyBatis Plus 的 `KeySequence`
- **字符集差异**：Oracle 用 `VARCHAR2` 代替 `VARCHAR`
- **时间函数差异**：`SYSDATE` 代替 `CURRENT_TIMESTAMP`
- **设计意图**：通过分目录 + 同样的 DDL 结构，让运维可以快速切换数据库

## 4. 关键要点总结

- ruoyi 通过「每种数据库一个 SQL 目录」实现多数据库适配
- MySQL 是最常用的开发数据库，脚本最完善
- Quartz 调度表是 ruoyi 定时任务的基础
- 每个表的 `creator/create_time/updater/update_time/deleted/tenant_id` 是 ruoyi 的标准字段

## 5. 练习题

### 练习 1：基础（必做）

本地初始化 ruoyi 数据库：执行 `mysql/ruoyi-vue-pro.sql` 和 `quartz.sql`，列出所有以 `system_` 开头的业务表（应该有 20+ 张）。

### 练习 2：进阶

对比 `sql/mysql/ruoyi-vue-pro.sql` 和 `sql/postgresql/` 中的同名表（如 `system_role`），列出至少 3 处类型/语法差异。

### 练习 3：挑战（选做）

为 ruoyi 设计「数据字典表 system_dict」（含 dict_type、dict_label、dict_value、sort 字段），写出 DDL，并插入 5 条用户状态字典数据（0=启用、1=停用...）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/sql/mysql/ruoyi-vue-pro.sql`
- `/Users/xu/code/github/ruoyi-vue-pro/sql/mysql/quartz.sql`
- Quartz 调度文档：https://www.quartz-scheduler.org/documentation/

---

**文档版本**：v1.0
**最后更新**：2026-07-13