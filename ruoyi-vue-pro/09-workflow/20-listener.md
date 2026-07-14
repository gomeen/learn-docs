# 5.4 流程监听器

> 深入理解 BPMN 中的"监听器"机制：ExecutionListener、TaskListener 及 ruoyi 的应用。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"执行监听器"（ExecutionListener）和"任务监听器"（TaskListener）
- 知道监听器的常用事件：start、end、take、create、complete
- 理解 ruoyi 在哪些地方用监听器
- 能在 BPMN 中配置监听器

## 📚 前置知识

- 01-bpmn.md（BPMN 基础）
- 02-flowable-concepts.md（事件类型）
- 03-ruoyi-workflow.md（ruoyi 扩展）

## 1. 核心概念

### 1.1 两种监听器

| 类型 | 监听对象 | 触发时机 | 用途 |
|------|---------|---------|------|
| **ExecutionListener** | 流程 / 节点执行 | start、end、take | 流程级业务：开始/结束/连线 |
| **TaskListener** | UserTask | create、assignment、complete、delete | 任务级业务：通知、催办 |

### 1.2 ExecutionListener 事件

```java
public interface ExecutionListener {
    String EVENTNAME_START = "start";      // 节点开始
    String EVENTNAME_END = "end";          // 节点结束
    String EVENTNAME_TAKE = "take";        // 离开连线（sequenceFlow）
}
```

**应用场景**：
- start：节点开始时，初始化数据
- end：节点结束时，写业务表
- take：某条连线被激活时

### 1.3 TaskListener 事件

```java
public interface TaskListener {
    String EVENTNAME_CREATE = "create";        // 任务创建
    String EVENTNAME_ASSIGNMENT = "assignment";// 任务分配
    String EVENTNAME_COMPLETE = "complete";    // 任务完成
    String EVENTNAME_DELETE = "delete";        // 任务删除
}
```

**应用场景**：
- create：发送通知给 assignee
- complete：记录审批历史
- assignment：更新审批人信息

### 1.4 ruoyi 的监听器实现

ruoyi 在两个层面使用监听器：
1. **全局监听器**（`BpmTaskEventListener`、`BpmProcessInstanceEventListener`）：监听所有流程
2. **BPMN 元素级监听器**：在 BPMN 中给特定节点配置

## 2. 代码示例

### 2.1 BPMN 配置监听器

```xml
<userTask id="approve" name="审批">
    <extensionElements>
        <!-- 任务创建时调用 Java 类 -->
        <flowable:taskListener event="create"
                               class="cn.iocoder.yudao.module.bpm.framework.flowable.core.listener.demo.MyTaskListener"/>
    </extensionElements>
</userTask>
```

### 2.2 BPMN 配置全局错误处理

```xml
<process id="main" name="主流程">
    <extensionElements>
        <flowable:executionListener event="end"
                                    class="cn.iocoder.yudao.module.bpm.listener.ProcessEndListener"/>
    </extensionElements>
    ...
</process>
```

### 2.3 编写自定义监听器

```java
public class MyTaskListener implements TaskListener {
    @Override
    public void notify(DelegateTask task) {
        // 任务创建时：发通知
        if ("create".equals(task.getEventName())) {
            messageService.sendToUser(task.getAssignee(), "您有新的审批任务");
        }
    }
}
```

### 2.4 常见错误：监听器抛异常影响流程

```java
// ❌ 错误：监听器抛异常会中断流程
public class BadListener implements TaskListener {
    @Override
    public void notify(DelegateTask task) {
        throw new RuntimeException("业务异常");
        // 流程不会继续！
    }
}

// ✅ 正确：监听器只记录日志，不抛异常
public class GoodListener implements TaskListener {
    @Override
    public void notify(DelegateTask task) {
        try {
            // 业务逻辑
        } catch (Exception e) {
            log.error("监听器异常", e);
            // 不抛出去
        }
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 BpmTaskEventListener：任务事件监听

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/listener/BpmTaskEventListener.java`
**核心代码**（行 38-77）：

```java
/**
 * 监听 {@link Task} 的开始与完成
 */
@Component
@Slf4j
public class BpmTaskEventListener extends AbstractFlowableEngineEventListener {

    @Resource
    @Lazy
    private BpmModelService modelService;
    @Resource
    @Lazy
    private BpmTaskService taskService;

    public static final Set<FlowableEngineEventType> TASK_EVENTS = ImmutableSet.<FlowableEngineEventType>builder()
            .add(FlowableEngineEventType.TASK_CREATED)
            .add(FlowableEngineEventType.TASK_ASSIGNED)
            .add(FlowableEngineEventType.TASK_COMPLETED)
            .add(FlowableEngineEventType.ACTIVITY_CANCELLED)
            .add(FlowableEngineEventType.TIMER_FIRED) // 监听审批超时
            .build();

    public BpmTaskEventListener() {
        super(TASK_EVENTS);
    }

    @Override
    protected void taskCreated(FlowableEngineEntityEvent event) {
        Task entity = (Task) event.getEntity();
        FlowableUtils.execute(entity.getTenantId(), () -> taskService.processTaskCreated(entity));
    }
```

