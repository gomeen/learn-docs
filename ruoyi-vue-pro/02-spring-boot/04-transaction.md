# 04 Spring 事务管理

> 掌握 `@Transactional` 的传播行为、隔离级别、回滚规则，能正确处理 ruoyi-vue-pro 中的事务场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Spring 事务的 ACID 特性和底层原理
- 区分 7 种传播行为（PROPAGATION_REQUIRED、REQUIRES_NEW 等）
- 正确设置隔离级别（READ_UNCOMMITTED、SERIALIZABLE 等）
- 掌握 `@Transactional` 失效的常见场景

## 📚 前置知识

- [03-aop.md](./03-aop.md)（AOP 基础，事务本质是 AOP）
- 数据库事务基础（MySQL 事务与隔离级别详见 [02-mysql-transaction](../04-database/02-mysql-transaction.md)）

## 1. 核心概念

### 1.1 事务的 ACID

- **A**tomicity（原子性）：要么全成功，要么全失败
- **C**onsistency（一致性）：事务前后数据完整性约束不变
- **I**solation（隔离性）：并发事务互不干扰
- **D**urability（持久性）：事务提交后永久生效

### 1.2 7 种传播行为

| 传播行为 | 说明 |
|---------|------|
| **REQUIRED**（默认） | 有事务就加入，没有就新建 |
| **SUPPORTS** | 有事务就加入，没有就非事务执行 |
| **MANDATORY** | 必须在已有事务中执行，否则抛异常 |
| **REQUIRES_NEW** | 无论有没有，都新建事务（外层事务挂起） |
| **NOT_SUPPORTED** | 非事务执行，有事务则挂起 |
| **NEVER** | 非事务执行，有事务则抛异常 |
| **NESTED** | 有事务则嵌套（保存点），没有就新建 |

### 1.3 4 种隔离级别

| 隔离级别 | 脏读 | 不可重复读 | 幻读 |
|---------|------|-----------|------|
| READ_UNCOMMITTED | ✅ | ✅ | ✅ |
| READ_COMMITTED | ❌ | ✅ | ✅ |
| REPEATABLE_READ（MySQL 默认） | ❌ | ❌ | ✅ |
| SERIALIZABLE | ❌ | ❌ | ❌ |

## 2. 代码示例

### 2.1 基础事务

```java
// 文件：OrderServiceImpl.java
@Service
public class OrderServiceImpl {

    @Transactional  // 默认 REQUIRED 传播，方法抛异常自动回滚
    public void createOrder(OrderDTO order) {
        orderDao.insert(order);
        stockDao.deduct(order.getSkuId(), order.getQuantity());
        // 任何一步失败，整体回滚
    }
}
```

### 2.2 常见错误：自调用导致事务失效

```java
// ❌ 错误：通过 this 调用，绕过 Spring 代理（代理机制见 [03-aop](./03-aop.md)）
@Service
public class UserService {
    @Transactional
    public void methodA() { methodB(); }  // 不会触发事务！

    @Transactional
    public void methodB() { ... }
}

// ✅ 正确：注入自己的代理
@Service
public class UserService {
    @Autowired
    private UserService self;  // 注入自己（Spring 代理）

    public void methodA() { self.methodB(); }  // 触发事务
}
```

### 2.3 REQUIRES_NEW：日志独立提交

```java
@Service
public class OrderService {

    @Transactional
    public void createOrder() {
        orderDao.insert(order);
        // 无论订单是否成功，操作日志都独立提交
        logService.saveLog();  // 在子方法上加 @Transactional(propagation = REQUIRES_NEW)
    }
}
```

## 3. 关键要点总结

- **默认传播 REQUIRED + 默认隔离依赖数据库**
- **`@Transactional` 失效场景**：
  - 自调用（`this.method()`）绕过代理
  - 方法不是 public
  - 异常被 try-catch 吞掉
  - 抛出非 RuntimeException（如 IOException 默认不回滚，需配 `rollbackFor`）
- ruoyi 通过 `ServiceException` + `GlobalExceptionHandler` 实现统一事务回滚
- 推荐：`@Transactional(rollbackFor = Exception.class)` 显式指定回滚异常

---

**文档版本**：v1.0
**最后更新**：2026-07-13
