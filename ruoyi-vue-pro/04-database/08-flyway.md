# 07 Flyway / Liquibase 数据库迁移

> 数据库结构需要版本化管理。ruoyi 当前不强制使用 Flyway，但生产项目推荐引入。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解数据库迁移工具的作用
- 掌握 Flyway 的基本使用方法
- 知道 Liquibase 与 Flyway 的差异
- 评估是否在 ruoyi 中启用 Flyway

## 📚 前置知识

- [01-mysql-basics.md](./01-mysql-basics.md)
- Maven 基础（详见 [11-maven-modules](../01-java-fundamentals/13-maven-modules.md) / [13-maven-lifecycle](../01-java-fundamentals/15-maven-lifecycle.md)）

## 1. 核心概念

### 1.1 什么是数据库迁移？

```
传统方式：手动执行 SQL → 容易遗漏 → 团队协作困难

数据库迁移：将数据库变更脚本化、版本化、可重复执行
```

### 1.2 Flyway vs Liquibase

| 维度 | Flyway | Liquibase |
|------|--------|-----------|
| 配置文件 | SQL 脚本（原生 SQL） | XML/YAML/JSON（抽象描述） |
| 学习曲线 | 低（懂 SQL 即可） | 中（需学 XML 语法） |
| 回滚 | 需付费版 | 免费支持 |
| 社区 | MyBatis Plus 默认推荐 | Spring Boot 默认推荐 |
| 适用场景 | SQL 简单、直接 | 复杂变更、多数据库 |

### 1.3 Flyway 工作原理

```
应用启动 →
  Flyway 检查 flyway_schema_history 表 →
    扫描 classpath:db/migration/*.sql →
      对比版本号 → 执行新版本脚本 →
        更新历史表
```

## 2. 代码示例

### 2.1 Flyway 集成 Spring Boot

```xml
<!-- pom.xml -->
<dependency>
    <groupId>org.flywaydb</groupId>
    <artifactId>flyway-core</artifactId>
</dependency>

<!-- MySQL 8.x 还需要 -->
<dependency>
    <groupId>org.flywaydb</groupId>
    <artifactId>flyway-mysql</artifactId>
</dependency>
```

### 2.2 Flyway 配置文件

```yaml
# application.yml
spring:
  flyway:
    enabled: true                   # 启用 Flyway
    locations: classpath:db/migration  # 脚本位置
    baseline-on-migrate: true       # 已有数据库也能用
    table: flyway_schema_history    # 历史表名
    validate-on-migrate: true       # 启动时校验
```

### 2.3 Flyway 脚本规范

```
src/main/resources/db/migration/
├── V1.0.0__init_tables.sql        # 版本 1.0.0：初始化
├── V1.0.1__add_user_email.sql     # 版本 1.0.1：新增字段
├── V1.1.0__add_index.sql          # 版本 1.1.0：新增索引
└── V2.0.0__create_order_table.sql # 版本 2.0.0：创建订单表
```

**命名规则**：`V<版本号>__<描述>.sql`，双下划线分隔。

### 2.4 SQL 脚本示例

```sql
-- V1.0.1__add_user_email.sql
ALTER TABLE system_user ADD COLUMN email VARCHAR(50) DEFAULT '';

-- 创建索引
CREATE INDEX idx_email ON system_user(email);
```

## 3. 关键要点总结

- Flyway 让数据库变更可追溯、可重复执行
- 推荐使用 **Flyway**（MyBatis Plus 生态友好）
- 脚本命名：`V<版本>__<描述>.sql`
- 已有数据库需开启 `baseline-on-migrate: true`
- ruoyi 当前未内置 Flyway，但生产建议补充

---

**文档版本**：v1.0
**最后更新**：2026-07-13
