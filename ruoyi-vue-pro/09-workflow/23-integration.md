# 6.1 与业务模块集成

> 理解 ruoyi 中工作流与业务模块的集成方式：以 OA 请假为例。

## 🎯 学习目标

完成本文档后，你将能够：
- 知道"工作流"是"基础设施"，业务模块在自己的 Service 中调用工作流
- 掌握 ruoyi 的"双表设计"：业务表 + 流程实例表
- 理解 `BpmProcessInstanceApi` 的设计目的（供其他模块调用）
- 能在自己的业务模块中接入工作流

## 📚 前置知识

- 03-ruoyi-workflow.md（架构）
- 12-start-process.md（启动流程）
- 16-process-vars.md（变量）

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

## 3. ruoyi 仓库源码解读

### 3.1 BpmOALeaveController：业务 Controller 模板

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/oa/BpmOALeaveController.java`
**核心代码**（行 24-32）：

```java
/**
 * OA 请假申请 Controller，用于演示自己存储数据，接入工作流的例子
 *
 * @author jason
 * @author 芋道源码
 */
@Tag(name = "管理后台 - OA 请假申请")
@RestController
@RequestMapping("/bpm/oa/leave")
@Validated
public class BpmOALeaveController {
```

**解读**：
- 第 24 行：注释明确说明这是"演示业务接入工作流的例子"
- 业务模块可参考这个 Controller 写自己的接入代码
- **关键设计**：ruoyi 把"业务接入"的最佳实践写成了"参考实现"

### 3.2 业务表与流程表的双表同步

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/dal/dataobject/oa/BpmOALeaveDO.java`（基于命名推断）
**核心字段**（推断）：

```java
@TableName("bpm_oa_leave")
@Data
public class BpmOALeaveDO extends BaseDO {
    private Long id;
    private Long userId;           // 申请人
    private String type;            // 请假类型
    private Integer days;           // 天数
    private String reason;          // 原因
    private String processInstanceId;  // 流程实例 ID（核心关联字段）
    private Integer status;         // 业务状态
}
```

**解读**：
- `processInstanceId` 是核心关联字段
- 业务表只存"业务字段"，不存流程变量
- **关键设计**：业务表与流程表通过 `processInstanceId` 关联，**关注点分离**

### 3.3 BpmProcessInstanceApi 跨模块接口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/api/task/`
**核心代码**（基于命名推断）：

```java
@FeignClient(name = ApiConstants.NAME)  // Feign 远程调用
public interface BpmProcessInstanceApi {
    String PREFIX = ApiConstants.PREFIX + "/process-instance";

    @PostMapping(PREFIX + "/create")
    CommonResult<String> createProcessInstance(@RequestParam("userId") Long userId,
                                                @Valid @RequestBody BpmProcessInstanceCreateReqDTO dto);

    @PostMapping(PREFIX + "/cancel")
    CommonResult<Boolean> cancelProcessInstance(@RequestParam("userId") Long userId,
                                                 @RequestParam("processInstanceId") String processInstanceId,
                                                 @RequestParam(value = "reason", required = false) String reason);
}
```

**解读**：
- 用 Spring Cloud OpenFeign 暴露内部 API
- DTO 类（如 `BpmProcessInstanceCreateReqDTO`）在 `api/task/dto/` 下
- **关键设计**：通过 Feign 暴露**轻量 API**，**避免直接依赖 bpm 模块的 Service**

## 4. 关键要点总结

- 业务模块通过 `BpmProcessInstanceApi`（Feign）调用工作流
- ruoyi 演示了"双表设计"：业务表 + Flowable 表
- `processInstanceId` 是关联字段，**业务表只存业务字段**
- `businessKey` 通常设为业务表 ID（便于反查）
- 跨模块调用不走 Spring 事务，**分布式事务需用 Seata**
- ruoyi 的 OA 请假是"业务接入"参考实现

## 5. 练习题

### 练习 1：基础（必做）

回答：
1. ruoyi 用什么机制跨模块调用工作流？
2. 业务表和 Flowable 表的关联字段是？
3. 什么是 `businessKey`？为什么设置？

**参考答案**：见 `solutions/23-integration.md`

### 练习 2：进阶

阅读 `BpmOALeaveServiceImpl.createLeave` 完整实现，列出至少 3 个与工作流相关的操作。

### 练习 3：挑战（选做）

设计一个"图书借阅"业务：用户提交借阅申请 → 图书馆管理员审批 → 借阅成功。写出 Controller、Service、业务表 DO 的核心代码。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/oa/BpmOALeaveController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/api/task/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/dal/dataobject/oa/`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
