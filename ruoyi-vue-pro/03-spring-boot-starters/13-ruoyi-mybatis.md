# 2.8 ruoyi 的 MyBatis 配置分析

> 全面分析 yudao MyBatis Starter 的配置项与扩展点。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 yudao MyBatis 的所有配置项
- 掌握 `application.yml` 中 MyBatis 相关配置
- 了解 yudao 对 MyBatis-Plus 的深度定制点
- 能根据业务需求调整 MyBatis 行为

## 📚 前置知识

- [06-mybatis-starter.md](./06-mybatis-starter.md)
- [09-pagination.md](./09-pagination.md)
- [10-data-permission.md](./10-data-permission.md)
- [11-tenant-interceptor.md](./11-tenant-interceptor.md)

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

## 3. ruoyi 仓库源码解读

### 3.1 EncryptTypeHandler（加密字段）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/type/EncryptTypeHandler.java`
**核心代码**（节选）：

```java
public class EncryptTypeHandler extends BaseTypeHandler<String> {

    @Override
    public void setNonNullParameter(PreparedStatement ps, int i, String parameter, JdbcType jdbcType) {
        // 写入时加密
        ps.setString(i, encrypt(parameter));
    }

    @Override
    public String getNullableResult(ResultSet rs, String columnName) {
        // 读出时解密
        return decrypt(rs.getString(columnName));
    }
    // ...
}
```

**解读**：
- 透明加密：`SELECT *` 返回明文（自动解密），`UPDATE` 时自动加密
- 业务方在实体字段上加 `typeHandler = EncryptTypeHandler.class` 即可

### 3.2 TranslateUtils（字典翻译）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/translate/core/TranslateUtils.java`
**核心代码**（节选）：

```java
public class TranslateUtils {
    /**
     * 将字典项 value 翻译为 label
     */
    public static <T> T translate(CharSequence type, String value, Class<T> returnType) {
        DictDataSimpleDO dictData = DictFrameworkUtils.getDictData(type, value);
        if (returnType == String.class) {
            return (T) dictData.getLabel();
        }
        // ...
    }
}
```

**典型用法**：

```java
@Data
public class OrderRespVO {
    private Long id;
    private Long status;
    @DictFormat("order_status")  // 翻译成 label
    @JsonSerialize(using = DictDataVOConvertSerializer.class)
    private String statusName;
}
```

### 3.3 IdTypeEnvironmentPostProcessor

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/IdTypeEnvironmentPostProcessor.java`
**核心代码**（节选）：

```java
public class IdTypeEnvironmentPostProcessor implements EnvironmentPostProcessor {
    @Override
    public void postProcessEnvironment(ConfigurableEnvironment environment, SpringApplication application) {
        // 1. 解析 spring.datasource.url 中的数据库类型
        // 2. 根据数据库类型设置 mybatis-plus.global-config.db-config.id-type
        //    - MySQL/PostgreSQL/Oracle: ASSIGN_ID（雪花）
        //    - Oracle 12c+: 特殊处理
    }
}
```

**解读**：
- `EnvironmentPostProcessor` 是 Spring Boot 早期扩展点
- 在 Spring 启动前根据数据库类型**自动设置 ID 策略**
- **业务方不用关心**配置

### 3.4 多数据源支持

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/datasource/`
**核心组件**：

- `YudaoDataSourceAutoConfiguration` — 装配
- `@DS` 注解 — 切换数据源
- `DynamicDataSourceAnnotationAdvisor` — AOP 切面

```java
@Service
public class OrderServiceImpl {
    @DS("slave")  // 切到从库
    public List<OrderDO> getOrders() {
        return orderMapper.selectList();
    }
}
```

## 4. 关键要点总结

- **yudao 的 MyBatis Starter 是"全家桶"**——分页、租户、权限、加解密、字典翻译全覆盖
- **`IdTypeEnvironmentPostProcessor`** 自动识别数据库类型
- **`EncryptTypeHandler`** 实现字段级透明加密
- **`@DictFormat` + `DictDataVOConvertSerializer`** 实现字典翻译
- **`@DS` 注解**支持多数据源

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 的 `application.yml` 中找到所有 MyBatis 相关配置，理解每一项的意义。

### 练习 2：进阶

为 `UserDO.email` 字段加 `EncryptTypeHandler`，验证写入数据库是密文，读取时自动解密。

### 练习 3：挑战（选做）

为 yudao 扩展多数据源（master + slave + report），用 `@DS` 切换，并实现读写分离。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/type/EncryptTypeHandler.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/translate/core/TranslateUtils.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/IdTypeEnvironmentPostProcessor.java`
- MyBatis-Plus 文档：https://baomidou.com/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
