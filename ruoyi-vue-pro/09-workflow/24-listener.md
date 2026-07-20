# 5.4 流程监听器

> 深入理解 BPMN 中的"监听器"机制：ExecutionListener、TaskListener 及 ruoyi 的应用。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"执行监听器"（ExecutionListener）和"任务监听器"（TaskListener）
- 知道监听器的常用事件：start、end、take、create、complete
- 理解 ruoyi 在哪些地方用监听器
- 能在 BPMN 中配置监听器

## 📚 前置知识

- BPMN 基础（详见 [BPMN](./01-bpmn.md)）
- 事件类型（详见 [Flowable 概念](./02-flowable-concepts.md)）
- ruoyi 扩展（详见 [ruoyi 工作流](./03-ruoyi-workflow.md)）
- Spring Event（可选，详见 [Spring Event](../02-spring-boot/05-event.md)）

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

## 3. 关键要点总结

- 两种监听器：ExecutionListener（流程级）、TaskListener（任务级）
- ruoyi 在两个层级使用：全局监听器 + BPMN 元素级
- 全局监听器用 `AbstractFlowableEngineEventListener`
- 监听器异常**不抛出去**（只 log），避免影响流程
- 监听器只做"路由"，业务逻辑委托给 Service

---

**文档版本**：v1.0
**最后更新**：2026-07-13
