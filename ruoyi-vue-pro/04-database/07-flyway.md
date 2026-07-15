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
- Maven 基础（详见 [11-maven-modules](../01-java-fundamentals/11-maven-modules.md) / [13-maven-lifecycle](../01-java-fundamentals/13-maven-lifecycle.md)）

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

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 当前不使用 Flyway 的原因

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/pom.xml`

```xml
<!-- yudao-spring-boot-starter-mybatis 的 pom.xml -->
<!-- 当前未引入 flyway-core 依赖 -->
<!-- 数据初始化由「代码生成器」+ 「SQL 脚本」组合完成 -->
```

**解读**：
- ruoyi 倾向于「代码生成器 + 一次性 SQL 脚本」的方案
- 优点：学习成本低，适合从 0 到 1 的项目
- 缺点：长期演进的项目缺少版本管理
- **官方建议**：生产环境推荐补充 Flyway 进行增量管理

### 3.2 ruoyi SQL 脚本组织方式（替代方案）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/sql/mysql/`

```
sql/mysql/
├── ruoyi-vue-pro.sql   # 完整初始化脚本
└── quartz.sql          # Quartz 调度表
```

**解读**：
- **一次性脚本**：整个项目一份 SQL，包含所有表结构 + 初始数据
- **初始数据示例**（节选自 `ruoyi-vue-pro.sql`）：
  ```sql
  -- 初始化-内置角色
  INSERT INTO system_role(id, name, code, sort, status, type, tenant_id)
  VALUES (1, '超级管理员', 'super_admin', 1, 0, 1, 0);
  ```
- **实践方式**：新部署直接执行完整脚本；老项目增量维护靠手动 SQL 文件夹管理

### 3.3 如果在 ruoyi 中启用 Flyway

**推荐目录结构**：

```
yudao-server/src/main/resources/db/migration/
├── V1.0.0__init_base_tables.sql      # 基础表（user/role/menu 等）
├── V1.0.1__init_business_tables.sql  # 业务表
├── V1.1.0__add_xxx_column.sql        # 后续增量变更
```

**配置示例**：

```yaml
spring:
  flyway:
    enabled: true
    locations: classpath:db/migration
    baseline-on-migrate: true   # 兼容已有数据库
```

## 4. 关键要点总结

- Flyway 让数据库变更可追溯、可重复执行
- 推荐使用 **Flyway**（MyBatis Plus 生态友好）
- 脚本命名：`V<版本>__<描述>.sql`
- 已有数据库需开启 `baseline-on-migrate: true`
- ruoyi 当前未内置 Flyway，但生产建议补充

## 5. 练习题

### 练习 1：基础（必做）

新建一个 Spring Boot 项目，集成 Flyway，编写 `V1.0.0__init.sql` 创建 `student(id, name, age)` 表，启动应用验证是否自动建表。

### 练习 2：进阶

在 ruoyi 的某个模块（如 yudao-module-system）添加 Flyway 依赖，并编写迁移脚本：给 `system_user` 表新增 `last_login_time` 字段。

### 练习 3：挑战（选做）

设计一个 Flyway 迁移管理规范文档（团队使用），要求：
1. 版本号命名规则
2. 脚本审核流程
3. 紧急修复（hotfix）脚本如何处理
4. 回滚方案

## 6. 参考资料

- Flyway 官方文档：https://flywaydb.org/documentation/
- Spring Boot Flyway 集成：https://docs.spring.io/spring-boot/docs/current/reference/html/howto.html#howto.data-initialization.migration-tool.flyway
- Liquibase 官方文档：https://docs.liquibase.com/

---

**文档版本**：v1.0
**最后更新**：2026-07-13