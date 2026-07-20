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

## 3. 关键要点总结

- ruoyi 的 BPM 模块结构清晰：**controller / service / dal / framework** 四层
- `framework/flowable/core/` 是"扩展四件套"：Behavior、Listener、Candidate、Util
- 用户/角色/部门**复用 system 模块**，不依赖 Flowable 自带 `ACT_ID_*` 表
- **核心扩展**：`BpmUserTaskActivityBehavior`（审批人分配）+ `BpmTaskEventListener`（任务事件）
- 任何 Flowable 集成都应走 ruoyi 的 `*ServiceImpl`，**避免直接调 Flowable API**（否则失去事件监听、消息通知）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
