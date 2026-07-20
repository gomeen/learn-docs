# 1.2 数据源配置

> 学习代码生成器如何连接不同的业务数据库，理解多数据源架构。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 ruoyi 数据源管理的核心表 `infra_data_source_config`
- 理解 `DatabaseTableService` 如何从任意数据源读取表结构
- 在自己项目中扩展一个新的数据源类型
- 区分"框架数据源"与"业务数据源"

## 📚 前置知识

- JDBC 基础
- Spring Boot 多数据源（`HikariDataSource`）
- 代码生成总览（详见 [总览](./01-overview.md)）

## 1. 核心概念

### 1.1 为什么需要数据源管理？

代码生成器要扫描**任意业务库**的表结构，而不是系统库（默认 `ruoyi-vue-pro`）。所以需要一个**数据源注册表**，让用户能"在线添加 MySQL/Oracle/PG 连接"。

### 1.2 核心实体：`DataSourceConfigDO`

```sql
CREATE TABLE infra_data_source_config (
    id           BIGINT PRIMARY KEY,
    name         VARCHAR(100),   -- 连接名（如 "订单库"）
    url          VARCHAR(500),   -- JDBC URL
    username     VARCHAR(100),
    password     VARCHAR(200),   -- 加密存储
    create_time  DATETIME,
    update_time  DATETIME,
    creator      VARCHAR(64),
    updater      VARCHAR(64),
    remark       VARCHAR(500)
);
```

### 1.3 数据源获取流程

```mermaid
graph LR
    A[用户在前端选数据源] --> B[Controller 接收 dataSourceConfigId]
    B --> C[DataSourceConfigService<br/>根据 ID 查 URL/账号/密码]
    C --> D[JdbcUtils 临时创建<br/>HikariDataSource]
    D --> E[DatabaseTableService<br/>用 JDBC 查 information_schema]
    E --> F[返回表/字段信息]
```

## 2. 代码示例

### 2.1 添加一个 MySQL 数据源（前端表单）

```json
{
  "name": "订单库（测试）",
  "url": "jdbc:mysql://127.0.0.1:3306/order_db?useSSL=false",
  "username": "root",
  "password": "123456"
}
```

### 2.2 通过 ID 获取数据源配置

```java
// 由 DataSourceConfigServiceImpl 实现
public DataSourceConfigDO getDataSourceConfig(Long id) {
    return dataSourceConfigMapper.selectById(id);
}
```

## 3. 关键要点总结

- 数据源信息存在 `infra_data_source_config` 表中，运行时**按需创建连接**
- 不使用连接池，直接用 `DriverManager.getConnection` 临时连接
- 不同的数据库（MySQL/Oracle/PG/...）需要**不同的 SQL** 查询 `information_schema`
- 所有数据库差异在 `DatabaseTableService` 内部被消化，对外统一返回 `TableInfo`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
