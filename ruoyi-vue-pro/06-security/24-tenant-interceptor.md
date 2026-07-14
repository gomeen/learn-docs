# 24 SQL 拦截器：自动加 tenant_id

> 详解 `TenantDatabaseInterceptor` 的实现：MyBatis-Plus TenantLineInnerInterceptor + JSqlParser。

## 🎯 学习目标

完成本文档后，你将能够：
- 深入理解 MyBatis-Plus 多租户插件的原理
- 掌握 JSqlParser 解析 SQL 的能力
- 能为新表接入多租户
- 知道"忽略多租户"的三种方式

## 📚 前置知识

- 21-multi-tenant.md
- 22-ruoyi-tenant.md
- 23-tenant-context.md
- MyBatis 拦截器机制

## 1. 核心概念

### 1.1 MyBatis-Plus 的多租户插件

```
MybatisPlusInterceptor
    └─ TenantLineInnerInterceptor  // 多租户拦截器
        └─ TenantLineHandler       // 业务实现
            ├─ getTenantId()       // 返回当前租户 ID
            └─ ignoreTable()       // 判断表是否忽略
```

### 1.2 拦截器工作流程

```
MyBatis 执行原始 SQL：SELECT * FROM system_user
    ↓
TenantLineInnerInterceptor 拦截
    ↓
JSqlParser 解析 SQL（解析成 AST 抽象语法树）
    ↓
获取 SQL 中涉及的表名
    ↓
对每个表判断是否需要加 tenant_id
    ├─ 继承 TenantBaseDO → 加
    ├─ 加了 @TenantIgnore → 不加
    └─ 全局 IGNORE=true → 不加
    ↓
如果是"要加"的表，在 WHERE 中加 "tenant_id = ?"
    ↓
JSqlParser 重新生成 SQL
    ↓
执行：SELECT * FROM system_user WHERE tenant_id = 1
```

### 1.3 性能影响

每次 SQL 执行都要：
- JSqlParser 解析 AST
- 检查表名、列名
- 重组 SQL

**开销大约 1-5ms/查询**（取决于 SQL 复杂度）。对于高并发场景需要考虑。

## 2. 代码示例

### 2.1 手动配置（不通过 Spring Boot）

```java
// 文件：MybatisConfig.java
@Configuration
public class MybatisConfig {

    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();

        // 多租户拦截器
        TenantLineInnerInterceptor tenantInterceptor = new TenantLineInnerInterceptor();
        tenantInterceptor.setTenantLineHandler(new TenantLineHandler() {
            @Override
            public Expression getTenantId() {
                return new LongValue(TenantContextHolder.getTenantId());
            }

            @Override
            public boolean ignoreTable(String tableName) {
                return "system_dict".equalsIgnoreCase(tableName);  // 字典表不需要租户
            }
        });
        interceptor.addInnerInterceptor(tenantInterceptor);

        return interceptor;
    }
}
```

### 2.2 全局忽略多租户

```java
// 场景：定时任务清理所有租户的数据
@TenantIgnore
public void cleanAllTenants() {
    // SQL 不加 tenant_id
    orderMapper.delete(null);
}

// 场景：系统级别的数据迁移
TenantUtils.executeIgnore(() -> {
    orderMapper.delete(null);
});
```

## 3. ruoyi 仓库源码解读

### 3.1 TenantDatabaseInterceptor 完整实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/db/TenantDatabaseInterceptor.java`
**核心代码**（行 21-83）：

```java
public class TenantDatabaseInterceptor implements TenantLineHandler {

    /**
     * 忽略的表（KEY：表名，VALUE：是否忽略）
     */
    private final Map<String, Boolean> ignoreTables = new HashMap<>();

    public TenantDatabaseInterceptor(TenantProperties properties) {
        // 1. 配置中的忽略表
        properties.getIgnoreTables().forEach(table -> {
            addIgnoreTable(table, true);
        });
        // 2. Oracle 主键生成器查询的表，忽略
        addIgnoreTable("DUAL", true);
    }

    @Override
    public Expression getTenantId() {
        // 关键：从 ThreadLocal 拿当前租户 ID
        return new LongValue(TenantContextHolder.getRequiredTenantId());
    }

    @Override
    public boolean ignoreTable(String tableName) {
        // 情况一：全局忽略多租户
        if (TenantContextHolder.isIgnore()) {
            return true;
        }
        // 情况二：指定的表忽略
        tableName = SqlParserUtils.removeWrapperSymbol(tableName);
        Boolean ignore = ignoreTables.get(tableName.toLowerCase());
        if (ignore == null) {
            ignore = computeIgnoreTable(tableName);
            synchronized (ignoreTables) {
                addIgnoreTable(tableName, ignore);
            }
        }
        return ignore;
    }

    private void addIgnoreTable(String tableName, boolean ignore) {
        ignoreTables.put(tableName.toLowerCase(), ignore);
        ignoreTables.put(tableName.toUpperCase(), ignore);
    }

    private boolean computeIgnoreTable(String tableName) {
        // 1. 找不到的表，说明不是 yudao 项目里的，不拦截
        TableInfo tableInfo = TableInfoHelper.getTableInfo(tableName);
        if (tableInfo == null) {
            return true;
        }
        // 2. 继承了 TenantBaseDO 显然不忽略（要加 tenant_id）
        if (TenantBaseDO.class.isAssignableFrom(tableInfo.getEntityType())) {
            return false;
        }
        // 3. 添加了 @TenantIgnore 注解，忽略
        TenantIgnore tenantIgnore = tableInfo.getEntityType().getAnnotation(TenantIgnore.class);
        return tenantIgnore != null;
    }
}
```

