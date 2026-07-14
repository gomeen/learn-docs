# 19 dynamic-datasource 多数据源

> ruoyi 通过 dynamic-datasource 实现读写分离 + 多数据库切换，是生产级分布式项目的基础。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解多数据源的常见应用场景
- 掌握 dynamic-datasource 的核心配置
- 知道 `@DS` 注解的用法
- 了解 ruoyi 的多数据源架构设计

## 📚 前置知识

- Spring Boot 数据库连接池
- 02-mysql-transaction.md

## 1. 核心概念

### 1.1 为什么需要多数据源？

```
1. 读写分离：主库写、从库读，提升读性能
2. 业务分库：订单库、用户库、商品库独立
3. 多租户：每个租户独立数据库
4. 多数据库类型：MySQL + PostgreSQL + Elasticsearch
```

### 1.2 dynamic-datasource 是什么？

`dynamic-datasource-spring-boot-starter` 是基于 MyBatis Plus 的多数据源切换框架：
- 基于 Spring AOP + 注解实现数据源路由
- 支持任意数据库（MySQL、PostgreSQL、Oracle）
- 内置连接池（Druid、HikariCP）
- 支持 `@DS` 注解方法级/类级切换
- 支持 `@DSTransactional` 多数据源事务

### 1.3 ruoyi 的多数据源架构

```
yudao-framework/yudao-spring-boot-starter-mybatis
    ├── 整合 dynamic-datasource
    ├── 提供 @DS / @DSTransactional 注解
    └── 提供 DataSourceConfigDO（运行时数据源配置）
```

## 2. 代码示例

### 2.1 引入依赖

```xml
<dependency>
    <groupId>com.baomidou</groupId>
    <artifactId>dynamic-datasource-spring-boot3-starter</artifactId>
</dependency>
```

### 2.2 配置多数据源

```yaml
spring:
  datasource:
    dynamic:
      primary: master           # 默认数据源
      strict: false             # 找不到数据源时不抛异常
      datasource:
        master:                 # 主库
          url: jdbc:mysql://127.0.0.1:3306/ruoyi?useSSL=false
          username: root
          password: 123456
        slave:                  # 从库（读）
          url: jdbc:mysql://127.0.0.1:3306/ruoyi?useSSL=false
          username: readonly
          password: 123456
        oracle:                 # 其他库
          url: jdbc:oracle:thin:@127.0.0.1:1521:xe
          username: system
          password: oracle
          driver-class-name: oracle.jdbc.OracleDriver
```

### 2.3 使用 @DS 切换

```java
@Service
public class OrderServiceImpl implements OrderService {

    // 不写 @DS：使用默认 primary
    public List<Order> listAll() {
        return orderMapper.selectList();
    }

    // 强制走从库
    @DS("slave")
    public List<Order> listFromSlave() {
        return orderMapper.selectList();
    }

    // 强制走主库
    @DS("master")
    public void createOrder(Order order) {
        orderMapper.insert(order);
    }

    // 在类上使用，对所有方法生效
    @DS("slave")
    public List<OrderVO> statOrders() {
        return orderMapper.statByDay();
    }
}
```

### 2.4 多数据源事务

```java
// 单数据源：用 @Transactional
@Transactional(rollbackFor = Exception.class)
public void updateMaster(Order order) {
    orderMapper.updateById(order);
}

// 多数据源：用 @DSTransactional（来自 dynamic-datasource）
@DSTransactional
public void updateMultiple(Order order, Log log) {
    orderMapper.updateById(order);  // master
    logMapper.insert(log);           // slave
}
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的多数据源配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
**核心代码**（行 33-80）：

```yaml
  datasource:
    druid:
      web-stat-filter:
        enabled: true
      stat-view-servlet:
        enabled: true
      filter:
        stat:
          enabled: true
          log-slow-sql: true
          slow-sql-millis: 100
          merge-sql: true
    dynamic:
      druid:
        initial-size: 1
        min-idle: 1
        max-active: 20
        max-wait: 60000
        validation-query: SELECT 1 FROM DUAL
      primary: master
      datasource:
        master:
          url: jdbc:mysql://127.0.0.1:3306/ruoyi-vue-pro-jdk8?useSSL=false&serverTimezone=Asia/Shanghai
          username: root
          password: 123456
        slave:
          lazy: true
          url: jdbc:mysql://127.0.0.1:3306/ruoyi-vue-pro-jdk8?useSSL=false&serverTimezone=Asia/Shanghai
          username: root
          password: 123456
