# 20 @DS 切换数据源

> `@DS` 是 dynamic-datasource 的核心注解，理解它就掌握了多数据源切换的关键。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `@DS` 注解的所有用法
- 知道 `@DS` 与 `@Transactional` 的关系
- 理解 `@DSTransactional` 解决的问题
- 在 ruoyi 中正确应用数据源切换

## 📚 前置知识

- [23-dynamic-datasource.md](./23-dynamic-datasource.md)
- [02-mysql-transaction.md](./02-mysql-transaction.md)
- Spring `@Transactional` 见 [04-transaction](../02-spring-boot/04-transaction.md)

## 1. 核心概念

### 1.1 `@DS` 注解的三种粒度

```java
// 方法级（最常用）
@DS("slave")
public List<Order> listFromSlave() { ... }

// 类级（对所有方法生效）
@DS("slave")
@Service
public class ReportService { ... }

// 类 + 方法（方法级别覆盖类级别）
@DS("slave")
@Service
public class ReportService {
    @DS("master")  // 这个方法走 master
    public void saveReport() { ... }
}
```

### 1.2 `@DS` 与 `@Transactional` 的执行顺序

```
请求 → @Transactional（开启事务）→ @DS（切换数据源）→ 业务方法
```

**重要**：`@Transactional` 必须在 `@DS` 的外层。

### 1.3 `@DSTransactional` 解决的事务问题

```
场景：跨多个数据源的操作需要事务
  - @Transactional：只支持单数据源
  - @DSTransactional：支持多数据源（基于 dynamic-datasource）
```

## 2. 代码示例

### 2.1 基础用法

```java
@Service
public class OrderServiceImpl implements OrderService {

    @Resource
    private OrderMapper orderMapper;

    // 默认 master
    public List<Order> listAll() {
        return orderMapper.selectList();
    }

    // 走从库（读多写少场景）
    @DS("slave")
    public PageResult<Order> pageOrders(OrderPageReqVO reqVO) {
        return orderMapper.selectPage(reqVO, new LambdaQueryWrapperX<>());
    }

    // 走其他数据源
    @DS("oracle")
    public List<LegacyOrder> listLegacyOrders() {
        return legacyOrderMapper.selectList();
    }
}
```

### 2.2 类级别使用

```java
@DS("slave")
@Service
public class ReportServiceImpl implements ReportService {

    // 所有方法都走 slave
    public ReportVO dailyReport() {
        return reportMapper.dailyReport();
    }

    // 覆盖：单独这个方法走 master
    @DS("master")
    public void saveReportSnapshot(ReportVO report) {
        reportMapper.insert(report);
    }
}
```

### 2.3 多数据源事务

```java
// ❌ 错误：@Transactional 只支持单数据源
@Transactional
public void processCrossDB(Order order, Log log) {
    orderMapper.insert(order);  // master
    logMapper.insert(log);       // slave（事务失效！）
}

// ✅ 正确：使用 @DSTransactional
@DSTransactional
public void processCrossDB(Order order, Log log) {
    orderMapper.insert(order);  // master 事务
    logMapper.insert(log);       // slave 事务（一起回滚）
}
```

### 2.4 动态数据源（运行时切换）

```java
// 手动切换数据源（不推荐，优先用 @DS）
DynamicDataSourceContextHolder.push("slave");
// ... 业务操作 ...
DynamicDataSourceContextHolder.poll();
```

## 3. 关键要点总结

- `@DS("name")` 用于切换数据源，可加在方法或类上
- 单数据源用 `@Transactional`，多数据源用 `@DSTransactional`
- `@Transactional` 必须在 `@DS` 的外层（确保数据源在事务开启前确定）
- ruoyi 通过 `assignRoleMenu` 演示了 `@DSTransactional` 的正确用法
- 数据源名称必须在 yml 中预先配置

---

**文档版本**：v1.0
**最后更新**：2026-07-13
