# 5.5 用户任务分配：候选人/候选组

> 深入理解 BPMN 中"用户任务分配"的 7 种 ruoyi 策略：指定用户、角色、部门、发起人、表达式等。

## 🎯 学习目标

完成本文档后，你将能够：
- 列出 ruoyi 的 7 种候选策略
- 知道每种策略的应用场景
- 理解 `BpmTaskCandidateStrategy` 接口的设计
- 能在 BPMN 中选用合适的策略

## 📚 前置知识

- 03-ruoyi-workflow.md（ruoyi 工作流架构）
- 13-task-query.md（任务查询）
- 02-flowable-concepts.md（Task）

## 1. 核心概念

### 1.1 ruoyi 的 7 种候选策略

| 策略 | 枚举 | 用途 |
|------|------|------|
| **指定用户** | `USER` | 审批人固定 |
| **指定角色** | `ROLE` | 某角色的所有人 |
| **部门成员** | `DEPT_MEMBER` | 某部门的所有人 |
| **部门负责人** | `DEPT_LEADER` | 某部门的 leader |
| **发起人** | `START_USER` | 流程发起人自己审 |
| **发起人部门负责人** | `START_USER_DEPT_LEADER` | 发起人所在部门 leader |
| **表单内用户** | `FORM_USER` | 从表单字段读取 |
| **自定义表达式** | `EXPRESSION` | SpEL 表达式 |

**Flowable 原生** vs **ruoyi 扩展**：

| 概念 | Flowable | ruoyi |
|------|---------|-------|
| **单个 assignee** | `assignee="userId"` | 通过 `candidateStrategy=USER, candidateParam=101` |
| **多个候选** | `candidateUsers="1,2,3"` | 策略类自动展开 |
| **候选组** | `candidateGroups="hr"` | 通过 `candidateStrategy=ROLE, candidateParam=2` |

### 1.2 策略接口

```java
public interface BpmTaskCandidateStrategy {
    BpmTaskCandidateStrategyEnum getStrategy();
    void validateParam(String param);
    default boolean isParamRequired() { return true; }
    Set<Long> calculateUsers(String param, DelegateExecution execution);
}
```

**关键方法**：`calculateUsers` 根据参数计算**候选用户集合**。

### 1.3 策略调用入口

`BpmTaskCandidateInvoker` 是所有策略的"路由器"：
- 注入 `List<BpmTaskCandidateStrategy>`
- 根据 `BpmTaskCandidateStrategyEnum` 路由到具体策略
- 提供 `validateBpmnConfig()` 校验策略配置

## 2. 代码示例

### 2.1 "指定用户"策略实现

```java
@Component
public class BpmTaskCandidateUserStrategy implements BpmTaskCandidateStrategy {

    @Override
    public BpmTaskCandidateStrategyEnum getStrategy() {
        return BpmTaskCandidateStrategyEnum.USER;
    }

    @Override
    public void validateParam(String param) {
        Assert.notNull(Long.parseLong(param), "用户编号不能为空");
    }

    @Override
    public Set<Long> calculateUsers(String param, DelegateExecution execution) {
        return CollUtil.newHashSet(Long.parseLong(param));
    }
}
```

### 2.2 "部门负责人"策略实现（简化）

```java
@Component
public class BpmTaskCandidateDeptLeaderStrategy extends AbstractBpmTaskCandidateDeptLeaderStrategy {

    @Override
    public BpmTaskCandidateStrategyEnum getStrategy() {
        return BpmTaskCandidateStrategyEnum.DEPT_LEADER;
    }

    @Override
    public Set<Long> calculateUsers(String param, DelegateExecution execution) {
        // 1. param = 部门 ID
        // 2. 调用 DeptApi.getDept(deptId).leaderUserId
        return CollUtil.newHashSet(deptApi.getDept(Long.parseLong(param)).getLeaderUserId());
    }
}
```

### 2.3 常见错误：策略参数忘了

