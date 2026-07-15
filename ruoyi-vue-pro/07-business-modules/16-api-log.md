# 7.3.4 API 日志

> 理解 ruoyi 的 API 访问日志设计，异步记录 + 慢 SQL 警告。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 的 API 访问日志设计
- 理解 AOP + 异步队列实现日志记录
- 学会慢请求和错误的自动告警
- 能自定义 API 日志

## 📚 前置知识

- Spring AOP（详见 [AOP](../02-spring-boot/03-aop.md)）
- 消息队列（详见 [MQ 概念](../../_common/02-mq/01-concepts.md)、[Redis Stream 实现](../05-cache-and-mq/14-redis-stream-impl.md)）
- 菜单权限（详见 [菜单](./09-menu.md)）

## 1. 核心概念

### 1.1 API 日志的用途

- **调试**：查看某个请求的处理时间、参数、结果
- **审计**：谁在什么时间调用了什么接口
- **性能监控**：识别慢请求
- **异常排查**：自动记录错误响应

### 1.2 ruoyi 的 API 日志架构

```
[HTTP 请求] → [AOP 切面拦截] → [业务方法] → [AOP 记录结果]
                                  ↓
                          [通过 MQ 异步发送]
                                  ↓
                          [API 日志消费者]
                                  ↓
                          [写入 infra_api_access_log]
```

**关键设计**：
- **同步拦截**：AOP 切面记录开始时间
- **异步写入**：通过消息队列发送日志，**不阻塞业务**
- **慢请求警告**：超过 500ms 自动标记

### 1.3 @ApiAccessLog 注解

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface ApiAccessLog {
    String[] value() default {};  // 业务名
    boolean enable() default true;  // 是否启用
    boolean logResult() default true;  // 是否记录返回结果
    OperateTypeEnum operateType() default OperateTypeEnum.OTHER;
}
```

## 2. 代码示例

### 2.1 在 Controller 上使用

```java
@PostMapping("/create")
@PreAuthorize("@ss.hasPermission('system:user:create')")
@ApiAccessLog(operateType = OperateTypeEnum.CREATE)  // 标记为"创建"操作
public CommonResult<Long> createUser(@Valid @RequestBody UserSaveReqVO reqVO) {
    return success(userService.createUser(reqVO));
}
```

### 2.2 API 日志表

```sql
CREATE TABLE infra_api_access_log (
    id BIGINT PRIMARY KEY,
    trace_id VARCHAR(64),          -- 链路追踪 ID
    user_id BIGINT,                -- 用户 ID
    user_type TINYINT,             -- 用户类型
    application_name VARCHAR(50),  -- 应用名
    request_method VARCHAR(10),    -- GET/POST
    request_url VARCHAR(500),      -- 请求 URL
    request_params TEXT,           -- 请求参数
    response_body TEXT,            -- 响应结果
    user_ip VARCHAR(50),           -- 客户端 IP
    user_agent VARCHAR(500),       -- User-Agent
    java_method VARCHAR(500),      -- Java 方法
    java_method_args TEXT,         -- 方法参数
    start_time DATETIME,           -- 开始时间
    response_time INT,             -- 响应耗时（ms）
    error_code INT,                -- 错误码
    error_message TEXT,            -- 错误消息
    create_time DATETIME           -- 创建时间
);
```

### 2.3 异步发送日志

```java
@Aspect
@Component
public class ApiAccessLogAspect {

    @Around("@annotation(apiAccessLog)")
    public Object around(ProceedingJoinPoint joinPoint, ApiAccessLog apiAccessLog) throws Throwable {
        // 1. 记录开始时间
        LocalDateTime startTime = LocalDateTime.now();
        try {
            // 2. 执行目标方法
            Object result = joinPoint.proceed();
            // 3. 异步记录日志
            apiAccessLogFrameworkService.send(joinPoint, startTime, result, null);
            return result;
        } catch (Throwable ex) {
            // 4. 异常时也记录
            apiAccessLogFrameworkService.send(joinPoint, startTime, null, ex);
            throw ex;
        }
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 API 日志 Controller

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/controller/admin/logger/ApiAccessLogController.java`

**核心代码**（简化）：

```java
@Tag(name = "管理后台 - API 访问日志")
@RestController
@RequestMapping("/infra/api-access-log")
@Validated
public class ApiAccessLogController {

    @Resource
    private ApiAccessLogService apiAccessLogService;

    @GetMapping("/page")
    @PreAuthorize("@ss.hasPermission('infra:api-access-log:query')")
    public CommonResult<PageResult<ApiAccessLogRespVO>> getApiAccessLogPage(
            @Valid ApiAccessLogPageReqVO pageVO) {
        PageResult<ApiAccessLogDO> pageResult = apiAccessLogService.getApiAccessLogPage(pageVO);
        return success(BeanUtils.toBean(pageResult, ApiAccessLogRespVO.class));
    }

    @GetMapping("/get")
    @PreAuthorize("@ss.hasPermission('infra:api-access-log:query')")
    public CommonResult<ApiAccessLogRespVO> getApiAccessLog(@RequestParam("id") Long id) {
        ApiAccessLogDO log = apiAccessLogService.getApiAccessLog(id);
        return success(BeanUtils.toBean(log, ApiAccessLogRespVO.class));
    }

    @DeleteMapping("/delete")
    @PreAuthorize("@ss.hasPermission('infra:api-access-log:delete')")
    public CommonResult<Boolean> deleteApiAccessLog(@RequestParam("id") Long id) {
        apiAccessLogService.deleteApiAccessLog(id);
        return success(true);
    }
}
```

### 3.2 ApiAccessLog 注解

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/apilog/core/annotation/ApiAccessLog.java`

```java
@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
@Inherited
public @interface ApiAccessLog {

    String[] enable() default {WebFilterUtils.X_REQUEST_ID_HEADER};

    String[] exclude() default {};

    String operateModule() default "";

    String operateName() default "";

    int[] costTime() default {};  // 慢请求阈值（ms）
}
```

### 3.3 异步日志消费者

```java
@Component
public class ApiAccessLogConsumer {
    @Resource
    private ApiAccessLogService apiAccessLogService;

    @EventListener  // 或 @RabbitListener
    public void onMessage(ApiAccessLogMessage message) {
        // 写入数据库
        apiAccessLogService.createApiAccessLog(message);
    }
}
```

## 4. 关键要点总结

- ruoyi API 日志通过 AOP 切面拦截
- **异步写入**（不阻塞业务）
- 通过 `@ApiAccessLog` 注解标记
- 包含请求参数、响应、耗时、用户、IP 等
- 支持慢请求警告（默认 500ms）
- 异常也会被记录

## 5. 练习题

### 练习 1：基础（必做）

打开 `ApiAccessLogDO.java`，列出所有字段，理解每个字段的用途。

### 练习 2：进阶

阅读 `ApiAccessLogAspect.java`，理解 AOP 切面如何捕获 Controller 方法的入参和返回值。

### 练习 3：挑战（选做）

如果要支持"按用户分组查看 API 调用次数"统计，需要怎么实现？给出数据库 SQL 和 Java 聚合思路。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/controller/admin/logger/ApiAccessLogController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/apilog/core/annotation/ApiAccessLog.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
