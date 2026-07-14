# 6.2 流程图高亮追踪

> 理解 BPMN 中"流程图高亮追踪"的实现：用历史节点回放流程状态。

## 🎯 学习目标

完成本文档后，你将能够：
- 知道"流程图追踪"的业务场景
- 理解 `HistoricActivityInstance` 表的查询方式
- 掌握 ruoyi 在审批详情页中拼接"已完成节点 / 当前节点 / 待办节点"的方法
- 能用 Flowable API 拿到流程的"当前状态"

## 📚 前置知识

- 13-task-query.md（任务查询）
- 02-flowable-concepts.md（HistoryService）
- 01-bpmn.md（BPMN 节点）

## 1. 核心概念

### 1.1 流程图高亮追踪的两种状态

| 状态 | 来源 | 含义 |
|------|------|------|
| **已完成节点** | `act_hi_actinst` | 已经执行过的节点（绿色） |
| **当前节点** | `act_ru_task` / `act_ru_execution` | 正在执行的节点（黄色） |
| **未来节点** | BPMN XML 解析 | 还未执行的节点（灰色） |

### 1.2 实现思路

```
[审批详情页] /bpm/process-instance/detail?id=xxx
   ↓ 后端查询
1. BpmnModel bpmnModel = repositoryService.getBpmnModel(processDefinitionId);
   // 拿到完整 BPMN 模型（含所有节点）
2. List<HistoricActivityInstance> finished = historyService
       .createHistoricActivityInstanceQuery()
       .processInstanceId(piId)
       .finished()
       .list();
   // 历史已完成节点
3. List<Task> currentTasks = taskService.createTaskQuery()
       .processInstanceId(piId)
       .list();
   // 当前活跃任务
4. 组装为 Map<String, NodeStatus>：
   - 节点 ID → 已完成/进行中/未来
5. 返回给前端，前端用 bpmn.js 高亮
```

### 1.3 ruoyi 的 `BpmApprovalDetailRespVO`

ruoyi 把流程追踪信息封装为 VO：
- 流程基本信息
- 流程变量
- 节点状态列表
- 审批历史
- 当前用户可执行的操作

## 2. 代码示例

### 2.1 查询历史节点

```java
List<HistoricActivityInstance> activities = historyService
    .createHistoricActivityInstanceQuery()
    .processInstanceId(piId)
    .finished()  // 只查已完成的
    .orderByHistoricActivityInstanceStartTime().asc()
    .list();
```

### 2.2 查询当前活跃任务

```java
List<Task> currentTasks = taskService.createTaskQuery()
    .processInstanceId(piId)
    .active()
    .list();
```

### 2.3 拼装节点状态

```java
// 简化版：构建 activityId -> status 映射
Map<String, String> nodeStatus = new HashMap<>();
// 已完成节点 → "FINISHED"
finishedActivities.forEach(a -> nodeStatus.put(a.getActivityId(), "FINISHED"));
// 当前节点 → "RUNNING"
currentTasks.forEach(t -> nodeStatus.put(t.getTaskDefinitionKey(), "RUNNING"));
// 其他节点（来自 BpmnModel） → "WAITING"
```

### 2.4 常见错误：忽略并行分支的状态

```java
// ❌ 错误：只查主流程节点，忽略并行分支
List<HistoricActivityInstance> list = historyService.createHistoricActivityInstanceQuery()
    .processInstanceId(piId)
    .list();  // 包含所有分支的节点

// ✅ 正确：需要按 activityType 区分
List<HistoricActivityInstance> userTasks = historyService.createHistoricActivityInstanceQuery()
    .processInstanceId(piId)
    .activityType("userTask")  // 只看 UserTask
    .list();
```

## 3. ruoyi 仓库源码解读