```java
// ❌ 错误：选了"指定用户"但没填用户
candidateStrategy = "USER"
candidateParam = ""
// 部署时抛 MODEL_DEPLOY_FAIL_TASK_CANDIDATE_NOT_CONFIG

// ✅ 正确
candidateStrategy = "USER"
candidateParam = "101"
```

## 3. ruoyi 仓库源码解读

### 3.1 BpmTaskCandidateStrategy 接口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/candidate/BpmTaskCandidateStrategy.java`
**核心代码**（行 17-50）：

```java
/**
 * BPM 任务的候选人的策略接口
 * 例如说：分配审批人
 */
public interface BpmTaskCandidateStrategy {

    /**
     * 对应策略
     */
    BpmTaskCandidateStrategyEnum getStrategy();

    /**
     * 校验参数
     */
    void validateParam(String param);

    /**
     * 是否一定要输入参数
     */
    default boolean isParamRequired() {
        return true;
    }

    /**
     * 获得任务的候选人
     * @param param 策略参数
     * @param execution 执行任务
     * @return 用户编号集合
     */
    Set<Long> calculateUsers(String param, DelegateExecution execution);
}
```

**解读**：
- 4 个方法：getStrategy / validateParam / isParamRequired / calculateUsers
- `default` 方法：`isParamRequired` 默认 true（子类可重写为 false）
- **关键设计**：接口方法**少而精**，新增策略只需实现 4 个方法

### 3.2 BpmTaskCandidateInvoker：策略路由器

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/candidate/BpmTaskCandidateInvoker.java`
**核心代码**（行 36-90）：

```java
@Slf4j
public class BpmTaskCandidateInvoker {

    private final Map<BpmTaskCandidateStrategyEnum, BpmTaskCandidateStrategy> strategyMap = new HashMap<>();

    private final AdminUserApi adminUserApi;

    public BpmTaskCandidateInvoker(List<BpmTaskCandidateStrategy> strategyList,
                                   AdminUserApi adminUserApi) {
        strategyList.forEach(strategy -> {
            BpmTaskCandidateStrategy oldStrategy = strategyMap.put(strategy.getStrategy(), strategy);
            Assert.isNull(oldStrategy, "策略(%s) 重复", strategy.getStrategy());
        });
        this.adminUserApi = adminUserApi;
    }

