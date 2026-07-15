# 1.3 ruoyi 工作流架构

> 理解 ruoyi-vue-pro 中 BPM 模块的目录结构、与 system 模块的协作关系、核心设计思想。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 yudao-module-bpm 模块的目录组织（controller/service/dal/framework）
- 理解 ruoyi 工作流与"系统用户/部门"模块的集成方式
- 识别 ruoyi 工作流的"扩展点"：candidate 策略、listener、behavior
- 能快速定位某个功能（例如"查询待办"）对应的 ruoyi 文件

## 📚 前置知识

- Flowable Service/对象（详见 [Flowable 概念](./02-flowable-concepts.md)）
- Spring Boot 模块化（详见 [模块结构](../07-business-modules/01-module-structure.md)）
- Controller / Service / DAO 三层（详见 [MVC 分层](../07-business-modules/02-mvc-layers.md)）

## 1. 核心概念

### 1.1 ruoyi 工作流模块概览

**模块位置**：`yudao-module-bpm/`

```
yudao-module-bpm/
├── pom.xml                          # 依赖 Flowable、Activiti 等
├── src/main/java/cn/iocoder/yudao/module/bpm/
│   ├── controller/                  # REST 接口层
│   │   ├── admin/                   # 管理后台
│   │   │   ├── definition/          # 流程定义
│   │   │   ├── task/                # 任务（待办、已办、实例）
│   │   │   ├── oa/                  # OA 示例（请假、报销）
│   │   │   └── comment/             # 评论/批注
│   │   └── app/                     # 用户前台
│   ├── service/                     # 业务层
│   │   ├── definition/              # 流程定义
│   │   ├── task/                    # 任务/实例
│   │   ├── message/                 # 消息（待办通知）
│   │   ├── oa/                      # OA 示例
│   │   └── comment/                 # 评论
│   ├── dal/                         # 数据访问
│   │   ├── mysql/                   # MyBatis Mapper
│   │   ├── redis/                   # Redis DAO
│   │   └── dataobject/              # 数据库表 DO
│   ├── framework/                   # 框架扩展
│   │   ├── flowable/                # Flowable 深度集成
│   │   │   ├── config/              # Flowable 配置类
│   │   │   └── core/                # 行为、监听器、候选人策略
│   │   └── web/                     # Web 配置
│   ├── convert/                     # DO/VO 转换
│   ├── api/                         # 对外暴露的 API（供其他模块调用）
│   └── enums/                       # 枚举（流程状态、节点类型等）
└── src/main/resources/
    ├── application-bpm.yaml         # 模块配置
    ├── processes/                   # 内置流程 XML（请假示例等）
    └── mapper/                      # MyBatis XML
```

### 1.2 ruoyi 工作流的"扩展四件套"

ruoyi 在 `framework/flowable/core/` 下扩展了 Flowable 的核心能力：

| 扩展点 | 目录 | 作用 |
|--------|-----|------|
| **Behavior** | `core/behavior/` | 自定义节点行为（如审批人分配、并行多实例） |
| **Listener** | `core/listener/` | 事件监听（任务创建/完成、超时） |
| **Candidate** | `core/candidate/` | 审批人候选策略（指定用户、角色、部门、发起人等） |
| **Util** | `core/util/` | 工具类（BPMN 解析、表单字段提取、HTTP 调用） |

### 1.3 与 system 模块的关系

ruoyi 的工作流**不**使用 Flowable 自带的 `ACT_ID_*` 身份表，而是复用 `yudao-module-system` 的用户/角色/部门表：

```
yudao-module-system           yudao-module-bpm
┌──────────────────┐         ┌──────────────────────┐
│ system_user      │  ←───  │ BpmTaskCandidateStrategy │
│ system_role      │  ←───  │ （通过 roleId 找用户）   │
│ system_dept      │  ←───  │ （通过 deptId 找用户）   │
└──────────────────┘         └──────────────────────┘
```

**调用方式**：通过 `AdminUserApi` / `DeptApi` / `RoleApi`（Feign 远程调用）。

