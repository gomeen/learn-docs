# 04 Spring 事务管理

> 掌握 `@Transactional` 的传播行为、隔离级别、回滚规则，能正确处理 ruoyi-vue-pro 中的事务场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Spring 事务的 ACID 特性和底层原理
- 区分 7 种传播行为（PROPAGATION_REQUIRED、REQUIRES_NEW 等）
- 正确设置隔离级别（READ_UNCOMMITTED、SERIALIZABLE 等）
- 掌握 `@Transactional` 失效的常见场景

## 📚 前置知识

- 01-ioc.md（AOP 基础，事务本质是 AOP）
- 数据库事务基础

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
// ❌ 错误：通过 this 调用，绕过 Spring 代理
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

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 全局异常处理触发事务回滚

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
**核心代码**（行 130-160）：

```java
/**
 * 处理 ServiceException 业务异常
 */
@ExceptionHandler(value = ServiceException.class)
public CommonResult<?> serviceExceptionHandler(ServiceException ex) {
    log.warn("[serviceExceptionHandler]", ex);
    // 插入异常日志
    createExceptionLog(ex, null);
    return CommonResult.error(ex.getCode(), ex.getMessage());
}

/**
 * 处理系统异常
 */
@ExceptionHandler(value = Exception.class)
public CommonResult<?> exceptionHandler(HttpServletRequest request, Throwable ex) {
    log.error("[exceptionHandler]", ex);
    // 插入异常日志
    createExceptionLog(ex, WebFrameworkUtils.getLoginUserId());
    // 返回 ERROR CommonResult
    return CommonResult.error(INTERNAL_SERVER_ERROR.getCode(), INTERNAL_SERVER_ERROR.getMsg());
}
```

**解读**：
- 第 6 行：`@ExceptionHandler(value = ServiceException.class)` 拦截业务异常
- **事务关联**：当 Service 中抛 `ServiceException`，外层 `@Transactional` 捕获后回滚
- 第 15 行：所有未捕获的 `Exception` 都返回统一的 500 错误，避免敏感信息泄露
- **设计意图**：业务异常用 `ServiceException`（可预期、可处理），系统异常用 `Exception`（兜底处理）

### 3.2 ServiceException 设计

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/exception/ServiceException.java`（推测存在）
**相关代码**（CommonResult.java 第 99-105）：

```java
/**
 * 判断是否有异常。如果有，则抛出 {@link ServiceException} 异常
 */
public void checkError() throws ServiceException {
    if (isSuccess()) {
        return;
    }
    // 业务异常
    throw new ServiceException(code, msg);
}
```

**解读**：
- `CommonResult.checkError()` 是 ruoyi 的特色：把 RPC 调用的失败结果"翻译"为本地 `ServiceException`
- 这种设计让调用方可以用 `try-catch` 或 `@Transactional(rollbackFor = ServiceException.class)` 统一处理
- **事务回滚触发**：抛 `ServiceException` → `@Transactional` 拦截 → 默认 RuntimeException 触发回滚

## 4. 关键要点总结

- **默认传播 REQUIRED + 默认隔离依赖数据库**
- **`@Transactional` 失效场景**：
  - 自调用（`this.method()`）绕过代理
  - 方法不是 public
  - 异常被 try-catch 吞掉
  - 抛出非 RuntimeException（如 IOException 默认不回滚，需配 `rollbackFor`）
- ruoyi 通过 `ServiceException` + `GlobalExceptionHandler` 实现统一事务回滚
- 推荐：`@Transactional(rollbackFor = Exception.class)` 显式指定回滚异常

## 5. 练习题

### 练习 1：基础（必做）

编写一个 `TransferService.transfer(fromId, toId, amount)` 方法，用 `@Transactional` 保证转账原子性（扣款 + 加款）。

### 练习 2：进阶

解释为什么 ruoyi 的 `CommonResult.checkError()` 方法要抛 `ServiceException` 而不是 `BusinessException` 或 `RuntimeException`？这种设计对事务管理有什么好处？

### 练习 3：挑战（选做）

实现一个嵌套事务场景：订单创建（外层 REQUIRED）+ 发送通知（内层 NESTED），用 `try-catch` 捕获通知失败但不影响订单。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/pojo/CommonResult.java`
- Spring 事务官方文档：https://docs.spring.io/spring-framework/reference/data-access.html#transaction
- 芋道事务教程：https://doc.iocoder.cn/spring-boot-transaction/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
