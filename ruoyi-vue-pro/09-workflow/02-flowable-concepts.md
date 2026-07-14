# 1.2 Flowable 核心概念

> 掌握 Flowable 引擎的核心对象、Service API 与表结构，能定位到 ruoyi 集成的具体类。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 ProcessEngine、RepositoryService、RuntimeService、TaskService、HistoryService 五大服务
- 理解 Deployment、ProcessDefinition、ProcessInstance、Task、Execution、HistoricProcessInstance 之间的关系
- 掌握 Flowable 内置的核心表（ACT_RE_*、ACT_RU_*、ACT_HI_*、ACT_ID_*、ACT_GE_*）作用
- 能读懂 ruoyi 中调用 Flowable 服务的代码

## 📚 前置知识

- 01-bpmn.md（BPMN 2.0 基础）
- Spring Bean / 依赖注入
- 关系型数据库基础（表、主外键）

## 1. 核心概念

### 1.1 五大 Service

| Service | 中文名 | 职责 | 常用方法 |
|---------|-------|------|---------|
| `RepositoryService` | 仓库服务 | 流程定义、部署、查询 | `createDeployment()`、`createProcessDefinitionQuery()` |
| `RuntimeService` | 运行时服务 | 启动流程、读运行时变量、操作执行 | `startProcessInstanceByKey()`、`getVariable()` |
| `TaskService` | 任务服务 | 我的任务、完成任务、转办 | `createTaskQuery()`、`complete()`、`addCandidateUser()` |
| `HistoryService` | 历史服务 | 已完成实例、节点历史 | `createHistoricProcessInstanceQuery()` |
| `ManagementService` | 管理服务 | 作业管理、数据库表 | `createJobQuery()` |

**关系图**：

```
ProcessEngine（流程引擎：所有 Service 的容器）
  ├─ RepositoryService   ── 静态资源（流程定义、部署包）
  ├─ RuntimeService      ── 运行时状态（执行流、变量）
  ├─ TaskService         ── 用户任务（待办、已办）
  ├─ HistoryService      ── 历史归档（完成后归档）
  └─ ManagementService   ── 后台作业（定时器、异步）
```

### 1.2 核心对象生命周期

```
[开发者] 部署 .bpmn20.xml
   ↓
[RepositoryService] Deployment（部署对象）
   ↓ 解析后
ProcessDefinition（流程定义，可被多次启动）
   ↓ 启动
[RuntimeService] startProcessInstanceByKey(...)
   ↓
ProcessInstance（流程实例 1 次申请 = 1 个实例）
   ├─ Execution（执行流，可能有多个：并行分支）
   └─ Task（用户任务，UserTask 时产生）
   ↓ 流程完成
[HistoryService] HistoricProcessInstance（历史归档）
```

### 1.3 Flowable 表前缀

| 前缀 | 含义 | 例子 |
|------|------|------|
| `ACT_RE_*` | REpository 仓库（流程定义、部署） | `ACT_RE_DEPLOYMENT`、`ACT_RE_PROCDEF` |
| `ACT_RU_*` | RUntime 运行时（执行、任务、变量） | `ACT_RU_TASK`、`ACT_RU_VARIABLE` |
| `ACT_HI_*` | HIstory 历史（完成的实例、节点） | `ACT_HI_PROCINST`、`ACT_HI_ACTINST` |
| `ACT_GE_*` | GEneral 通用（二进制、表结构） | `ACT_GE_BYTEARRAY` |
| `ACT_ID_*` | IDentity 身份（用户/组，可选） | `ACT_ID_USER`（ruoyi 不用 Flowable 自带身份） |

## 2. 代码示例

### 2.1 部署 + 启动 + 完成任务（最小闭环）

```java
// 1. 部署流程
Deployment deploy = repositoryService.createDeployment()
        .addClasspathResource("processes/leave.bpmn20.xml")
        .name("请假流程")
        .deploy();

// 2. 启动流程实例
ProcessInstance pi = runtimeService.startProcessInstanceByKey("leave",
        Map.of("startUserId", 1L, "days", 3));

// 3. 查询张三的待办
List<Task> tasks = taskService.createTaskQuery()
        .taskAssignee("1")
        .processInstanceId(pi.getId())
        .list();

// 4. 完成任务
taskService.complete(tasks.get(0).getId(),
        Map.of("approveResult", "agree"));
```

**说明**：四行核心代码串起"部署 → 启动 → 查询 → 完成"的完整生命周期。

### 2.2 常见错误：把 `taskService` 当成 `runtimeService`

```java
// ❌ 错误：用 TaskService 启动流程（TaskService 没有 start 方法）
taskService.startProcessInstanceByKey("leave");  // 编译报错

// ✅ 正确：启动流程属于运行时服务
runtimeService.startProcessInstanceByKey("leave");
```

### 2.3 常见错误：忘记释放 `historicProcessInstance`