## 2. 代码示例

### 2.1 路由：发起一个请假申请

```java
// 1. 前端调用
POST /admin-api/bpm/process-instance/create
Body: { "processDefinitionKey": "leave", "variables": {"days": 3} }

// 2. 路由到 BpmProcessInstanceController.createProcessInstance
// 3. 调用 BpmProcessInstanceServiceImpl.createProcessInstance
// 4. 内部调用 runtimeService.startProcessInstanceByKey(...)
// 5. 触发 TASK_CREATED 事件 → BpmTaskEventListener.taskCreated
// 6. 监听器内部调用 taskService.processTaskCreated → 发送消息
```

**说明**：一个"发起申请"涉及 6 步链路，ruoyi 把它们**清晰分层**到 controller / service / listener。

### 2.2 候选人策略的扩展

```java
// 文件：framework/flowable/core/candidate/strategy/BpmTaskCandidateUserStrategy.java
// ruoyi 的"指定用户"策略实现 BpmTaskCandidateStrategy 接口
public class BpmTaskCandidateUserStrategy implements BpmTaskCandidateStrategy {

    @Override
    public BpmTaskCandidateStrategyEnum getEnum() {
        return BpmTaskCandidateStrategyEnum.USER;  // 对应前端下拉选项"指定用户"
    }

    @Override
    public Set<Long> calcUsers(String param, String taskDefinitionKey, Long startUserId) {
        // param 是用户在设计器中配置的 userId
        return CollUtil.newHashSet(Long.parseLong(param));
    }
}
```

**说明**：候选人有 7 种策略，每种实现一个类，通过 Spring 注入到 `BpmTaskCandidateInvoker`，由 `BpmTaskCandidateStrategyEnum` 路由。

### 2.3 常见错误：直接调用 Flowable 而绕过 ruoyi 封装

```java
// ❌ 错误：绕过 ruoyi 的 BpmTaskServiceImpl，直接调 Flowable
// 后果：ruoyi 的事件监听、消息通知、候选人策略全部失效
runtimeService.startProcessInstanceByKey("leave");

// ✅ 正确：通过 ruoyi 的 Service 入口
processInstanceService.createProcessInstance(...);
```

## 3. ruoyi 仓库源码解读

### 3.1 BpmModuleConfiguration：Flowable 的核心配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/config/`
**核心代码**（来自 `BpmFlowableConfiguration`）：

```java
/**
 * BPM 模块的配置类
 * 目的：注册 Flowable 引擎相关 Bean，包括：
 * 1. ProcessEngineConfigurationImpl：Flowable 引擎配置
 * 2. 自定义 BehaviorFactory：把 ruoyi 的 BpmUserTaskActivityBehavior 注入
 * 3. 事件监听器：BpmProcessInstanceEventListener / BpmTaskEventListener
 */
@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(BpmFlowableProperties.class)
public class BpmFlowableConfiguration {
    // ...
}
```

**解读**：
- 这是**Flowable 在 ruoyi 中的"启动入口"**
- 关键职责：把 ruoyi 自定义的 `BpmUserTaskActivityBehavior`（候选人分配）注册到 Flowable 引擎
- **关键设计**：用 `@Configuration` 集中管理扩展点，新增 Behavior/Listener 只需在此注册

### 3.2 BpmUserTaskActivityBehavior：核心行为扩展

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/behavior/BpmUserTaskActivityBehavior.java`
**核心代码**（行 31-60）：

```java
/**
 * 自定义的【单个】流程任务的 assignee 负责人的分配
 * 第一步，基于分配规则，计算出分配任务的【单个】候选人。如果找不到，则直接报业务异常，不继续执行后续的流程；
 * 第二步，随机选择一个候选人，则选择作为 assignee 负责人。
 */
@Slf4j
public class BpmUserTaskActivityBehavior extends UserTaskActivityBehavior {

    @Setter
    private BpmTaskCandidateInvoker taskCandidateInvoker;

