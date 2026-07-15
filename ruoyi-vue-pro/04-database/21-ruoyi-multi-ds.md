# 21 ruoyi 的多数据源实战

> ruoyi 通过 dynamic-datasource 实现「读写分离 + 多租户 + 多类型数据库」的完整方案。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ruoyi 多数据源架构设计
- 掌握数据源配置的动态扩展机制
- 知道密码加密存储的实现
- 了解多租户场景下的数据源切换

## 📚 前置知识

- [19-dynamic-datasource.md](./19-dynamic-datasource.md)
- [20-ds-annotation.md](./20-ds-annotation.md)
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

## 3. ruoyi 仓库源码解读

### 3.1 完整数据源配置结构

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`

```yaml
spring:
  autoconfigure:
    exclude:
      - com.alibaba.druid.spring.boot.autoconfigure.DruidDataSourceAutoConfigure  # 排除 Druid 自动配置
  datasource:
    druid:
      filter:
        stat:
          enabled: true
          log-slow-sql: true  # 慢 SQL 记录
          slow-sql-millis: 100
    dynamic:
      druid:
        initial-size: 1
        min-idle: 1
        max-active: 20
        max-wait: 60000
        validation-query: SELECT 1 FROM DUAL
        test-while-idle: true
      primary: master
      datasource:
        master:
          url: jdbc:mysql://127.0.0.1:3306/ruoyi-vue-pro-jdk8
          username: root
          password: 123456
        slave:
          lazy: true
          url: jdbc:mysql://127.0.0.1:3306/ruoyi-vue-pro-jdk8
          username: root
          password: 123456
```

**解读**：
- 第 3 行：排除 Druid 自动配置（因为 dynamic-datasource 自己接管 Druid）
- 第 5-12 行：Druid 监控配置（与连接池配置分离）
- 第 13-21 行：`dynamic.druid` —— 连接池参数（被 dynamic-datasource 复用）
- 第 22 行：`primary: master` —— 默认数据源
- 第 23-37 行：master + slave 双数据源
- **关键**：slave 用 `lazy: true` 懒加载（启动时不连接，避免从库挂掉导致启动失败）

### 3.2 DataSourceConfigService 实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/db/DataSourceConfigServiceImpl.java`

```java
@Service
@Validated
public class DataSourceConfigServiceImpl implements DataSourceConfigService {

    @Resource
    private DataSourceConfigMapper dataSourceConfigMapper;

    @Resource
    private DynamicDataSourceProperties dynamicDataSourceProperties;

    @Override
    public Long createDataSourceConfig(DataSourceConfigSaveReqVO createReqVO) {
        DataSourceConfigDO config = BeanUtils.toBean(createReqVO, DataSourceConfigDO.class);
        validateConnectionOK(config);  // 验证连接可用

        // 插入
        dataSourceConfigMapper.insert(config);
        // 返回
        return config.getId();
    }

    private void validateConnectionOK(DataSourceConfigDO config) {
        boolean success = JdbcUtils.isConnectionOK(config.getUrl(), config.getUsername(), config.getPassword());
        if (!success) {
            throw exception(DATA_SOURCE_CONFIG_NOT_OK);
        }
    }
}
```

**解读**：
- 第 12 行：`validateConnectionOK` —— 创建数据源前先测试连接（避免写入无效配置）
- 第 14 行：`JdbcUtils.isConnectionOK` —— 通过 JDBC Driver 测试连接
- **设计意图**：用户在前端页面填写数据源 → 先验证连接 → 写入 DB → 后续动态注册

### 3.3 密码加密：EncryptTypeHandler

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/type/EncryptTypeHandler.java`（典型实现）

```java
// 加密处理器（简化示例）
public class EncryptTypeHandler extends BaseTypeHandler<String> {
    @Override
    public void setNonNullParameter(PreparedStatement ps, int i, String parameter, JdbcType jdbcType) {
        // 写入：明文 → 密文
        ps.setString(i, encrypt(parameter));
    }

    @Override
    public String getNullableResult(ResultSet rs, String columnName) {
        // 读取：密文 → 明文
        return decrypt(rs.getString(columnName));
    }

    private String encrypt(String plain) {
        return AESUtils.encrypt(plain, KEY);
    }

    private String decrypt(String encrypted) {
        return AESUtils.decrypt(encrypted, KEY);
    }
}
```

**解读**：
- `EncryptTypeHandler` 拦截字段的写入/读取
- 数据库存储的是密文，Java 对象是明文
- **应用场景**：数据源密码、API 密钥、用户敏感信息
- **密钥管理**：KEY 应该来自配置中心或环境变量，不要硬编码

### 3.4 多租户数据源（tenant 字段自动填充）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/`

通过 `TenantBaseDO`（继承 `BaseDO`）实现多租户隔离：

```java
// 简化的多租户实现思路
public abstract class TenantBaseDO extends BaseDO {
    @TableField(fill = FieldFill.INSERT)
    private Long tenantId;
}
```

**运行时多租户**通过：
1. 请求头 `X-Tenant-Id` 携带
2. 拦截器提取到 `TenantContextHolder`
3. 查询时 `WHERE tenant_id = ?`（ruoyi 通过 MyBatis 拦截器自动注入）

## 4. 关键要点总结

- ruoyi 多数据源 = dynamic-datasource + Druid + 多数据库支持
- yml 配置 + DB 配置混合：启动时静态 + 运行时动态
- 密码必须加密存储（`EncryptTypeHandler`）
- `@DSTransactional` 处理多数据源事务
- 多租户场景通过 `TenantBaseDO` + 拦截器实现

## 5. 练习题

### 练习 1：基础（必做）

修改 `application-local.yaml`，添加一个 `bi` 数据源（PostgreSQL），启动应用，访问 Druid 监控页面验证三个数据源都已注册。

### 练习 2：进阶

阅读 `DataSourceConfigServiceImpl`，追踪「用户添加数据源」到「动态数据源生效」的完整流程：哪些类、哪些方法、什么时机生效。

### 练习 3：挑战（选做）

设计一个「数据源热加载」机制：当 `infra_data_source_config` 表的数据发生变化（如新增）时，自动注册到 dynamic-datasource，无需重启应用（提示：用 Redis 发布订阅或定时轮询）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/db/DataSourceConfigServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/dal/dataobject/db/DataSourceConfigDO.java`
- dynamic-datasource 官方文档：https://github.com/baomidou/dynamic-datasource
- ruoyi 官方文档《芋道 Spring Boot 多数据源（读写分离）入门》

---

**文档版本**：v1.0
**最后更新**：2026-07-13