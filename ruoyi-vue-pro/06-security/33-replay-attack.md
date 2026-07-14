# 33 防重放攻击：幂等性

> 详解防重放攻击（Replay Attack）的原理，以及 ruoyi 的幂等性实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解重放攻击的原理和危害
- 掌握幂等性（Idempotent）的概念
- 知道 ruoyi 的防重放方案：Token + Redis
- 能为关键接口实现幂等性

## 📚 前置知识

- HTTP 协议
- Redis 基础

## 1. 核心概念

### 1.1 什么是重放攻击？

**重放攻击（Replay Attack）**：攻击者截获合法的请求，**重复发送**给服务器，达到未授权目的。

**经典场景**：
```
1. 用户发起"转账 1000 元"请求
2. 攻击者截获请求
3. 攻击者重复发送请求
4. 用户被扣了 5000 元（5 次）
```

### 1.2 重放攻击的三个条件

1. **请求可被截获**：HTTP 明文传输
2. **请求无时间限制**：没有 timestamp
3. **请求无唯一标识**：服务器无法识别"同一个请求"

### 1.3 防御方案

| 方案 | 实现 | 作用 |
|------|------|------|
| **HTTPS** | 加密传输 | 防截获 |
| **Timestamp + 过期时间** | 请求带时间戳，过期拒绝 | 防复用 |
| **Nonce（随机数）** | 请求带唯一随机数 | 防重复 |
| **幂等 Token** | 服务端用 Redis 去重 | 业务级防护 |

## 2. 代码示例

### 2.1 幂等 Token 方案

```java
// 1. 前端发起请求前，先拿 Token
GET /api/idem-token
→ 返回: { "token": "uuid-1234" }

// 2. 业务请求带 token
POST /api/order
Headers: { "Idempotent-Token": "uuid-1234" }
Body: { ... }

// 3. 服务端用 Redis 去重
SET idem:uuid-1234 1 EX 300 NX
// 如果设置成功（NX 成功），说明是首次请求
// 如果设置失败（NX 失败），说明是重复请求
```

### 2.2 完整实现

```java
// 文件：IdempotentAspect.java
@Aspect
@Component
public class IdempotentAspect {

    @Around("@annotation(idempotent)")
    public Object around(ProceedingJoinPoint joinPoint, Idempotent idempotent) throws Throwable {
        // 1. 从请求头拿 token
        String token = ServletUtils.getRequest().getHeader("Idempotent-Token");
        if (StrUtil.isBlank(token)) {
            throw new ServiceException("缺少幂等 Token");
        }

        // 2. 尝试占用（SETNX）
        String key = "idem:" + token;
        Boolean success = redis.opsForValue().setIfAbsent(key, "1", idempotent.expireTime(), TimeUnit.SECONDS);
        if (Boolean.FALSE.equals(success)) {
            throw new ServiceException("请求重复，请稍后再试");
        }

        // 3. 执行业务
        return joinPoint.proceed();
    }
}
```

### 2.3 注解定义

```java
// 文件：Idempotent.java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Idempotent {
    int expireTime() default 300;  // 5 分钟
    String message() default "请求重复";
}
```

## 3. ruoyi 的幂等性方案

### 3.1 ruoyi 的实际实现

ruoyi 通过 `IdempotentAspect` + Redis SETNX 实现：

**AOP 拦截**（推测位置：`yudao-framework/yudao-spring-boot-starter-protection`）：

```java
@Aspect
public class IdempotentAspect {

    @Around("@annotation(idempotent)")
    public Object around(ProceedingJoinPoint joinPoint, Idempotent idempotent) throws Throwable {
        String token = obtainIdempotentToken();
        if (token == null) {
            throw new ServiceException("缺少幂等 Token");
        }

        // 关键：SETNX 原子操作
        String key = "idempotent:" + token;
        Boolean success = redisTemplate.opsForValue()
                .setIfAbsent(key, "1", idempotent.timeout(), TimeUnit.MILLISECONDS);
        if (Boolean.FALSE.equals(success)) {
            throw new ServiceException(idempotent.message());
        }
        return joinPoint.proceed();
    }
}
```

### 3.2 用法示例

```java
// 文件：OrderController.java
@PostMapping("/create")
@Idempotent(timeout = 5000, message = "请勿重复提交")
public CommonResult<Long> createOrder(@RequestBody OrderCreateReqVO reqVO) {
    return success(orderService.createOrder(reqVO));
}
```

### 3.3 防重放 vs 幂等的区别

| 维度 | 防重放 | 幂等 |
|------|--------|------|
| 关注点 | 网络层 | 业务层 |
| 实现 | Timestamp + Nonce | 业务唯一键 |
| 场景 | API 防攻击 | 用户重复点击 |
| 时间窗口 | 短（秒级） | 长（业务相关） |

## 4. 关键要点总结

- 重放攻击：攻击者**重复**发送合法请求
- 幂等性：同一请求多次执行结果一致
- 防御方案：HTTPS + Timestamp + Nonce + 业务幂等 Token
- ruoyi 用 `Idempotent` 注解 + Redis `SETNX` 实现
- 关键 API（支付、下单）必须加幂等

## 5. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/`（推测位置）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