    public BpmUserTaskActivityBehavior(UserTask userTask) {
        super(userTask);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    protected void handleAssignments(TaskService taskService, String assignee, String owner,
        List<String> candidateUsers, List<String> candidateGroups, TaskEntity task, ExpressionManager expressionManager,
        DelegateExecution execution, ProcessEngineConfigurationImpl processEngineConfiguration) {
        // 第一步，获得任务的候选用户
        Long assigneeUserId = calculateTaskCandidateUsers(execution);
        // 第二步，设置作为负责人
        if (assigneeUserId != null) {
            TaskHelper.changeTaskAssignee(task, String.valueOf(assigneeUserId));
        }
    }
```

**解读**：
- 第 32 行：**继承自 Flowable 官方的 `UserTaskActivityBehavior`**，覆盖 `handleAssignments` 方法
- 第 42 行：`@Transactional` 保证"计算候选人 + 设置 assignee"在同一事务
- 第 47 行：调用 `calculateTaskCandidateUsers`（下方方法）按候选人策略计算
- 第 50 行：随机选一个候选人作为最终 assignee
- **关键设计**：通过继承官方 Behavior，**拦截 Flowable 任务创建流程**，插入 ruoyi 的业务规则。这是经典的"模板方法模式"应用

### 3.3 BpmTaskEventListener：核心事件监听

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/listener/BpmTaskEventListener.java`
**核心代码**（行 33-77）：

```java
/**
 * 监听 {@link Task} 的开始与完成
 */
@Component
@Slf4j
public class BpmTaskEventListener extends AbstractFlowableEngineEventListener {

    @Resource
    @Lazy // 延迟加载，避免循环依赖
    private BpmModelService modelService;
    @Resource
    @Lazy // 解决循环依赖
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
- 第 40 行：继承 `AbstractFlowableEngineEventListener`，**只监听关心的 5 类事件**（行 49-55）
- 第 43 行：`@Lazy` 解决 Listener → Service → Mapper → Listener 的循环依赖
- 第 64 行：每个事件回调都通过 `FlowableUtils.execute(tenantId, ...)` 包裹，**支持多租户**
- 第 65 行：实际处理逻辑委托给 `BpmTaskService`，Listener 只做"事件接收 + 路由"
- **关键设计**：用"事件驱动"把 Flowable 与业务解耦，**新增业务逻辑只需新增 Listener**，不动 Service

## 4. 关键要点总结

- ruoyi 的 BPM 模块结构清晰：**controller / service / dal / framework** 四层
- `framework/flowable/core/` 是"扩展四件套"：Behavior、Listener、Candidate、Util
- 用户/角色/部门**复用 system 模块**，不依赖 Flowable 自带 `ACT_ID_*` 表
- **核心扩展**：`BpmUserTaskActivityBehavior`（审批人分配）+ `BpmTaskEventListener`（任务事件）
- 任何 Flowable 集成都应走 ruoyi 的 `*ServiceImpl`，**避免直接调 Flowable API**（否则失去事件监听、消息通知）

## 5. 练习题

### 练习 1：基础（必做）

阅读 `yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/task/BpmTaskController.java`，列出至少 5 个接口路径（例如 `/my-todo-page`），并说明每个接口的职责。

**参考答案**：见 `solutions/03-ruoyi-workflow.md`

### 练习 2：进阶

解释 `BpmUserTaskActivityBehavior` 中 `@Setter private BpmTaskCandidateInvoker taskCandidateInvoker` 的设计目的：为什么不直接 new，而是用 Setter 注入？这样改如何支持"无候选人抛业务异常"？

### 练习 3：挑战（选做）

新增一个候选人策略 `BpmTaskCandidateFormUserStrategy`：从流程变量 `submitterId` 中读取审批人（用于"提交人自己审批"场景）。要求写出完整类文件、注册到 `BpmTaskCandidateInvoker`、扩展 `BpmTaskCandidateStrategyEnum`。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/behavior/BpmUserTaskActivityBehavior.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/listener/BpmTaskEventListener.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/util/BpmnModelUtils.java`
- ruoyi 官方文档（芋道源码）：https://doc.iocoder.cn/bpm/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