```

**解读**：
- 第 1-15 行：`druid` 配置 —— 监控 + 慢 SQL 记录
- 第 16-23 行：`dynamic.druid` —— 连接池参数（连接池复用 Druid）
- 第 24 行：`primary: master` —— 默认数据源
- 第 25-40 行：`master` + `slave` —— 读写分离的两个数据源
- 第 37 行：`lazy: true` —— 懒加载，启动时不连接从库（避免启动报错）
- **设计意图**：所有配置集中在 `spring.datasource.dynamic` 下，与 Spring Boot 默认格式兼容

### 3.2 运行时数据源配置（DataSourceConfigDO）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/dal/dataobject/db/DataSourceConfigDO.java`

```java
@TableName(value = "infra_data_source_config", autoResultMap = true)
@KeySequence("infra_data_source_config_seq")
@Data
@TenantIgnore
public class DataSourceConfigDO extends BaseDO {

    public static final Long ID_MASTER = 0L;

    private Long id;
    private String name;
    private String url;
    private String username;

    @TableField(typeHandler = EncryptTypeHandler.class)
    private String password;
}
```

**解读**：
- 第 1 行：`@TenantIgnore` —— 多租户场景忽略此表（数据源配置是全局的）
- 第 10 行：`ID_MASTER = 0L` —— 主库用特殊 ID 标识
- 第 16 行：`@TableField(typeHandler = EncryptTypeHandler.class)` —— **密码加密存储**
- **设计意图**：支持「运行时动态添加数据源」—— 通过管理后台配置 → 写入 `infra_data_source_config` 表 → 动态注册到数据源路由

### 3.3 DataSourceConfigServiceImpl 动态注册

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
    public DataSourceConfigDO getDataSourceConfig(Long id) {
        // 如果 id 为 0，默认为 master 的数据源
        if (Objects.equals(id, DataSourceConfigDO.ID_MASTER)) {
            return buildMasterDataSourceConfig();
        }
        // 从 DB 中读取
        return dataSourceConfigMapper.selectById(id);
    }

    private DataSourceConfigDO buildMasterDataSourceConfig() {
        String primary = dynamicDataSourceProperties.getPrimary();
        DataSourceProperty dataSourceProperty = dynamicDataSourceProperties.getDatasource().get(primary);
        return new DataSourceConfigDO().setId(DataSourceConfigDO.ID_MASTER).setName(primary)
                .setUrl(dataSourceProperty.getUrl())
                .setUsername(dataSourceProperty.getUsername())
                .setPassword(dataSourceProperty.getPassword());
    }
}
```

**解读**：
- 第 5-8 行：注入 `DynamicDataSourceProperties` —— 读取 yml 中已配置的数据源
- 第 14-17 行：`getDataSourceConfig(0L)` 返回 master 数据源配置（从 yml 读取）
- 第 19 行：`getDataSourceConfig(其他ID)` 从 DB 读取
- **设计意图**：用户可在管理后台「数据源」菜单新增数据源 → 写入 `infra_data_source_config` → 用 `@DS("custom_name")` 引用

## 4. 关键要点总结

- dynamic-datasource 是 MyBatis Plus 生态最流行的多数据源方案
- ruoyi 默认配置 master + slave（读写分离）
- `@DS("name")` 切换数据源；`@DSTransactional` 处理多数据源事务
- 运行时数据源通过 `infra_data_source_config` 表管理
- 密码加密通过 `EncryptTypeHandler` 实现

## 5. 练习题

### 练习 1：基础（必做）

配置两个数据源（master + slave），用 `@DS("slave")` 注解一个查询方法，启动应用观察是否切换到从库。

### 练习 2：进阶

阅读 `DataSourceConfigDO` 和 `DataSourceConfigServiceImpl`，说明 ruoyi 如何实现「运行时动态添加数据源」。找出动态注册的触发代码（在哪个方法 / 哪个事件）。

### 练习 3：挑战（选做）

设计一个「多租户动态数据源」方案：每个租户的请求路由到独立数据库。要求：
1. 拦截 HTTP 请求，提取 tenantId
2. 根据 tenantId 动态注册数据源（如果未注册）
3. 用 ThreadLocal 保存当前租户数据源

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/dal/dataobject/db/DataSourceConfigDO.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/db/DataSourceConfigServiceImpl.java`
- dynamic-datasource 官方文档：https://github.com/baomidou/dynamic-datasource

---

**文档版本**：v1.0
**最后更新**：2026-07-13