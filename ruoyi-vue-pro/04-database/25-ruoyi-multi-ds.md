# 21 ruoyi 的多数据源实战

> ruoyi 通过 dynamic-datasource 实现「读写分离 + 多租户 + 多类型数据库」的完整方案。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ruoyi 多数据源架构设计
- 掌握数据源配置的动态扩展机制
- 知道密码加密存储的实现
- 了解多租户场景下的数据源切换

## 📚 前置知识

- [23-dynamic-datasource.md](./23-dynamic-datasource.md)
- [24-ds-annotation.md](./24-ds-annotation.md)
- 多租户见 [多租户](../../_common/08-authorization/05-multi-tenant.md)

## 1. 核心概念

### 1.1 ruoyi 多数据源的核心设计

```
┌────────────────┐
│  yml 配置（静态）│   ← 启动时加载
│  master / slave │
└────────┬───────┘
         │
┌────────▼────────────────┐
│ DataSourceConfigDO（动态）│   ← 运行时通过管理后台添加
│ infra_data_source_config  │
└────────┬─────────────────┘
         │
┌────────▼─────────────┐
│ DynamicDataSource   │   ← 整合
└────────┬─────────────┘
         │
┌────────▼─────────────┐
│  @DS 注解 / 拦截器   │   ← 使用
└──────────────────────┘
```

### 1.2 三大应用场景

1. **读写分离**：master 写、slave 读
2. **多租户**：不同租户路由到不同数据库（通过 tenantId 动态注册）
3. **多业务库**：订单库、用户库、商品库独立

### 1.3 关键设计决策

| 决策 | 实现 |
|------|------|
| 密码加密 | `EncryptTypeHandler` 加密字段 |
| 多数据库类型 | yml 中按需配置不同驱动 |
| 动态注册 | `infra_data_source_config` 表 + 启动加载 |
| 数据源切换 | `@DS` 注解（方法/类级） |
| 多数据源事务 | `@DSTransactional` 代替 `@Transactional` |

## 2. 代码示例

### 2.1 完整多数据源配置示例

```yaml
spring:
  datasource:
    dynamic:
      primary: master
      strict: false
      datasource:
        master:
          url: jdbc:mysql://127.0.0.1:3306/ruoyi?useSSL=false&serverTimezone=Asia/Shanghai
          username: root
          password: 123456
        slave:
          lazy: true  # 懒加载
          url: jdbc:mysql://127.0.0.1:3306/ruoyi-readonly?useSSL=false
          username: readonly
          password: 123456
        bi:  # 业务独立库
          url: jdbc:postgresql://127.0.0.1:5432/bi
          username: bi_user
          password: bi_pass
          driver-class-name: org.postgresql.Driver
```

### 2.2 动态数据源注册

```java
// 监听应用启动事件，加载 DB 中配置的数据源
@Component
public class DataSourceConfigInitializer implements ApplicationRunner {

    @Resource
    private DataSourceConfigService dataSourceConfigService;

    @Resource
    private DynamicDataSource dataSource;  // dynamic-datasource 核心类

    @Override
    public void run(ApplicationArguments args) {
        // 1. 查询 DB 中所有数据源配置
        List<DataSourceConfigDO> configs = dataSourceConfigService.getDataSourceConfigList();

        // 2. 逐个注册到动态数据源
        configs.forEach(config -> {
            DataSourceProperty property = new DataSourceProperty();
            BeanUtils.copyProperties(config, property);
            dataSource.addDataSource(config.getId().toString(), property);
        });
    }
}
```

### 2.3 多租户场景：根据 tenantId 动态选择数据源

```java
// 拦截器提取 tenantId → 切换数据源
@Component
public class TenantDataSourceInterceptor implements HandlerInterceptor {

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        String tenantId = request.getHeader("X-Tenant-Id");
        if (tenantId != null) {
            DynamicDataSourceContextHolder.push("tenant_" + tenantId);
        }
        return true;
    }
}
```

## 3. 关键要点总结

- ruoyi 多数据源 = dynamic-datasource + Druid + 多数据库支持
- yml 配置 + DB 配置混合：启动时静态 + 运行时动态
- 密码必须加密存储（`EncryptTypeHandler`）
- `@DSTransactional` 处理多数据源事务
- 多租户场景通过 `TenantBaseDO` + 拦截器实现

---

**文档版本**：v1.0
**最后更新**：2026-07-13
