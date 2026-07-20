# 19 dynamic-datasource 多数据源

> ruoyi 通过 dynamic-datasource 实现读写分离 + 多数据库切换，是生产级分布式项目的基础。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解多数据源的常见应用场景
- 掌握 dynamic-datasource 的核心配置
- 知道 `@DS` 注解的用法
- 了解 ruoyi 的多数据源架构设计

## 📚 前置知识

- Spring Boot 数据库连接池（Druid 见 [22-druid](./26-druid.md)，Hikari 见 [23-hikari](./27-hikari.md)）
- [02-mysql-transaction.md](./02-mysql-transaction.md)
- `@DS` 注解见 [20-ds-annotation](./24-ds-annotation.md)

## 1. 核心概念

### 1.1 为什么需要多数据源？

```
1. 读写分离：主库写、从库读，提升读性能
2. 业务分库：订单库、用户库、商品库独立
3. 多租户：每个租户独立数据库（多租户见 [多租户](../../_common/08-authorization/05-multi-tenant.md)）
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

## 3. 关键要点总结

- dynamic-datasource 是 MyBatis Plus 生态最流行的多数据源方案
- ruoyi 默认配置 master + slave（读写分离）
- `@DS("name")` 切换数据源；`@DSTransactional` 处理多数据源事务
- 运行时数据源通过 `infra_data_source_config` 表管理
- 密码加密通过 `EncryptTypeHandler` 实现

---

**文档版本**：v1.0
**最后更新**：2026-07-13
