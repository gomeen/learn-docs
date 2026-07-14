# 21 多租户架构：SAAS 模式

> 详解多租户（Multi-Tenancy）架构的 3 种方案、独立数据库 vs 共享数据库。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解多租户（SAAS）的核心价值
- 掌握多租户的 3 种隔离方案：独立 DB / 共享 DB 独立 Schema / 共享 DB 共享 Schema
- 知道 ruoyi 用的是哪种方案
- 能为新业务设计多租户架构

## 📚 前置知识

- 数据库基础
- MyBatis-Plus

## 1. 核心概念

### 1.1 什么是多租户？

**单租户**：每个客户一套独立部署
- 成本高（每客户一台服务器）
- 升级慢（要一个个客户升级）
- 隔离好

**多租户（SAAS）**：多个客户共享一套部署
- 成本低（一台服务器服务 N 个客户）
- 升级快（一次升级所有客户生效）
- 隔离是关键挑战

### 1.2 三种多租户方案

| 方案 | 隔离级别 | 成本 | 适用场景 |
|------|---------|------|---------|
| 独立数据库 | 强 | 高 | 大客户、定制化要求高 |
| 共享数据库 + 独立 Schema | 中 | 中 | 中等规模 |
| 共享数据库 + 共享 Schema + tenant_id 字段 | 弱 | 低 | **ruoyi 用这种** |

### 1.3 ruoyi 的方案（共享 Schema）

```sql
-- 每个业务表加 tenant_id 字段
CREATE TABLE system_user (
    id BIGINT PRIMARY KEY,
    tenant_id BIGINT NOT NULL,  -- 关键：租户 ID
    username VARCHAR(50),
    -- ... 其他字段
    INDEX idx_tenant_id (tenant_id)
);

-- 同一个 system_user 表，存所有租户的用户
-- A 租户：tenant_id=1
-- B 租户：tenant_id=2
```

**好处**：
- 成本低（一台 DB 服务所有租户）
- 升级快（一次 DDL 影响所有租户）
- 缺点：需要严格的 SQL 拦截，否则容易数据泄露

## 2. 代码示例

### 2.1 手动加 tenant_id（不推荐）

```java
// ❌ 错误：每个 Service 都要手动加 tenant_id
public List<OrderDO> listOrders() {
    Long tenantId = TenantContextHolder.getTenantId();
    return orderMapper.selectList(
        new LambdaQueryWrapperX<OrderDO>()
            .eq(OrderDO::getTenantId, tenantId)  // 容易遗漏！
    );
}

// ✅ 正确：用 MyBatis 拦截器自动加（ruoyi 方式）
public List<OrderDO> listOrders() {
    // SQL 自动变成：SELECT * FROM orders WHERE tenant_id = ?
    return orderMapper.selectList();
}
```

## 3. ruoyi 仓库源码解读

### 3.1 TenantBaseDO 基类

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
- 继承 `TenantBaseDO` 的实体类，**自动启用租户隔离**
- 拦截器会自动在 SQL 中加 `tenant_id = ?` 条件
- 这是"约定优于配置"：业务表必须继承这个基类

### 3.2 TenantDatabaseInterceptor（核心拦截器）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/db/TenantDatabaseInterceptor.java`
**核心代码**（行 21-83）：

