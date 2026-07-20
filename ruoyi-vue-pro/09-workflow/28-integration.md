# 6.1 与业务模块集成

> 理解 ruoyi 中工作流与业务模块的集成方式：以 OA 请假为例。

## 🎯 学习目标

完成本文档后，你将能够：
- 知道"工作流"是"基础设施"，业务模块在自己的 Service 中调用工作流
- 掌握 ruoyi 的"双表设计"：业务表 + 流程实例表
- 理解 `BpmProcessInstanceApi` 的设计目的（供其他模块调用）
- 能在自己的业务模块中接入工作流

## 📚 前置知识

- 架构（详见 [ruoyi 工作流](./03-ruoyi-workflow.md)）
- 启动流程（详见 [启动流程](./15-start-process.md)）
- 变量（详见 [流程变量](./19-process-vars.md)）
- 业务模块分层（详见 [MVC 分层](../07-business-modules/02-mvc-layers.md)）

## 1. 核心概念

### 1.1 业务模块如何"接入"工作流？

**核心思路**：业务模块**不直接**调 Flowable，而是调 ruoyi 提供的 `BpmProcessInstanceApi`（Feign 远程调用）。

```
yudao-module-bpm
  ├── controller/admin/        # 管理后台 API
  ├── service/                 # 业务实现
  ├── api/                     # 对外暴露的 API（Feign）
  │   ├── task/                # 流程实例相关
  │   └── event/               # 事件相关
  └── dal/                     # Flowable 表 + ruoyi 业务表

yudao-module-oa  (假设的业务模块)
  ├── controller/admin/
  ├── service/                 # 调 BpmProcessInstanceApi 启动流程
  └── dal/                     # 业务表（oa_leave）
```

### 1.2 ruoyi 的"双表设计"

OA 请假流程涉及两张表：
- **业务表** `bpm_oa_leave`：存请假业务数据（申请人、天数、原因、状态）
- **Flowable 表** `act_ru_task` / `act_hi_procinst`：存流程实例

**为什么双表？**
- 业务表：业务系统自己的数据模型（CRUD、统计、报表）
- Flowable 表：流程运行时的状态

**双表同步**：
- 创建请假时：插入 `bpm_oa_leave` → 启动流程 → 监听器回写 `processInstanceId` 到 `bpm_oa_leave`
- 流程完成时：监听器更新 `bpm_oa_leave.status = 已完成`

### 1.3 BpmProcessInstanceApi：跨模块入口

```java
public interface BpmProcessInstanceApi {
    String createProcessInstance(Long userId, BpmProcessInstanceCreateReqDTO dto);
    void cancelProcessInstance(Long userId, String processInstanceId, String reason);
    BpmProcessInstanceRespDTO getProcessInstance(String processInstanceId);
}
```

**位置**：`yudao-module-bpm/.../api/task/`

## 2. 代码示例

### 2.1 OA 请假 Controller

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/oa/BpmOALeaveController.java`
**核心代码**（行 24-65）：

```java
/**
 * OA 请假申请 Controller，用于演示自己存储数据，接入工作流的例子
 */
@Tag(name = "管理后台 - OA 请假申请")
@RestController
@RequestMapping("/bpm/oa/leave")
@Validated
public class BpmOALeaveController {

    @Resource
    private BpmOALeaveService leaveService;

    @PostMapping("/create")
    @PreAuthorize("@ss.hasPermission('bpm:oa-leave:create')")
    @Operation(summary = "创建请求申请")
    public CommonResult<Long> createLeave(@Valid @RequestBody BpmOALeaveCreateReqVO createReqVO) {
        return success(leaveService.createLeave(getLoginUserId(), createReqVO));
    }

    @GetMapping("/get")
    @PreAuthorize("@ss.hasPermission('bpm:oa-leave:query')")
    @Operation(summary = "获得请假申请")
    @Parameter(name = "id", description = "编号", required = true, example = "1024")
    public CommonResult<BpmOALeaveRespVO> getLeave(@RequestParam("id") Long id) {
        BpmOALeaveDO leave = leaveService.getLeave(id);
        return success(BeanUtils.toBean(leave, BpmOALeaveRespVO.class));
    }
```

**解读**：
- 第 30 行：`/bpm/oa/leave` 路由
- 第 32 行：`@PreAuthorize` 权限校验
- 第 39-41 行：创建请假申请（内部会启动流程）
- **关键设计**：Controller 只做"接收请求 + 返回结果"，**业务逻辑全在 Service**

### 2.2 BpmOALeaveServiceImpl 创建流程（简化版）

```java
@Service
@Slf4j
public class BpmOALeaveServiceImpl implements BpmOALeaveService {

    @Resource
    private BpmProcessInstanceApi processInstanceApi;  // 调用 bpm 模块

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Long createLeave(Long userId, BpmOALeaveCreateReqVO createReqVO) {
        // 1. 插入业务表
        BpmOALeaveDO leave = BpmOALeaveConvert.INSTANCE.convert(createReqVO)
                .setUserId(userId).setStatus(BpmOALeaveStatusEnum.DRAFT.getStatus());
        leaveMapper.insert(leave);

        // 2. 启动流程
        Map<String, Object> variables = new HashMap<>();
        variables.put("days", createReqVO.getDays());
        BpmProcessInstanceCreateReqDTO dto = new BpmProcessInstanceCreateReqDTO()
                .setProcessDefinitionKey("leave")
                .setBusinessKey(String.valueOf(leave.getId()))  // 关联业务数据
                .setVariables(variables);
        String processInstanceId = processInstanceApi.createProcessInstance(userId, dto);

        // 3. 回填 processInstanceId
        leave.setProcessInstanceId(processInstanceId);
        leaveMapper.updateById(leave);
        return leave.getId();
    }
}
```

**解读**：
- 第 11 行：先插入业务表（**拿到 leaveId**）
- 第 19 行：构造 BpmProcessInstanceCreateReqDTO（业务无关）
- 第 20 行：businessKey = leaveId（**业务与流程关联**）
- 第 22 行：调 `processInstanceApi.createProcessInstance` 启动流程
- 第 25-26 行：把 processInstanceId 回填到业务表
- **关键设计**：`businessKey` 字段**贯穿**业务表和流程

### 2.3 常见错误：业务表和流程表不同步

```java
// ❌ 错误：启动流程失败但业务表已插入
leaveMapper.insert(leave);
processInstanceApi.createProcessInstance(...);  // 抛异常
// 业务表留下"孤儿"记录
```

```java
// ✅ 正确：用一个事务 + 异常时回滚
@Transactional
public Long createLeave(...) {
    leaveMapper.insert(leave);
    processInstanceApi.createProcessInstance(...);  // 抛异常
    leaveMapper.updateById(leave);  // 不会执行
    return leave.getId();
}
```

**注意**：Feign 调用是远程调用，**不参与 Spring 事务**。如果需要分布式事务，用 Seata 等方案。

## 3. 关键要点总结

- 业务模块通过 `BpmProcessInstanceApi`（Feign）调用工作流
- ruoyi 演示了"双表设计"：业务表 + Flowable 表
- `processInstanceId` 是关联字段，**业务表只存业务字段**
- `businessKey` 通常设为业务表 ID（便于反查）
- 跨模块调用不走 Spring 事务，**分布式事务需用 Seata**
- ruoyi 的 OA 请假是"业务接入"参考实现

---

**文档版本**：v1.0
**最后更新**：2026-07-13
