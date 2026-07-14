# 04 - 数据库与 MyBatis Plus

> ruoyi-vue-pro 使用 MyBatis Plus（不是 MyBatis），是 Java 生态最流行的 ORM 增强工具。

## 模块 4.1 SQL 与 MySQL 基础

- [ ] [1.1 MySQL 基础：CRUD / JOIN / 索引](./01-mysql-basics.md)
- [ ] [1.2 MySQL 事务与隔离级别](./02-mysql-transaction.md)
- [ ] [1.3 MySQL 索引原理与优化](./03-mysql-index.md)
- [ ] [1.4 MySQL 慢查询分析](./04-mysql-slow-query.md)
- [ ] [1.5 数据库设计：三大范式](./05-normalization.md)

## 模块 4.2 数据库迁移与代码生成

- [ ] [2.1 ruoyi 的 SQL 初始化脚本](./06-sql-scripts.md)
- [ ] [2.2 Flyway / Liquibase 数据库迁移](./07-flyway.md)
- [ ] [2.3 ruoyi 代码生成器生成 SQL](./08-gen-sql.md)

## 模块 4.3 MyBatis Plus 核心

- [ ] [3.1 MyBatis 与 MyBatis Plus 区别](./09-mybatis-vs-mp.md)
- [ ] [3.2 BaseMapper 通用 CRUD](./10-base-mapper.md)
- [ ] [3.3 IService 与 ServiceImpl](./11-service-impl.md)
- [ ] [3.4 条件构造器：QueryWrapper / LambdaQueryWrapper](./12-query-wrapper.md)
- [ ] [3.5 分页查询：Page / PaginationInnerInterceptor](./13-mp-pagination.md)
- [ ] [3.6 自动填充：MetaObjectHandler](./14-auto-fill.md)
- [ ] [3.7 逻辑删除：@TableLogic](./15-logic-delete.md)
- [ ] [3.8 乐观锁：@Version](./16-optimistic-lock.md)
- [ ] [3.9 关联查询：@One / @Many](./17-relation.md)
- [ ] [3.10 自定义 SQL：@Select / @Update](./18-custom-sql.md)

## 模块 4.4 多数据源

- [ ] [4.1 dynamic-datasource 多数据源](./19-dynamic-datasource.md)
- [ ] [4.2 @DS 切换数据源](./20-ds-annotation.md)
- [ ] [4.3 ruoyi 的多数据源实战](./21-ruoyi-multi-ds.md)

## 模块 4.5 数据库连接池

- [ ] [5.1 Druid 连接池](./22-druid.md)
- [ ] [5.2 HikariCP 连接池](./23-hikari.md)
- [ ] [5.3 ruoyi 的 Druid 配置](./24-ruoyi-druid.md)

## 🎯 ruoyi-vue-pro 仓库对应位置

- SQL 脚本：`/Users/xu/code/github/ruoyi-vue-pro/sql/`
- 数据源配置：`yudao-spring-boot-starter-mybatis/`
- DAO 层：`yudao-module-system/src/main/java/.../dal/`
- DO 实体：`yudao-module-system/src/main/java/.../dal/dataobject/`
