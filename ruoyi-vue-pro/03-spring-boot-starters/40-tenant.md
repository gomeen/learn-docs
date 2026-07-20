# 6.2 多租户：TenantContext / @TenantIgnore

> 深入理解 yudao 多租户的实现，能为业务添加多租户能力。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 yudao 多租户的核心 API
- 理解 `@TenantIgnore` 的使用场景
- 能用 `TenantContextHolder` 在代码中获取/设置租户
- 了解多租户在 MQ/缓存中的传播

## 📚 前置知识

- [13-tenant-interceptor.md](./13-tenant-interceptor.md)
- SaaS 多租户架构（详见 [多租户](../../_common/08-authorization/05-multi-tenant.md)）

## 1. 核心概念

### 1.1 多租户 API 速查

| API | 作用 |
|------|------|
| `TenantContextHolder.getTenantId()` | 拿当前租户 ID |
| `TenantContextHolder.getRequiredTenantId()` | 必须有租户，否则抛异常 |
| `TenantContextHolder.setTenantId(id)` | 设置租户 |
| `TenantContextHolder.setIgnore(true)` | 临时忽略租户 |
| `@TenantIgnore` | 方法/类级忽略 |
| `TenantBaseDO` | 实体基类（带 tenant_id） |

## 2. 代码示例

### 2.1 获取当前租户

```java
@Service
public class OrderServiceImpl {
    public void createOrder(OrderCreateReq req) {
        // 拿到当前租户
        Long tenantId = TenantContextHolder.getRequiredTenantId();
        OrderDO order = new OrderDO();
        order.setTenantId(tenantId);  // 自动设置（也可不写，BaseDO 自动填充）
        // ...
    }
}
```

### 2.2 临时忽略租户

```java
public void exportAll() {
    TenantContextHolder.setIgnore(true);
    try {
        return orderMapper.selectList();  // 不会加 tenant_id 过滤
    } finally {
        TenantContextHolder.setIgnore(false);
    }
}
```

### 2.3 @TenantIgnore 注解

```java
@Service
public class SysConfigServiceImpl {
    @TenantIgnore  // 字典表不需要租户隔离
    public List<SysConfigDO> getAllConfigs() {
        return configMapper.selectList();
    }
}
```

## 3. 关键要点总结

- **`TenantContextHolder`** 是多租户 API 入口
- **`@TenantIgnore`** 用于不需要租户隔离的方法
- **Web Filter** 从 Header 拿租户 ID
- **缓存 / MQ 自动加租户前缀** 隔离
- **TTL ThreadLocal**支持线程池

---

**文档版本**：v1.0
**最后更新**：2026-07-13
