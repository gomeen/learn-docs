# 04 - 数据库与 MyBatis Plus

> ruoyi-vue-pro 使用 MyBatis Plus（不是 MyBatis），是 Java 生态最流行的 ORM 增强工具。

> **学习顺序**：按下方清单**从上到下**进行——读完一组文档后立刻做紧随其后的「✅ 小验证」，再继续下一组。练习已穿插在路径中间，不要把文档全部读完再回头找练习。

## 模块 4.1 SQL 与 MySQL 基础

- [ ] [1.1 MySQL 基础：CRUD / JOIN / 索引](./01-mysql-basics.md)
- [ ] [1.2 MySQL 事务与隔离级别](./02-mysql-transaction.md)
- [ ] [1.3 MySQL 索引原理与优化](./03-mysql-index.md)
- [ ] [1.4 MySQL 慢查询分析](./04-mysql-slow-query.md)
- [ ] [1.5 数据库设计：三大范式](./05-normalization.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [06-*-mysql-basics: MySQL 基础与设计](./06-*-mysql-basics.md)
  - 覆盖：01-mysql-basics.md, 02-mysql-transaction.md, 03-mysql-index.md, 04-mysql-slow-query.md, 05-normalization.md


## 模块 4.2 数据库迁移与代码生成

- [ ] [2.1 ruoyi 的 SQL 初始化脚本](./07-sql-scripts.md)
- [ ] [2.2 Flyway / Liquibase 数据库迁移](./08-flyway.md)
- [ ] [2.3 ruoyi 代码生成器生成 SQL](./09-gen-sql.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [10-*-sql-migration: SQL 脚本 / 迁移 / 代码生成 SQL](./10-*-sql-migration.md)
  - 覆盖：07-sql-scripts.md, 08-flyway.md, 09-gen-sql.md


## 模块 4.3 MyBatis Plus 核心

- [ ] [3.1 MyBatis 与 MyBatis Plus 区别](./11-mybatis-vs-mp.md)
- [ ] [3.2 BaseMapper 通用 CRUD](./12-base-mapper.md)
- [ ] [3.3 IService 与 ServiceImpl](./13-service-impl.md)
- [ ] [3.4 条件构造器：QueryWrapper / LambdaQueryWrapper](./14-query-wrapper.md)
- [ ] [3.5 分页查询：Page / PaginationInnerInterceptor](./15-mp-pagination.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [16-*-mybatis-plus: MyBatis Plus 基础 CRUD 与条件构造](./16-*-mybatis-plus.md)
  - 覆盖：11-mybatis-vs-mp.md, 12-base-mapper.md, 13-service-impl.md, 14-query-wrapper.md, 15-mp-pagination.md

- [ ] [3.6 自动填充：MetaObjectHandler](./17-auto-fill.md)
- [ ] [3.7 逻辑删除：@TableLogic](./18-logic-delete.md)
- [ ] [3.8 乐观锁：@Version](./19-optimistic-lock.md)
- [ ] [3.9 关联查询：@One / @Many](./20-relation.md)
- [ ] [3.10 自定义 SQL：@Select / @Update](./21-custom-sql.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [22-*-mp-advanced: 自动填充 / 逻辑删除 / 乐观锁 / 自定义 SQL](./22-*-mp-advanced.md)
  - 覆盖：17-auto-fill.md, 18-logic-delete.md, 19-optimistic-lock.md, 20-relation.md, 21-custom-sql.md


## 模块 4.4 多数据源

- [ ] [4.1 dynamic-datasource 多数据源](./23-dynamic-datasource.md)
- [ ] [4.2 @DS 切换数据源](./24-ds-annotation.md)
- [ ] [4.3 ruoyi 的多数据源实战](./25-ruoyi-multi-ds.md)

## 模块 4.5 数据库连接池

- [ ] [5.1 Druid 连接池](./26-druid.md)
- [ ] [5.2 HikariCP 连接池](./27-hikari.md)
- [ ] [5.3 ruoyi 的 Druid 配置](./28-ruoyi-druid.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [29-*-multi-ds-pool: 多数据源与连接池](./29-*-multi-ds-pool.md)
  - 覆盖：23-dynamic-datasource.md, 24-ds-annotation.md, 25-ruoyi-multi-ds.md, 26-druid.md, 27-hikari.md, 28-ruoyi-druid.md


## 🎯 ruoyi-vue-pro 仓库对应位置

- SQL 脚本：`/Users/xu/code/github/ruoyi-vue-pro/sql/`
- 数据源配置：`yudao-spring-boot-starter-mybatis/`
- DAO 层：`yudao-module-system/src/main/java/.../dal/`
- DO 实体：`yudao-module-system/src/main/java/.../dal/dataobject/`