    /**
     * 校验流程模型的任务分配规则全部都配置了
     */
    public void validateBpmnConfig(byte[] bpmnBytes) {
        BpmnModel bpmnModel = BpmnModelUtils.getBpmnModel(bpmnBytes);
        assert bpmnModel != null;
        List<UserTask> userTaskList = BpmnModelUtils.getBpmnModelElements(bpmnModel, UserTask.class);
        // 遍历所有的 UserTask，校验审批人配置
        userTaskList.forEach(userTask -> {
            Integer approveType = BpmnModelUtils.parseApproveType(userTask);
            if (ObjectUtils.equalsAny(approveType,
                    BpmUserTaskApproveTypeEnum.AUTO_APPROVE.getType(),
                    BpmUserTaskApproveTypeEnum.AUTO_REJECT.getType())) {
                return;
            }
            Integer strategy = BpmnModelUtils.parseCandidateStrategy(userTask);
            String param = BpmnModelUtils.parseCandidateParam(userTask);
            if (strategy == null) {
                throw exception(MODEL_DEPLOY_FAIL_TASK_CANDIDATE_NOT_CONFIG, userTask.getName());
            }
```

**解读**：
- 第 38 行：用 Map 缓存所有策略，**O(1) 查找**
- 第 42-49 行：构造时把 List 转 Map（Spring 注入 List 包含所有实现）
- 第 46 行：禁止策略重复注册
- 第 57-77 行：校验 BPMN 中所有 UserTask 的策略配置
- **关键设计**：用 Map 而非 if-else，**新增策略零修改 Invoker**

### 3.3 BpmnModelConstants：扩展属性名

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/enums/BpmnModelConstants.java`
**核心代码**（行 18-50）：

```java
/**
 * BPMN UserTask 的扩展属性，用于标记候选人策略
 */
String USER_TASK_CANDIDATE_STRATEGY = "candidateStrategy";

/**
 * BPMN UserTask 的扩展属性，用于标记候选人参数
 */
String USER_TASK_CANDIDATE_PARAM = "candidateParam";

/**
 * BPMN ExtensionElement 的扩展属性，用于标记边界事件类型
 */
String BOUNDARY_EVENT_TYPE = "boundaryEventType";

/**
 * BPMN ExtensionElement 的扩展属性，用于标记用户任务超时执行动作
 */
String USER_TASK_TIMEOUT_HANDLER_TYPE = "timeoutHandlerType";
```

**解读**：
- `candidateStrategy` / `candidateParam` 是 ruoyi 扩展属性
- 在 BPMN 中以 `flowable:property` 的形式存储
- **关键设计**：扩展属性有**统一前缀**（USER_TASK_*），便于在 BPMN 中查找

### 3.4 策略实现目录结构

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/candidate/strategy/`

```
strategy/
├── user/                  # 用户类策略
│   ├── BpmTaskCandidateUserStrategy.java          # 指定用户
│   ├── BpmTaskCandidateRoleStrategy.java          # 指定角色
│   ├── BpmTaskCandidatePostStrategy.java          # 指定岗位
│   ├── BpmTaskCandidateGroupStrategy.java         # 指定用户组
│   └── BpmTaskCandidateStartUserStrategy.java     # 发起人
├── dept/                  # 部门类策略
│   ├── BpmTaskCandidateDeptMemberStrategy.java    # 部门成员
│   ├── BpmTaskCandidateDeptLeaderStrategy.java    # 部门负责人
│   ├── BpmTaskCandidateDeptLeaderMultiStrategy.java  # 部门多级负责人
│   ├── AbstractBpmTaskCandidateDeptLeaderStrategy.java  # 抽象基类
│   └── BpmTaskCandidateStartUserDeptLeaderStrategy.java
├── form/                  # 表单类策略
│   ├── BpmTaskCandidateFormUserStrategy.java      # 表单用户
│   ├── BpmTaskCandidateFormDeptLeaderStrategy.java
│   └── BpmTaskCandidateApproveUserSelectStrategy.java
└── other/                 # 其他
    ├── BpmTaskCandidateStartUserSelectStrategy.java
    ├── BpmTaskCandidateAssignEmptyStrategy.java   # 空处理
    └── BpmTaskCandidateExpressionStrategy.java    # 表达式
```

**解读**：
- 4 大类：user（用户）、dept（部门）、form（表单）、other（其他）
- 每类一个目录，**结构清晰**
- 抽象基类 `AbstractBpmTaskCandidateDeptLeaderStrategy` 减少重复代码

## 4. 关键要点总结

- ruoyi 提供 7+ 种候选策略，分 4 大类
- 策略通过 `BpmTaskCandidateStrategy` 接口实现
- `BpmTaskCandidateInvoker` 用 Map 路由（O(1) 查找）
- 部署时 `validateBpmnConfig` 校验所有 UserTask 都有策略
- 自定义属性 `candidateStrategy` / `candidateParam` 存在 BPMN 扩展元素中
- 新增策略只需写一个 `@Component` 类，**Invoker 零修改**

## 5. 练习题

### 练习 1：基础（必做）

回答：
1. ruoyi 的 7 种策略分别是什么？
2. 策略如何注册到 Invoker？
3. 部署时如何校验策略配置？

**参考答案**：见 `solutions/21-task-assign.md`

### 练习 2：进阶

阅读 `BpmTaskCandidateDeptLeaderStrategy` 完整实现，说明它如何处理"部门没有 leader"的边界情况。

### 练习 3：挑战（选做）

新增"上级部门负责人"策略：审批人是"申请人所在部门的上级部门 leader"。提示：调用 `DeptApi.getDept(...).getParentId()` 拿到 parentId，再查 leader。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/candidate/BpmTaskCandidateStrategy.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/candidate/BpmTaskCandidateInvoker.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/enums/BpmnModelConstants.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/candidate/strategy/`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
