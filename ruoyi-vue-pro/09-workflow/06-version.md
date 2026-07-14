# 2.3 流程版本管理

> 理解 ruoyi 中流程定义的版本控制：同 key 多次部署产生的多版本、如何查询/激活/挂起指定版本。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 Flowable 中"版本"由 `VERSION_` 字段自增维护
- 区分"激活"（suspensionState=1）和"挂起"（suspensionState=2）
- 知道 ruoyi 在 `BpmProcessDefinitionService` 中如何查询版本列表
- 能用 SQL 查 `act_re_procdef` 表的所有版本

## 📚 前置知识

- 05-deploy.md（部署原理）
- 02-flowable-concepts.md（Deployment / ProcessDefinition）

## 1. 核心概念

### 1.1 版本号自动生成

`act_re_procdef` 表的关键字段：

| 字段 | 含义 | 示例 |
|------|------|------|
| `ID_` | 主键 | `leave:2:50002` |
| `REV_` | 乐观锁版本 | 1 |
| `CATEGORY_` | 分类 | `oa` |
| `NAME_` | 流程名称 | `请假流程` |
| `KEY_` | 流程 key | `leave` |
| `VERSION_` | 版本号 | 2 |
| `DEPLOYMENT_ID_` | 部署 ID | `50001` |
| `SUSPENSION_STATE_` | 状态 | 1=激活，2=挂起 |
| `DERIVED_VERSION_` | 衍生版本 | 0 |

**主键生成规则**：`{key}:{version}:{derived_version}:{timestamp-derived}`

### 1.2 激活 vs 挂起

- **激活（Active）**：流程可以被 `startProcessInstanceByKey()` 启动
- **挂起（Suspended）**：流程不能被启动，已启动的实例也不能继续流转

**用途**：
- 旧版本自动挂起（防止"未完成实例跑到新版本"）
- 紧急情况下管理员可手动挂起新版本

### 1.3 ruoyi 对版本的封装

ruoyi 通过 `BpmProcessDefinitionService` 提供：
- `getProcessDefinitionPage()`：分页查询（含版本号、分类等）
- `getActiveProcessDefinition(key)`：获取指定 key 的**最新激活版本**
- `updateProcessDefinitionState(id, state)`：激活/挂起

**`bpm_process_definition_info` 表**（ruoyi 自己的表）：
- 存储"业务字段"：category、formId、description 等
- 与 `act_re_procdef.ID_` 关联

## 2. 代码示例

### 2.1 查询所有版本

```java
List<ProcessDefinition> list = repositoryService.createProcessDefinitionQuery()
    .processDefinitionKey("leave")
    .orderByProcessDefinitionVersion().desc()
    .list();
// 输出：[v2, v1]（按版本倒序）
```

### 2.2 挂起 / 激活

```java
// 挂起
repositoryService.suspendProcessDefinitionById("leave:1:50001");

// 激活
repositoryService.activateProcessDefinitionById("leave:1:50001");
```

### 2.3 常见错误：用 key 启动流程但忘记 key 有多版本

```java
// ❌ 错误：以为 processDefinitionKey() 启动的是特定版本
// 实际：Flowable 默认启动该 key 的最新激活版本
ProcessInstance pi = runtimeService.startProcessInstanceByKey("leave");

// ✅ 正确：明确指定版本（通过 ID 而非 key）
ProcessInstance pi = runtimeService.startProcessInstanceById("leave:2:50002");
```

## 3. ruoyi 仓库源码解读

### 3.1 流程定义分页查询

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/BpmProcessDefinitionController.java`
**核心代码**（行 52-60）：

```java
@GetMapping("/page")
@Operation(summary = "获得流程定义分页")
@PreAuthorize("@ss.hasPermission('bpm:process-definition:query')")
public CommonResult<PageResult<BpmProcessDefinitionRespVO>> getProcessDefinitionPage(
        BpmProcessDefinitionPageReqVO pageReqVO) {
    PageResult<ProcessDefinition> pageResult = processDefinitionService.getProcessDefinitionPage(pageReqVO);
    if (CollUtil.isEmpty(pageResult.getList())) {
        return success(PageResult.empty(pageResult.getTotal()));
    }
```

**解读**：
- 第 52 行：`/bpm/process-definition/page` 提供分页查询
- 第 56 行：分页参数在 `BpmProcessDefinitionPageReqVO` 中（含 `key` 模糊匹配、`category` 等）
- 第 57 行：直接返回 Flowable 原生 `ProcessDefinition` 列表，由后续 `convertList` 转换为 VO
- **关键设计**：所有版本**都被查询出来**，不做"去重只保留最新"，让管理员看到完整历史

### 3.2 版本号在 VO 中暴露给前端

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/vo/process/BpmProcessDefinitionRespVO.java`（基于命名推断）
**核心代码**（推断结构）：

```java
@Schema(description = "管理后台 - 流程定义 Response VO")
@Data
public class BpmProcessDefinitionRespVO {
    @Schema(description = "编号", example = "1024")
    private String id;        // 完整 ID：leave:2:50002

    @Schema(description = "流程名称", example = "请假流程")
    private String name;

    @Schema(description = "流程 key", example = "leave")
    private String key;

    @Schema(description = "版本号", example = "2")
    private Integer version;  // 由 parseId 解析得到

    @Schema(description = "分类", example = "oa")
    private String category;

    @Schema(description = "状态", example = "1")  // 1=激活, 2=挂起
    private Integer suspensionState;
}
```

**解读**：
- `id` 是 Flowable 内部 ID（含版本号），前端需用工具拆分才能展示
- `version` 是从 `id` 解析出来的"纯版本号"
- `suspensionState` 暴露给前端做"激活/挂起"按钮的可见性判断

## 4. 关键要点总结

- Flowable 用 `VERSION_` 自增管理版本，**同 key 多次部署产生多版本**
- 旧版本自动挂起（`SUSPENSION_STATE_=2`），防止"未完成实例跳版本"
- 启动流程用 key 会默认走"最新激活版本"，用 ID 可指定具体版本
- ruoyi 的 `BpmProcessDefinitionService` 提供分页查询、激活/挂起 API
- ruoyi 自己在 `bpm_process_definition_info` 表保存业务字段（category、formId 等）

## 5. 练习题

### 练习 1：基础（必做）

用 SQL 查询所有 `key = "leave"` 的流程定义，按版本倒序：
```sql
SELECT ID_, KEY_, VERSION_, SUSPENSION_STATE_ FROM act_re_procdef
WHERE KEY_ = 'leave' ORDER BY ??? ;
```

**参考答案**：见 `solutions/06-version.md`

### 练习 2：进阶

阅读 `BpmProcessDefinitionServiceImpl.getProcessDefinitionPage`，看它如何把 `ProcessDefinition` 列表拼接上 ruoyi 的业务字段（category、formId、description）。它用了什么批量查询技巧？

### 练习 3：挑战（选做）

实现一个"版本回滚"接口：传入 `processDefinitionId`，把该版本重新激活，并把同 key 的其他版本都挂起。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/BpmProcessDefinitionController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/definition/BpmProcessDefinitionServiceImpl.java`
- Flowable 流程定义章节：https://www.flowable.com/open-source/docs/bpmn/ch14-API/#process-definitions

---

**文档版本**：v1.0
**最后更新**：2026-07-13