```java
// ❌ 错误：频繁查询历史表导致数据库压力大
for (int i = 0; i < 1000; i++) {
    HistoricProcessInstance hi = historyService
        .createHistoricProcessInstanceQuery()
        .processInstanceId(id)
        .singleResult();
    // ... 用完未处理
}

// ✅ 正确：配合 PageResult 批量查询，并设置超时清理策略
// ruoyi 中通过 deleteHistoricData 等定时任务清理
```

## 3. ruoyi 仓库源码解读

### 3.1 BpmTaskServiceImpl 注入多个 Flowable Service

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmTaskServiceImpl.java`
**核心代码**（行 76-100）：

```java
/**
 * 流程任务实例 Service 实现类
 *
 * @author 芋道源码
 * @author jason
 */
@Service
@Validated
@Slf4j
public class BpmTaskServiceImpl implements BpmTaskService {

    @Resource
    private TaskService taskService;        // Flowable 任务服务
    @Resource
    private HistoryService historyService;  // Flowable 历史服务
    @Resource
    private RuntimeService runtimeService;  // Flowable 运行时服务
    @Resource
    private ManagementService managementService; // Flowable 管理服务

    @Resource
    private BpmProcessInstanceService processInstanceService;
    @Resource
    private BpmProcessDefinitionService processDefinitionService;
    // ... 其他业务依赖
}
```

**解读**：
- 第 87-90 行：直接注入 4 个 Flowable 官方 Service，**与 Flowable 深度集成**
- 第 88 行：`HistoryService` 用于查询已完成的审批历史
- 第 89 行：`RuntimeService` 用于读取流程变量、触发信号
- 第 90 行：`ManagementService` 用于管理定时任务（催办）
- **关键设计**：ruoyi 的"业务层"和"Flowable 层"通过 `@Resource` 注入组合在一起，但业务逻辑封装在自己的 Service 中

### 3.2 BpmProcessInstanceServiceImpl 启动流程

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmProcessInstanceServiceImpl.java`
**核心代码**（行 80-90）：

```java
import org.flowable.engine.HistoryService;
import org.flowable.engine.RuntimeService;
import org.flowable.engine.history.HistoricActivityInstance;
import org.flowable.engine.history.HistoricProcessInstance;
import org.flowable.engine.history.HistoricProcessInstanceQuery;
import org.flowable.engine.repository.ProcessDefinition;
import org.flowable.engine.runtime.Execution;
import org.flowable.engine.runtime.ProcessInstance;
import org.flowable.engine.runtime.ProcessInstanceBuilder;
import org.flowable.engine.task.Attachment;
import org.flowable.task.api.Task;
import org.flowable.task.api.history.HistoricTaskInstance;
```

**解读**：
- 这只是**import 段**（行 80-90），但展示了 ruoyi 业务代码会同时操作多种 Flowable 核心对象
- `ProcessInstanceBuilder` 是 Flowable 6.4+ 提供的**链式启动器**，ruoyi 用它来传变量、设置发起人
- `HistoricActivityInstance` 用于流程图高亮追踪
- **关键设计**：ruoyi 把这些 API 集中到 `BpmProcessInstanceServiceImpl` 中，Controller 层不直接调用 Flowable

## 4. 关键要点总结

- **五大 Service**：Repository（部署） / Runtime（运行时） / Task（待办） / History（历史） / Management（作业）
- **核心对象**：Deployment → ProcessDefinition → ProcessInstance → Task → HistoricProcessInstance
- **表前缀**：RE 仓库、RU 运行时、HI 历史、GE 通用
- ruoyi 在自己的 `*ServiceImpl` 中调用 Flowable 官方 Service，**通过 `@Resource` 注入**
- 启动流程用 `RuntimeService.startProcessInstanceByKey()`，完成任务用 `TaskService.complete()`

## 5. 练习题

### 练习 1：基础（必做）

回答下列问题：
1. 部署流程定义用哪个 Service？
2. 查询"我的待办"用哪个 Service？
3. 查看"已结束的流程"用哪个 Service？

**参考答案**：见 `solutions/02-flowable-concepts.md`

### 练习 2：进阶

阅读 `BpmTaskServiceImpl` 第 80-100 行附近的代码，找到它的 `completeTask` 方法。说明该方法涉及的 Flowable Service 至少有几个？分别完成什么动作？

### 练习 3：挑战（选做）

启动 ruoyi 的本地开发环境（参考其 `docker-compose.yml`），登录后随便触发一个流程，然后查询数据库：
```sql
SELECT * FROM act_ru_task;
SELECT * FROM act_ru_variable;
```
观察每张表里产生了什么数据。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmTaskServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmProcessInstanceServiceImpl.java`
- Flowable 用户手册：https://www.flowable.com/open-source/docs/
- Flowable Javadoc：https://www.flowable.com/open-source/docs/javadoc/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