```java
public class TenantDatabaseInterceptor implements TenantLineHandler {

    /**
     * 忽略的表（KEY：表名，VALUE：是否忽略）
     */
    private final Map<String, Boolean> ignoreTables = new HashMap<>();

    public TenantDatabaseInterceptor(TenantProperties properties) {
        // 不同 DB 下，大小写的习惯不同，所以都添加进去
        properties.getIgnoreTables().forEach(table -> {
            addIgnoreTable(table, true);
        });
        // Oracle 主键生成器查询的表，忽略
        addIgnoreTable("DUAL", true);
    }

    @Override
    public Expression getTenantId() {
        // 关键：从 ThreadLocal 拿到当前租户 ID
        return new LongValue(TenantContextHolder.getRequiredTenantId());
    }

    @Override
    public boolean ignoreTable(String tableName) {
        // 情况一：全局忽略多租户（用 @TenantIgnore 开启）
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

    private boolean computeIgnoreTable(String tableName) {
        // 找不到的表（如 yudao 之外的表）不拦截
        TableInfo tableInfo = TableInfoHelper.getTableInfo(tableName);
        if (tableInfo == null) {
            return true;
        }
        // 继承了 TenantBaseDO 显然不忽略
        if (TenantBaseDO.class.isAssignableFrom(tableInfo.getEntityType())) {
            return false;
        }
        // 添加了 @TenantIgnore 注解，忽略
        TenantIgnore tenantIgnore = tableInfo.getEntityType().getAnnotation(TenantIgnore.class);
        return tenantIgnore != null;
    }
}
```

**解读**：
- 第 31-38 行：构造函数，加载配置 + Oracle `DUAL` 表
- 第 41-43 行 `getTenantId()`：从 `TenantContextHolder`（ThreadLocal）拿当前租户 ID
- 第 46-61 行 `ignoreTable()`：判断表是否需要加 `tenant_id` 条件
- 第 48-50 行：全局开关（`@TenantIgnore` 开启 `IGNORE` 模式时所有表都跳过）
- 第 68-82 行：动态判断 — 继承 `TenantBaseDO` 的表**不忽略**（要加 tenant_id），加了 `@TenantIgnore` 注解的表**忽略**

### 3.3 MyBatis-Plus 集成

`TenantDatabaseInterceptor` 是 MyBatis-Plus `TenantLineInnerInterceptor` 的 handler，配置位置：
```java
// yudao-framework/yudao-spring-boot-starter-biz-tenant/.../config/YudaoTenantAutoConfiguration.java
@Bean
public MybatisPlusInterceptor mybatisPlusInterceptor(TenantDatabaseInterceptor tenantInterceptor) {
    MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
    interceptor.addInnerInterceptor(new TenantLineInnerInterceptor(tenantInterceptor));
    return interceptor;
}
```

**完整链路**：
```
MyBatis 执行 SQL
    ↓
MybatisPlusInterceptor 拦截
    ↓
TenantLineInnerInterceptor 解析 SQL
    ↓
TenantDatabaseInterceptor.getTenantId() → ThreadLocal
    ↓
TenantDatabaseInterceptor.ignoreTable() → 判断是否需要加 tenant_id
    ↓
如果是：在 WHERE 条件前加 "tenant_id = ?"
    ↓
执行最终的 SQL
```

## 4. 关键要点总结

- 多租户有 3 种方案，ruoyi 用**共享 Schema + tenant_id** 方案
- `TenantBaseDO` 是"自动开启租户隔离"的标记基类
- `TenantDatabaseInterceptor` 通过 MyBatis 拦截器**自动加** `tenant_id` 条件
- 业务代码不需要手动加 `tenant_id`，由拦截器统一处理
- 三种忽略方式：全局开关（ThreadLocal）/ 指定表名 / 实体类 `@TenantIgnore`

## 5. 练习题

### 练习 1：基础（必做）

解释 ruoyi 为什么用"共享 Schema + tenant_id"方案，而不是"独立数据库"？两种方案各自的优缺点是什么？

### 练习 2：进阶

阅读 `TenantDatabaseInterceptor.ignoreTable()`，画出流程图说明：什么情况下表会被拦截、什么情况下不会。

### 练习 3：挑战（选做）

假设你是 SAAS 提供商，客户 A 要求把他的数据"物理隔离"（独立数据库）。如何在 ruoyi 基础上扩展"独立数据库"租户？

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/db/TenantBaseDO.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/db/TenantDatabaseInterceptor.java`
- MyBatis-Plus 多租户：https://baomidou.com/plugins/tenant/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
