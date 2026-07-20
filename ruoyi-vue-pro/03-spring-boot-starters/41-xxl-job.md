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

## 3. 关键要点总结

- **yudao 同时支持 Quartz + XXL-Job**
- **`JobHandler` 接口** 是业务方入口
- **`@Scheduled` + `@TenantJobAspect`** 实现多租户定时任务
- **XXL-Job** 适合分布式场景

---

**文档版本**：v1.0
**最后更新**：2026-07-13
