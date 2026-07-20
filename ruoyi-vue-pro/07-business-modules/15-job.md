# 7.3.2 定时任务

> 理解 ruoyi 中定时任务（Job）的实现，基于 Quartz 调度框架。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 定时任务的工作原理
- 理解 Cron 表达式的使用
- 学会在 ruoyi 中创建自定义定时任务
- 了解 Quartz 调度框架

## 📚 前置知识

- Spring Boot 定时任务（详见 [Scheduled](../02-spring-boot/27-scheduled.md)）
- Cron 表达式语法
- Quartz / XXL-Job 调度（详见 [XXL-Job Starter](../03-spring-boot-starters/41-xxl-job.md)）

## 1. 核心概念

### 1.1 ruoyi 定时任务架构

```
[管理后台] → [任务定义] → [数据库] ← [Quartz Scheduler] → [执行 Job]
                                       ↑
                                       │ 触发
                                       └─ Cron / 间隔
```

**核心组件**：
- **Job 定义**：存储在 `infra_job` 表
- **Job 日志**：执行记录存储在 `infra_job_log` 表
- **Job 调度器**：Quartz + Spring 集成
- **任务执行**：通过反射调用 `@JobHandler` 注解的类

### 1.2 定时任务核心字段

```java
public class JobDO {
    private Long id;
    private String name;          // 任务名称
    private String handlerName;   // JobHandler 名称
    private String handlerParam;  // 任务参数
    private String cronExpression; // Cron 表达式
    private Integer status;        // 状态（0-停止 1-运行）
    private Integer retryCount;    // 重试次数
    private Integer retryInterval; // 重试间隔
}
```

### 1.3 创建一个定时任务

```java
@Component
@JobHandler("demoJob")  // 任务标识
public class DemoJob implements IJobHandler {

    @Override
    public String execute(String param) {
        // 业务逻辑
        return "执行成功";
    }
}
```

## 2. 代码示例

### 2.1 JobHandler 注解

```java
@Component
@JobHandler(value = "orderAutoCancelJob")
public class OrderAutoCancelJob implements IJobHandler {

    @Resource
    private OrderService orderService;

    @Override
    public String execute(String param) {
        // 取消超时未支付的订单
        int count = orderService.autoCancelUnpaidOrders(30); // 30 分钟
        return String.format("取消 %d 个超时订单", count);
    }
}
```

### 2.2 Cron 表达式

```
秒   分   时   日   月   周
0    0    2    *    *    ?     每天凌晨 2 点
0    0    */2  *    *    ?     每 2 小时
0    30   9    *    *    ?     每天 9:30
0    0    0    1    *    ?     每月 1 号凌晨
```

### 2.3 触发定时任务

```java
// 立即触发一次
@PostMapping("/trigger")
public CommonResult<Boolean> triggerJob(@RequestParam("id") Long id) {
    jobService.triggerJob(id);
    return success(true);
}

// 启动 / 停止
@PutMapping("/update-status")
public CommonResult<Boolean> updateJobStatus(@RequestParam("id") Long id,
                                              @RequestParam("status") Integer status) {
    jobService.updateJobStatus(id, status);
    return success(true);
}
```

## 3. 关键要点总结

- ruoyi 定时任务基于 Quartz
- 通过 `@JobHandler` 注解定义任务
- 任务配置存储在 `infra_job` 表
- 支持 Cron 表达式、参数、重试
- 执行日志记录到 `infra_job_log`
- 任务状态：运行 / 停止

---

**文档版本**：v1.0
**最后更新**：2026-07-13
