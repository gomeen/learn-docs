# 5.6 流程超时与催办

> 深入理解 BPMN 中的"超时处理"和 ruoyi 的"催办"机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"任务超时"（Task Timeout）和"流程超时"（Process Timeout）
- 知道 ruoyi 中"超时处理"和"催办"的实现方式
- 理解 Flowable 的 `BoundaryEvent` + `TimerEventDefinition` 用法
- 能在 BPMN 中配置超时

## 📚 前置知识

- 监听器（详见 [监听器](./24-listener.md)）
- 流程变量（详见 [流程变量](./19-process-vars.md)）
- BPMN 定时器事件（详见 [BPMN](./01-bpmn.md)）
- 定时任务（可选，详见 [Scheduled](../02-spring-boot/27-scheduled.md)）

## 1. 核心概念

### 1.1 两种超时

| 类型 | 含义 | 实现 |
|------|------|------|
| **任务超时** | 某个 UserTask 在指定时间内未完成 | Flowable Boundary Timer + TaskListener |
| **流程超时** | 整个流程在指定时间内未结束 | Flowable Timer Start Event / 中间 Timer |
| **催办** | 任务接近超时，发提醒给 assignee | 定时任务扫描 + 消息推送 |

### 1.2 Flowable 的 Boundary Timer

```xml
<userTask id="approve" name="审批">
    <!-- 边界定时器：3 天后超时 -->
    <boundaryEvent id="timeout" attachedToRef="approve">
        <timerEventDefinition>
            <timeDuration>P3D</timeDuration>  <!-- ISO 8601 Duration: 3 days -->
        </timerEventDefinition>
    </boundaryEvent>
</userTask>
```

**作用**：3 天后未完成，触发定时器事件（可配置自动通过/拒绝/跳转）。

### 1.3 ruoyi 的超时处理

ruoyi 在 `BpmnModelConstants` 中定义了 `USER_TASK_TIMEOUT_HANDLER_TYPE`：
- `TIMEOUT_AUTO_APPROVE`：超时自动通过
- `TIMEOUT_AUTO_REJECT`：超时自动拒绝
- `TIMEOUT_AUTO_ASSIGN`：超时转给其他人

### 1.4 ruoyi 的催办

**催办** = 单独的业务概念，**不是 BPMN 标准元素**。

实现：
- 定时任务（`@Scheduled`）每天扫描 `act_ru_task`
- 对"接近超时"的任务发通知
- 记录在 `bpm_task_timeout_log` 表

## 2. 代码示例

### 2.1 BPMN 配置任务超时

```xml
<userTask id="approve" name="审批">
    <extensionElements>
        <flowable:property name="timeoutHandlerType" value="AUTO_REJECT"/>
    </extensionElements>

    <boundaryEvent id="timeout" attachedToRef="approve">
        <timerEventDefinition>
            <timeDuration>P3D</timeDuration>
        </timerEventDefinition>
        <sequenceFlow targetRef="timeoutEnd"/>
    </boundaryEvent>
</userTask>
```

### 2.2 启动时设置"提醒时间"变量

```java
Map<String, Object> variables = new HashMap<>();
variables.put("reminderHours", 24);  // 24 小时后提醒
variables.put("timeoutHours", 72);   // 72 小时后超时
ProcessInstance pi = runtimeService.startProcessInstanceByKey("leave", variables);
```

### 2.3 常见错误：timeDuration 写错

```xml
<!-- ❌ 错误：写成"3 days"（Flowable 不识别） -->
<timeDuration>3 days</timeDuration>

<!-- ✅ 正确：ISO 8601 Duration 格式 -->
<timeDuration>P3D</timeDuration>  <!-- 3 天 -->
<timeDuration>PT12H</timeDuration>  <!-- 12 小时 -->
<timeDuration>PT30M</timeDuration>  <!-- 30 分钟 -->
```

## 3. 关键要点总结

- 任务超时 = BPMN Boundary Timer + ExtensionElement 配置
- 流程超时 = BPMN 中间 Timer Event
- 催办 = 业务层 `@Scheduled` + 消息推送（**BPMN 不管**）
- timeDuration 必须用 ISO 8601 格式（P3D、PT12H）
- ruoyi 通过扩展属性 `timeoutHandlerType` 控制超时处理动作
- Flowable 内置 `Job` 也支持定时，但 ruoyi 用 Spring `@Scheduled` 更简单

---

**文档版本**：v1.0
**最后更新**：2026-07-13
