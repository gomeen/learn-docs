# 6.3 定时任务：XXL-Job 集成

> 掌握 yudao 定时任务的实现（基于 XXL-Job + Quartz），能开发分布式定时任务。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 yudao 定时任务的设计
- 掌握 XXL-Job 与 Quartz 的区别
- 能用 `@JobHandler` 开发定时任务
- 了解多租户在定时任务中的处理

## 📚 前置知识

- Spring Scheduling
- Quartz 基础
- 分布式定时任务概念

## 1. 核心概念

### 1.1 yudao 的双定时任务方案

yudao 同时支持两种定时任务：
- **Quartz**：本地集群化（基于数据库锁）
- **XXL-Job**：分布式（需要 XXL-Job Admin）

### 1.2 核心组件

| 组件 | 作用 |
|------|------|
| `JobHandler` | 任务接口（业务方实现） |
| `JobHandlerInvoker` | 反射调用 JobHandler |
| `SchedulerManager` | Quartz 管理 |
| `CronUtils` | Cron 表达式工具 |
| `TenantJobAspect` | 多租户传递 |

## 2. 代码示例

### 2.1 实现一个 JobHandler

```java
@Component
public class OrderTimeoutJob implements JobHandler {
    @Resource
    private OrderService orderService;

    @Override
    public String execute(String param) throws Exception {
        // 查询超时订单
        List<OrderDO> timeoutOrders = orderService.getTimeoutOrders();
        for (OrderDO order : timeoutOrders) {
            orderService.closeOrder(order.getId());
        }
        return "处理完成，处理订单数: " + timeoutOrders.size();
    }
}
```

### 2.2 注册到 yudao

在 `application.yml` 配置：

```yaml
yudao:
  job:
    enable: true
    core-pool-size: 10
```

### 2.3 XXL-Job 任务

```java
@JobHandler("orderTimeoutJob")
@Component
public class OrderTimeoutXxlJob {
    @XxlJob("orderTimeoutJob")
    public void execute() {
        // XXL-Job 执行
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 JobHandler 接口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-job/src/main/java/cn/iocoder/yudao/framework/quartz/core/handler/JobHandler.java`
**核心代码**：

```java
public interface JobHandler {
    /**
     * 执行任务
     *
     * @param param 任务参数
     * @return 执行结果
     */
    String execute(String param) throws Exception;
}
```

### 3.2 JobHandlerInvoker（反射调用）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-job/src/main/java/cn/iocoder/yudao/framework/quartz/core/handler/JobHandlerInvoker.java`

```java
public class JobHandlerInvoker implements Job {
    private final JobHandler jobHandler;
    private final String jobName;

    @Override
    public void execute(JobExecutionContext context) {
        // 1. 反射调用 jobHandler.execute(param)
        // 2. 记录日志
        // 3. 处理异常
    }
}
```

### 3.3 Quartz 集成

```java
@AutoConfiguration
public class YudaoQuartzAutoConfiguration {
    @Bean
    public SchedulerFactoryBean schedulerFactoryBean(JobHandlerInvoker invoker) {
        SchedulerFactoryBean factory = new SchedulerFactoryBean();
        // 配置 JobFactory、DataSource 等
        return factory;
    }
}
```

### 3.4 TenantJobAspect（多租户）

```java
@Aspect
@Component
public class TenantJobAspect {
    @Around("@annotation(org.springframework.scheduling.annotation.Scheduled)")
    public Object around(ProceedingJoinPoint point) throws Throwable {
        // 1. 遍历所有租户
        for (Long tenantId : tenantApi.getTenantIds()) {
            // 2. 设置租户上下文
            TenantContextHolder.setTenantId(tenantId);
            try {
                // 3. 执行任务
                return point.proceed();
            } finally {
                TenantContextHolder.clear();
            }
        }
    }
}
```

**解读**：
- **多租户定时任务**：遍历所有租户，每个租户都执行一次
- 通过 AOP 实现，**业务方无感**

## 4. 关键要点总结

- **yudao 同时支持 Quartz + XXL-Job**
- **`JobHandler` 接口** 是业务方入口
- **`@Scheduled` + `@TenantJobAspect`** 实现多租户定时任务
- **XXL-Job** 适合分布式场景

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中找到 3 个 `JobHandler` 实现，理解其结构。

### 练习 2：进阶

实现一个"订单超时关闭"任务：每分钟扫描超时订单并关闭。

### 练习 3：挑战（选做）

集成 XXL-Job Admin，实现任务的动态创建、暂停、恢复。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-job/`
- XXL-Job 文档：https://www.xuxueli.com/xxl-job/
- Quartz 文档：http://www.quartz-scheduler.org/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