### 3.1 BpmProcessInstanceServiceImpl 中导入的 API

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmProcessInstanceServiceImpl.java`
**核心代码**（行 47-60）：

```java
import org.flowable.bpmn.constants.BpmnXMLConstants;
import org.flowable.bpmn.model.*;
import org.flowable.engine.HistoryService;
import org.flowable.engine.RuntimeService;
import org.flowable.engine.history.HistoricActivityInstance;
import org.flowable.engine.history.HistoricProcessInstance;
import org.flowable.engine.history.HistoricProcessInstanceQuery;
import org.flowable.engine.repository.ProcessDefinition;
import org.flowable.engine.runtime.Execution;
import org.flowable.engine.runtime.ProcessInstance;
import org.flowable.engine.runtime.ProcessInstanceBuilder;
```

**解读**：
- `HistoricActivityInstance`：用于追踪历史节点
- `ProcessInstanceBuilder`：用于启动流程
- 这些 import 表明 ruoyi 的服务会**深入操作多个 Flowable 核心对象**

### 3.2 BpmApprovalDetailRespVO：审批详情 VO

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/task/vo/instance/BpmApprovalDetailRespVO.java`（基于命名推断）
**核心字段**（推断）：

```java
@Schema(description = "管理后台 - 审批详情 Response VO")
@Data
public class BpmApprovalDetailRespVO {
    @Schema(description = "流程实例")
    private ProcessInstance processInstance;

    @Schema(description = "流程定义")
    private ProcessDefinition processDefinition;

    @Schema(description = "流程变量")
    private Map<String, Object> processVariables;

    @Schema(description = "活动节点任务列表")
    private List<ActivityNodeTask> activityNodeTasks;

    @Data
    public static class ActivityNode {
        private String id;
        private String name;
        private String type;  // UserTask / Gateway / Start / End
        private String status;  // FINISHED / RUNNING / WAITING
    }

    @Data
    public static class ActivityNodeTask {
        private String activityId;
        private String assignee;
        private String status;  // FINISHED / RUNNING
        private Date startTime;
        private Date endTime;
    }
}
```

**解读**：
- 嵌套类 `ActivityNode` / `ActivityNodeTask` 表示"节点"和"节点上的任务"
- `status` 三种值：FINISHED / RUNNING / WAITING
- **关键设计**：VO 嵌套结构**贴合前端展示**

### 3.3 流程图的 BPMN 解析

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/util/BpmnModelUtils.java`
**核心代码**（基于 service 通用结构推断）：

```java
/**
 * 获取 BPMN 模型的所有 FlowElement
 */
public static <T extends FlowElement> List<T> getBpmnModelElements(BpmnModel bpmnModel, Class<T> clazz) {
    List<T> result = new ArrayList<>();
    bpmnModel.getMainProcess().getFlowElements().forEach(element -> {
        if (clazz.isInstance(element)) {
            result.add((T) element);
        }
    });
    return result;
}
```

**解读**：
- 第 5 行：遍历所有 FlowElement
- 第 6-9 行：用 `clazz.isInstance` 过滤出指定类型
- **关键设计**：通用方法，**支持所有 FlowElement 子类**

## 4. 关键要点总结

- 流程图追踪 = 已完成节点 + 当前节点 + 未来节点
- 已完成：HistoryService 查 `act_hi_actinst`
- 当前：TaskService 查 `act_ru_task`
- 未来：BPMN XML 解析 + 排除已执行的
- ruoyi 用 `BpmApprovalDetailRespVO` 封装追踪信息（含流程实例、变量、节点状态）
- 前端用 bpmn.js 根据 status 高亮节点

## 5. 练习题

### 练习 1：基础（必做）

回答：
1. 已完成、当前、未来节点分别查哪张表？
2. 节点状态有哪 3 种值？
3. 前端用什么库做高亮？

**参考答案**：见 `solutions/24-trace.md`

### 练习 2：进阶

阅读 `BpmProcessInstanceServiceImpl.getApprovalDetail` 完整实现，列出它拼装"节点状态"的具体步骤。

### 练习 3：挑战（选做）

实现"流程图 JSON"接口：传入 processInstanceId，返回 bpmn.js 渲染所需的 JSON（含每个节点的状态），便于前端直接展示。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmProcessInstanceServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/task/vo/instance/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/util/BpmnModelUtils.java`
- bpmn.js 文档：https://bpmn.io/toolkit/bpmn-js/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