**解读**：
- 第 40 行：继承 `AbstractFlowableEngineEventListener`（Flowable 提供的监听器基类）
- 第 49-55 行：注册 5 种事件（创建、分配、完成、取消、定时器）
- 第 64 行：所有事件回调都通过 `FlowableUtils.execute(tenantId, ...)` 包裹，**支持多租户**
- 第 65 行：实际处理委托给 `BpmTaskService`
- **关键设计**：Listener 只做"路由"，业务逻辑在 Service

### 3.2 BpmProcessInstanceEventListener：流程实例监听

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/listener/BpmProcessInstanceEventListener.java`
**核心代码**（行 17-60）：

```java
/**
 * 监听 {@link ProcessInstance} 的状态变更，更新其对应的 status 状态
 */
@Component
public class BpmProcessInstanceEventListener extends AbstractFlowableEngineEventListener {

    public static final Set<FlowableEngineEventType> PROCESS_INSTANCE_EVENTS = ImmutableSet.<FlowableEngineEventType>builder()
            .add(FlowableEngineEventType.PROCESS_CREATED)
            .add(FlowableEngineEventType.PROCESS_COMPLETED)
            .add(FlowableEngineEventType.PROCESS_CANCELLED)
            .build();

    @Resource
    @Lazy
    private BpmProcessInstanceService processInstanceService;

    public BpmProcessInstanceEventListener(){
        super(PROCESS_INSTANCE_EVENTS);
    }

    @Override
    protected void processCreated(FlowableEngineEntityEvent event) {
        ProcessInstance processInstance = (ProcessInstance) event.getEntity();
        FlowableUtils.execute(processInstance.getTenantId(),
                () -> processInstanceService.processProcessInstanceCreated(processInstance));
    }

    @Override
    protected void processCompleted(FlowableEngineEntityEvent event) {
        ProcessInstance processInstance = (ProcessInstance) event.getEntity();
        FlowableUtils.execute(processInstance.getTenantId(),
                () -> processInstanceService.processProcessInstanceCompleted(processInstance));
    }
```

**解读**：
- 第 25-29 行：监听 3 种流程事件
- 第 40-44 行：流程创建时，更新 ruoyi 业务状态（如写入 bpm_oa_leave）
- 第 47-51 行：流程完成时，更新为"已完成"状态
- **关键设计**：用监听器**同步** Flowable 流程状态到 ruoyi 业务表

### 3.3 BpmUserTaskListener：BPMN 元素级监听器示例

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/listener/BpmUserTaskListener.java`
**核心代码**（推断）：

```java
@Component
public class BpmUserTaskListener implements TaskListener {
    @Resource
    private BpmMessageService messageService;

    @Override
    public void notify(DelegateTask task) {
        // create 事件：发送待办通知
        if (EVENTNAME_CREATE.equals(task.getEventName())) {
            messageService.sendTaskAssignedMessage(task);
        }
    }
}
```

**解读**：
- 实现 `TaskListener` 接口
- 监听 `create` 事件
- **关键设计**：BPMN 元素级监听器适合做"特定节点的特定事件"处理

## 4. 关键要点总结

- 两种监听器：ExecutionListener（流程级）、TaskListener（任务级）
- ruoyi 在两个层级使用：全局监听器 + BPMN 元素级
- 全局监听器用 `AbstractFlowableEngineEventListener`
- 监听器异常**不抛出去**（只 log），避免影响流程
- 监听器只做"路由"，业务逻辑委托给 Service

## 5. 练习题

### 练习 1：基础（必做）

回答：
1. ExecutionListener 和 TaskListener 的区别？
2. 监听器能抛异常吗？为什么？
3. ruoyi 的全局监听器监听哪 5 种事件？

**参考答案**：见 `solutions/20-listener.md`

### 练习 2：进阶

阅读 `BpmProcessInstanceEventListener.processCancelled`，解释当流程被取消时，ruoyi 如何处理"未结束"的子流程。

### 练习 3：挑战（选做）

写一个监听器：监听 `PROCESS_COMPLETED` 事件，流程结束后发送通知给发起人。提示：发起人 = `runtimeService.getVariable(piId, "PROCESS-INSTANCE-VARIABLE-START-USER-ID")`。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/listener/BpmTaskEventListener.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/listener/BpmProcessInstanceEventListener.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/listener/`
- Flowable 监听器文档：https://www.flowable.com/open-source/docs/javadoc/org/flowable/engine/delegate/TaskListener.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