**逐行解读**：

- **第 26-38 行：构造函数**
  - 第 33-35 行：加载 `TenantProperties.getIgnoreTables()` 中配置的表
  - 第 37 行：Oracle `DUAL` 表（主键生成器会查它，必须忽略）

- **第 40-43 行 `getTenantId()`**
  - `TenantContextHolder.getRequiredTenantId()`：从 ThreadLocal 拿租户 ID，不存在就抛 NPE
  - 包成 `LongValue`（JSqlParser 的 AST 节点）

- **第 45-61 行 `ignoreTable()`**
  - 第 47-50 行：**全局忽略** — `TenantContextHolder.isIgnore()` 为 true 时所有表都跳过
  - 第 52 行 `removeWrapperSymbol`：去除 SQL 中的引号（不同 DB 引号风格不同）
  - 第 54-60 行：缓存机制 — 第一次查询表信息后缓存到 `ignoreTables`，避免每次查

- **第 68-82 行 `computeIgnoreTable()`**（核心决策）
  - 第 70-73 行：`TableInfoHelper` 是 MyBatis-Plus 的 API，能拿到实体类
  - 第 74-77 行：继承了 `TenantBaseDO` 就不忽略（**关键约定**）
  - 第 79-80 行：加了 `@TenantIgnore` 注解就忽略

### 3.2 TenantBaseDO（约定基类）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/db/TenantBaseDO.java`
**核心代码**（行 12-21）：

```java
@Data
@EqualsAndHashCode(callSuper = true)
public abstract class TenantBaseDO extends BaseDO {

    /**
     * 多租户编号
     */
    private Long tenantId;
}
```

**解读**：
- 业务实体**继承**这个基类，自动启用租户隔离
- `tenantId` 字段自动加入 INSERT 的 values
- ruoyi 的约定：**所有租户相关的表必须继承 TenantBaseDO**

### 3.3 拦截器装配

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/config/YudaoTenantAutoConfiguration.java`

```java
@Bean
public TenantDatabaseInterceptor tenantDatabaseInterceptor(TenantProperties properties) {
    return new TenantDatabaseInterceptor(properties);
}

@Bean
public MybatisPlusInterceptor mybatisPlusInterceptor(TenantDatabaseInterceptor tenantInterceptor) {
    MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
    interceptor.addInnerInterceptor(new TenantLineInnerInterceptor(tenantInterceptor));
    return interceptor;
}
```

**解读**：
- 创建 `TenantDatabaseInterceptor` 实例
- 包装成 MyBatis-Plus 的 `TenantLineInnerInterceptor`
- 添加到 `MybatisPlusInterceptor` 链中

## 4. 关键要点总结

- `TenantDatabaseInterceptor` 实现 `TenantLineHandler` 接口
- 用 JSqlParser 解析 SQL，根据 `ignoreTable()` 决定是否加 `tenant_id`
- 三种"加"的条件：继承 `TenantBaseDO` / 不在 IGNORE 模式 / 不在忽略表
- 三种"忽略"的方式：全局 IGNORE / 配置表名 / `@TenantIgnore` 注解
- 性能开销 1-5ms/查询（JSqlParser 解析）

## 5. 练习题

### 练习 1：基础（必做）

写一个 `OrderDO` 继承 `TenantBaseDO`，调用 `orderMapper.selectList()`，开启 MySQL 慢日志，查看实际执行的 SQL 是否带 `tenant_id`。

### 练习 2：进阶

实现一个自定义的 `ignoreTable()` 逻辑：表名以 `system_` 开头的就忽略，其他表都加 `tenant_id`。

### 练习 3：挑战（选做）

MyBatis-Plus 的多租户插件不支持 `UPDATE` 多表 `JOIN`、`DELETE` 关联子查询等复杂 SQL。如果 ruoyi 遇到这些 SQL 怎么办？（提示：搜索 `sqlParserCache`）

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/db/TenantDatabaseInterceptor.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/db/TenantBaseDO.java`
- MyBatis-Plus 多租户：https://baomidou.com/plugins/tenant/
- JSqlParser：https://github.com/JSQLParser/JSqlParser

---

**文档版本**：v1.0
**最后更新**：2026-07-13
