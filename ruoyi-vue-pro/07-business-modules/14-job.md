# 7.3.2 定时任务

> 理解 ruoyi 中定时任务（Job）的实现，基于 Quartz 调度框架。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 定时任务的工作原理
- 理解 Cron 表达式的使用
- 学会在 ruoyi 中创建自定义定时任务
- 了解 Quartz 调度框架

## 📚 前置知识

- Spring Boot 定时任务（详见 [Scheduled](../02-spring-boot/23-scheduled.md)）
- Cron 表达式语法
- Quartz / XXL-Job 调度（详见 [XXL-Job Starter](../03-spring-boot-starters/34-xxl-job.md)）

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

## 3. ruoyi 仓库源码解读

### 3.1 JobController 核心代码

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/controller/admin/job/JobController.java`

**核心代码**（简化）：

```java
@Tag(name = "管理后台 - 定时任务")
@RestController
@RequestMapping("/infra/job")
@Validated
public class JobController {

    @Resource
    private JobService jobService;

    @PostMapping("/create")
    @PreAuthorize("@ss.hasPermission('infra:job:create')")
    public CommonResult<Long> createJob(@Valid @RequestBody JobSaveReqVO createReqVO) {
        return success(jobService.createJob(createReqVO));
    }

    @PutMapping("/update")
    @PreAuthorize("@ss.hasPermission('infra:job:update')")
    public CommonResult<Boolean> updateJob(@Valid @RequestBody JobSaveReqVO updateReqVO) {
        jobService.updateJob(updateReqVO);
        return success(true);
    }

    @GetMapping("/page")
    @PreAuthorize("@ss.hasPermission('infra:job:query')")
    public CommonResult<PageResult<JobRespVO>> getJobPage(@Valid JobPageReqVO pageVO) {
        return success(jobService.getJobPage(pageVO));
    }

    @PutMapping("/trigger")
    @PreAuthorize("@ss.hasPermission('infra:job:trigger')")
    public CommonResult<Boolean> triggerJob(@RequestParam("id") Long id) {
        jobService.triggerJob(id);
        return success(true);
    }
}
```

### 3.2 JobHandler 注解

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-job/`

```java
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Component
public @interface JobHandler {
    String value() default "";
}
```

### 3.3 任务执行流程

```
1. Quartz 调度器根据 Cron 表达式触发
2. 通过 handlerName 找到 JobHandler Bean
3. 调用 IJobHandler.execute(param)
4. 记录执行日志到 infra_job_log
5. 失败时根据 retryCount 重试
```

## 4. 关键要点总结

- ruoyi 定时任务基于 Quartz
- 通过 `@JobHandler` 注解定义任务
- 任务配置存储在 `infra_job` 表
- 支持 Cron 表达式、参数、重试
- 执行日志记录到 `infra_job_log`
- 任务状态：运行 / 停止

## 5. 练习题

### 练习 1：基础（必做）

打开 `JobDO.java`，列出所有字段，理解每个字段的作用。

### 练习 2：进阶

在 ruoyi 仓库中搜索 `@JobHandler` 注解，列出所有内置的定时任务（如订单超时、缓存刷新等）。

### 练习 3：挑战（选做）

设计一个"每日凌晨 3 点清理无效图片"任务，要求支持传入保留天数参数，说明实现步骤。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/controller/admin/job/JobController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-job/`
- Quartz 官方文档：https://www.quartz-scheduler.org/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
