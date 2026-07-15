# 2.6 多租户（tenant）SQL 拦截器

> 深入理解 yudao 多租户的实现原理，能配置自己的多租户字段。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 yudao 多租户的完整架构（Web → AOP → DB → MQ）
- 掌握 `TenantLineInnerInterceptor` 的工作原理
- 理解 `TenantBaseDO` 与普通 `BaseDO` 的区别
- 能在自己的业务表中启用多租户

## 📚 前置知识

- [10-data-permission.md](./10-data-permission.md)
- MyBatis Plus 多租户插件
- SaaS 多租户架构基础（详见 [多租户](../../_common/08-authorization/05-multi-tenant.md)；应用 API 见 [33-tenant](./33-tenant.md)）

## 1. 核心概念

### 1.1 什么是多租户（Multi-Tenancy）？

**多租户** 是 SaaS 应用的常见架构：多个客户（租户）共用同一套代码库和数据库，但**数据严格隔离**。常见方案：

| 方案 | 数据隔离 | 成本 |
|------|---------|------|
| 独立数据库 | 物理隔离 | 高 |
| 独立 Schema | 数据库级隔离 | 中 |
| 共享数据库 + tenant_id 字段 | 逻辑隔离（**yudao 采用**） | 低 |

### 1.2 yudao 的多租户组件

| 组件 | 职责 |
|------|------|
| `TenantContextHolder` | ThreadLocal 存储当前租户 |
| `TenantContextWebFilter` | Web Filter 设置租户 ID |
| `TenantLineInnerInterceptor` | MyBatis 拦截器，SQL 加 `tenant_id` |
| `TenantIgnore` 注解 | 标记不参与多租户 |
| `TenantBaseDO` | 业务实体继承，自动带 `tenant_id` |
| `TenantProperties` | 配置（忽略的表/缓存） |
| `TenantRedisMessageInterceptor` | Redis MQ 传递租户 |

## 2. 代码示例

### 2.1 业务实体启用多租户

```java
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("sys_order")
public class OrderDO extends TenantBaseDO {  // 注意是 TenantBaseDO 不是 BaseDO
    private Long orderNo;
    private BigDecimal amount;
}
```

### 2.2 临时关闭多租户

```java
@DataPermission(enable = false)
@TenantIgnore  // 同时关闭租户过滤
public class OrderServiceImpl {
    public List<OrderDO> exportAll() {
        return orderMapper.selectList();
    }
}
```

### 2.3 配置 application.yml

```yaml
yudao:
  tenant:
    enable: true
    ignore-tables:
      - sys_config       # 配置表不过滤
      - sys_dict_data
    ignore-caches:
      - dict             # 缓存不过滤
```

## 3. ruoyi 仓库源码解读

### 3.1 TenantDatabaseInterceptor

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/db/TenantDatabaseInterceptor.java`
**核心代码**（行 40-80）：

```java
@Override
public Expression getTenantId() {
    return new LongValue(TenantContextHolder.getRequiredTenantId());
}

@Override
public boolean ignoreTable(String tableName) {
    // 情况一：全局忽略（TenantContextHolder.isIgnore() = true）
    if (TenantContextHolder.isIgnore()) {
        return true;
    }
    // 情况二：查询配置 + 计算
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
    // 找不到表说明不是 yudao 项目的表，不过滤
    TableInfo tableInfo = TableInfoHelper.getTableInfo(tableName);
    if (tableInfo == null) return true;
    // 继承 TenantBaseDO 的表必须过滤
    if (TenantBaseDO.class.isAssignableFrom(tableInfo.getEntityType())) {
        return false;
    }
    // 标注 @TenantIgnore 的表不过滤
    TenantIgnore tenantIgnore = tableInfo.getEntityType().getAnnotation(TenantIgnore.class);
    return tenantIgnore != null;
}
```

**解读**：
- 实现 MP 的 `TenantLineHandler` 接口
- `getTenantId()` 返回当前线程的 tenantId
- `ignoreTable()` 通过三步判断：全局开关 → 配置表 → 实体类（继承 TenantBaseDO 或 @TenantIgnore）
- 用了**缓存**（`ignoreTables`）避免重复计算

### 3.2 TenantLineInnerInterceptor 注册

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/config/YudaoTenantAutoConfiguration.java`
**核心代码**（行 78-85）：

```java
@Bean
public TenantLineInnerInterceptor tenantLineInnerInterceptor(TenantProperties properties,
                                                             MybatisPlusInterceptor interceptor) {
    TenantLineInnerInterceptor inner = new TenantLineInnerInterceptor(new TenantDatabaseInterceptor(properties));
    // 添加到 interceptor 中
    // 需要加在首个，主要是为了在分页插件前面。这个是 MyBatis Plus 的规定
    MyBatisUtils.addInterceptor(interceptor, inner, 0);
    return inner;
}
```

**解读**：
- **必须加在拦截器链的第 0 位**（在分页插件前）——MyBatis Plus 的规定
- 这样分页的 COUNT 也会带上 `tenant_id` 过滤

### 3.3 TenantContextHolder

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/context/TenantContextHolder.java`
**核心代码**（节选）：

```java
public class TenantContextHolder {
    private static final ThreadLocal<Long> TENANT_ID = TransmittableThreadLocal.withInitial(() -> 0L);
    private static final ThreadLocal<Boolean> IGNORE = new ThreadLocal<>();

    public static void setTenantId(Long tenantId) { TENANT_ID.set(tenantId); }
    public static Long getTenantId() { return TENANT_ID.get(); }
    public static Long getRequiredTenantId() {
        Long tenantId = TENANT_ID.get();
        if (tenantId == null || tenantId == 0L) {
            throw new IllegalStateException("租户 ID 未设置");
        }
        return tenantId;
    }
    public static boolean isIgnore() {
        Boolean ignore = IGNORE.get();
        return ignore != null && ignore;
    }
}
```

**解读**：
- 使用 `TransmittableThreadLocal` 支持线程池
- `getRequiredTenantId()` 没设置租户就抛异常（**严格模式**）
- `isIgnore()` 用于临时关闭租户（如 `TenantIgnore`）

## 4. 关键要点总结

- **多租户 = TenantContextHolder + TenantLineInnerInterceptor + TenantBaseDO**
- **租户 ID 来源**：URL Header / LoginUser / 系统配置
- **JsqlParser 自动改写** SQL 追加 `tenant_id = ?`
- **必须加在分页拦截器前**（MP 限制）
- **共享表用 `@TenantIgnore` 排除**

## 5. 练习题

### 练习 1：基础（必做）

阅读 `TenantContextWebFilter` 源码，理解租户 ID 如何从 HTTP Header 传递到 ThreadLocal。

### 练习 2：进阶

为业务表 `OrderDO` 启用多租户（继承 `TenantBaseDO`），并验证：传入不同租户的请求只能看到自己租户的订单。

### 练习 3：挑战（选做）

实现"超级租户"：某个特殊租户可以查看所有租户的数据（紧急运维用）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/db/TenantDatabaseInterceptor.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/config/YudaoTenantAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/context/TenantContextHolder.java`
- MyBatis-Plus 多租户文档：https://baomidou.com/pages/ea3a8d/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
