# 2.8 ruoyi 的 MyBatis 配置分析

> 全面分析 yudao MyBatis Starter 的配置项与扩展点。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 yudao MyBatis 的所有配置项
- 掌握 `application.yml` 中 MyBatis 相关配置
- 了解 yudao 对 MyBatis-Plus 的深度定制点
- 能根据业务需求调整 MyBatis 行为

## 📚 前置知识

- [07-mybatis-starter.md](./07-mybatis-starter.md)
- [10-pagination.md](./10-pagination.md)
- [12-data-permission.md](./12-data-permission.md)
- [13-tenant-interceptor.md](./13-tenant-interceptor.md)

## 1. 核心概念

### 1.1 yudao 对 MyBatis 的所有定制

| 定制点 | 实现 |
|--------|------|
| 自动填充 5 字段 | `DefaultDBFieldHandler` |
| 分页拦截器 | `PaginationInnerInterceptor` |
| 雪花 ID 生成器 | `IdTypeEnvironmentPostProcessor` |
| 增强的 Mapper | `BaseMapperX` |
| 增强的 Wrapper | `LambdaQueryWrapperX` |
| 自定义 TypeHandler | `EncryptTypeHandler` |
| 翻译组件 | `TranslateUtils` + `@Translate` |
| 多租户 | `TenantLineInnerInterceptor` |
| 数据权限 | `DataPermissionRuleHandler` |

### 1.2 yudao 的 MyBatis 配置结构

```yaml
mybatis-plus:
  global-config:
    db-config:
      id-type: AUTO                # 主键策略
      logic-delete-field: deleted  # 逻辑删除字段
      logic-delete-value: 1        # 已删除值
      logic-not-delete-value: 0    # 未删除值

mybatis:
  lazy-initialization: false       # Mapper 是否懒加载

yudao:
  info:
    base-package: com.ruoyi        # @MapperScan 扫描的包
  tenant:
    enable: true
    ignore-tables: [...]           # 不参与租户的表
```

## 2. 代码示例

### 2.1 完整 application.yml 模板

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/ruoyi-vue-pro
    username: root
    password: root
    driver-class-name: com.mysql.cj.jdbc.Driver
    druid:
      initial-size: 5
      min-idle: 5
      max-active: 20
      filters: stat

mybatis-plus:
  global-config:
    banner: false
    db-config:
      id-type: ASSIGN_ID  # 雪花算法
      logic-delete-field: deleted
      logic-delete-value: 1
      logic-not-delete-value: 0
  configuration:
    map-underscore-to-camel-case: true
    log-impl: org.apache.ibatis.logging.nologging.NoLoggingImpl

mybatis:
  lazy-initialization: false

yudao:
  info:
    base-package: com.ruoyi
  tenant:
    enable: true
```

### 2.2 自定义 TypeHandler

```java
// 文件：MyEncryptTypeHandler.java
public class MyEncryptTypeHandler extends EncryptTypeHandler {
    @Override
    protected String encrypt(String plain) {
        return AESUtils.encrypt(plain);  // 用 AES 加密
    }
}

// 在 application.yml 中配置
mybatis-plus:
  type-handlers-package: com.ruoyi.common.handler
```

## 3. 关键要点总结

- **yudao 的 MyBatis Starter 是"全家桶"**——分页、租户、权限、加解密、字典翻译全覆盖
- **`IdTypeEnvironmentPostProcessor`** 自动识别数据库类型
- **`EncryptTypeHandler`** 实现字段级透明加密
- **`@DictFormat` + `DictDataVOConvertSerializer`** 实现字典翻译
- **`@DS` 注解**支持多数据源

---

**文档版本**：v1.0
**最后更新**：2026-07-13
