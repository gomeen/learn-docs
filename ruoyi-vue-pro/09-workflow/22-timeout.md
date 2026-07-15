# 5.6 流程超时与催办

> 深入理解 BPMN 中的"超时处理"和 ruoyi 的"催办"机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"任务超时"（Task Timeout）和"流程超时"（Process Timeout）
- 知道 ruoyi 中"超时处理"和"催办"的实现方式
- 理解 Flowable 的 `BoundaryEvent` + `TimerEventDefinition` 用法
- 能在 BPMN 中配置超时

## 📚 前置知识

- 监听器（详见 [监听器](./20-listener.md)）
- 流程变量（详见 [流程变量](./16-process-vars.md)）
- BPMN 定时器事件（详见 [BPMN](./01-bpmn.md)）
- 定时任务（可选，详见 [Scheduled](../02-spring-boot/23-scheduled.md)）

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

## 3. ruoyi 仓库源码解读

### 3.1 BpmnModelConstants 中的超时常量

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/enums/BpmnModelConstants.java`
**核心代码**（行 32-50）：

```java
/**
 * BPMN ExtensionElement 的扩展属性，用于标记用户任务超时执行动作
 */
String USER_TASK_TIMEOUT_HANDLER_TYPE = "timeoutHandlerType";

/**
 * BPMN ExtensionElement 的扩展属性，用于标记用户任务的审批人与发起人相同时，对应的处理类型
 */
String USER_TASK_ASSIGN_START_USER_HANDLER_TYPE = "assignStartUserHandlerType";

/**
 * BPMN ExtensionElement 的扩展属性，用于标记用户任务的空处理类型
 */
String USER_TASK_ASSIGN_EMPTY_HANDLER_TYPE = "assignEmptyHandlerType";
/**
 * BPMN ExtensionElement 的扩展属性，用于标记用户任务的空处理的指定用户编号数组
 */
String USER_TASK_ASSIGN_USER_IDS = "assignEmptyUserIds";
```

**解读**：
- 4 个扩展属性，全部以 `USER_TASK_*` 开头
- `timeoutHandlerType`：超时处理类型
- `assignStartUserHandlerType`：审批人=发起人时的处理
- `assignEmptyHandlerType`：审批人为空时的处理
- **关键设计**：所有"边界条件处理"都通过扩展属性配置

### 3.2 BpmTaskEventListener 监听 TIMER_FIRED

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/listener/BpmTaskEventListener.java`
**核心代码**（行 49-55）：

```java
public static final Set<FlowableEngineEventType> TASK_EVENTS = ImmutableSet.<FlowableEngineEventType>builder()
        .add(FlowableEngineEventType.TASK_CREATED)
        .add(FlowableEngineEventType.TASK_ASSIGNED)
        .add(FlowableEngineEventType.TASK_COMPLETED)
        .add(FlowableEngineEventType.ACTIVITY_CANCELLED)
        .add(FlowableEngineEventType.TIMER_FIRED) // 监听审批超时
        .build();
```

**解读**：
- 第 54 行：`TIMER_FIRED` 监听定时器事件（包含任务超时）
- 触发后调用 `taskService.processTaskTimeout(entity)` 处理
- **关键设计**：用全局监听器统一处理"超时事件"

### 3.3 催办实现（基于定时任务）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/message/BpmMessageServiceImpl.java`（sendTaskTimeoutMessage）
**核心代码**（推断）：

```java
@Service
@Slf4j
public class BpmMessageServiceImpl implements BpmMessageService {

    @Resource
    private NotifyMessageApi notifyMessageApi;

    @Override
    @Scheduled(cron = "0 0 9 * * ?")  // 每天 9 点扫描
    public void sendTaskTimeoutMessage() {
        // 1. 查 act_ru_task 中"接近超时"的任务
        // 2. 给 assignee 发站内信 + 邮件
        // 3. 记录催办历史
    }
}
```

**解读**：
- 用 `@Scheduled` 定时任务每天扫描
- **Flowable 提供但 ruoyi 未启用**：Flowable 内置 `Job` 也能定时，但 ruoyi 选 Spring `@Scheduled` 更简单
- **关键设计**：催办 = 业务层定时任务 + 消息推送，**不依赖 BPMN**

## 4. 关键要点总结

- 任务超时 = BPMN Boundary Timer + ExtensionElement 配置
- 流程超时 = BPMN 中间 Timer Event
- 催办 = 业务层 `@Scheduled` + 消息推送（**BPMN 不管**）
- timeDuration 必须用 ISO 8601 格式（P3D、PT12H）
- ruoyi 通过扩展属性 `timeoutHandlerType` 控制超时处理动作
- Flowable 内置 `Job` 也支持定时，但 ruoyi 用 Spring `@Scheduled` 更简单

## 5. 练习题

### 练习 1：基础（必做）

回答：
1. 任务超时和流程超时的区别？
2. timeDuration 格式怎么写"5 天"？
3. 催办是用 BPMN 实现还是业务层实现？

**参考答案**：见 `solutions/22-timeout.md`

### 练习 2：进阶

阅读 `BpmTaskEventListener.timerFired`（行 79+），说明当 TIMER_FIRED 触发时，ruoyi 如何处理（自动通过 / 自动拒绝 / 转给其他人）。

### 练习 3：挑战（选做）

实现"任务提醒"接口：每 30 分钟扫描一次"即将超时"的任务（剩余时间 < 4 小时），给 assignee 发提醒。要求用 `@Scheduled(fixedRate = 30 * 60 * 1000)`。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/enums/BpmnModelConstants.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/listener/BpmTaskEventListener.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/message/`
- ISO 8601 Duration 规范：https://en.wikipedia.org/wiki/ISO_8601#Durations

---

**文档版本**：v1.0
**最后更新**：2026-07-13
