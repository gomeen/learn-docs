# 2.6 多租户（tenant）SQL 拦截器

> 深入理解 yudao 多租户的实现原理，能配置自己的多租户字段。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 yudao 多租户的完整架构（Web → AOP → DB → MQ）
- 掌握 `TenantLineInnerInterceptor` 的工作原理
- 理解 `TenantBaseDO` 与普通 `BaseDO` 的区别
- 能在自己的业务表中启用多租户

## 📚 前置知识

- [12-data-permission.md](./12-data-permission.md)
- MyBatis Plus 多租户插件
- SaaS 多租户架构基础（详见 [多租户](../../_common/08-authorization/05-multi-tenant.md)；应用 API 见 [33-tenant](./40-tenant.md)）

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

## 3. 关键要点总结

- **多租户 = TenantContextHolder + TenantLineInnerInterceptor + TenantBaseDO**
- **租户 ID 来源**：URL Header / LoginUser / 系统配置
- **JsqlParser 自动改写** SQL 追加 `tenant_id = ?`
- **必须加在分页拦截器前**（MP 限制）
- **共享表用 `@TenantIgnore` 排除**

---

**文档版本**：v1.0
**最后更新**：2026-07-13
