# 2.4 流程分类与标签

> 理解 ruoyi 中"流程分类"（Category）的设计：用于对流程进行归类、便于管理和查询。

## 🎯 学习目标

完成本文档后，你将能够：
- 知道"流程分类"是 ruoyi 自己的业务概念（Flowable 不内置）
- 掌握 ruoyi `BpmCategoryDO` 的字段含义
- 了解"分类 + 标签"的组合用法
- 能用 `/bpm/category/*` 接口管理分类

## 📚 前置知识

- 03-ruoyi-workflow.md（ruoyi BPM 模块结构）
- 04-modeler.md（流程设计与 category 关联）

## 1. 核心概念

### 1.1 什么是流程分类？

**流程分类** = 对流程进行"业务分组"，例如：
- `OA`：请假、报销、加班
- `HR`：入职、转正、离职
- `财务`：付款、报销
- `技术`：发布申请、服务器申请

**为什么需要分类？**
- **管理**：管理员按分类维护流程
- **查询**：用户按分类浏览"我能发起的流程"
- **权限**：可以按分类分配权限

### 1.2 Flowable 不内置分类？

正确。Flowable 的 `ProcessDefinition` 有 `CATEGORY_` 字段，但**只是字符串**。ruoyi 在此基础上扩展为 `BpmCategoryDO` 表，提供：
- 分类名称、图标、排序
- 启用/禁用状态
- 拖拽排序（`update-sort-batch`）

### 1.3 分类与 Model 的关联

```
BpmCategoryDO（id=1, name="OA", code="oa"）
   ↓
BpmModel.MetaInfo.category = "oa"
   ↓
BpmProcessDefinitionInfoDO.category = "oa"
   ↓
用户在【OA 分类】下看到所有 OA 相关流程
```

## 2. 代码示例

### 2.1 创建分类

```bash
POST /admin-api/bpm/category/create
{
  "name": "人事",
  "code": "hr",
  "icon": "user",
  "sort": 5,
  "status": 0
}
```

**说明**：
- `name`：中文名（前端展示用）
- `code`：英文 code（程序用）
- `status`：0=启用，1=禁用

### 2.2 拖拽排序

```bash
PUT /admin-api/bpm/category/update-sort-batch?ids=3,1,2
```

**说明**：传入新的顺序 ID 列表，后端按列表顺序更新 `sort` 字段。

### 2.3 常见错误：删除被引用的分类

```bash
# ❌ 错误：删除一个还有 Model 在引用的分类
DELETE /bpm/category/delete?id=1
# 响应：500 "分类已被流程使用，无法删除"

# ✅ 正确：先迁移 Model 到其他分类，再删除
```

## 3. ruoyi 仓库源码解读

### 3.1 BpmCategoryController：CRUD 标准模板

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/BpmCategoryController.java`
**核心代码**（行 27-58）：

```java
@Tag(name = "管理后台 - BPM 流程分类")
@RestController
@RequestMapping("/bpm/category")
@Validated
public class BpmCategoryController {

    @Resource
    private BpmCategoryService categoryService;

    @PostMapping("/create")
    @Operation(summary = "创建流程分类")
    @PreAuthorize("@ss.hasPermission('bpm:category:create')")
    public CommonResult<Long> createCategory(@Valid @RequestBody BpmCategorySaveReqVO createReqVO) {
        return success(categoryService.createCategory(createReqVO));
    }

    @PutMapping("/update")
    @Operation(summary = "更新流程分类")
    @PreAuthorize("@ss.hasPermission('bpm:category:update')")
    public CommonResult<Boolean> updateCategory(@Valid @RequestBody BpmCategorySaveReqVO updateReqVO) {
        categoryService.updateCategory(updateReqVO);
        return success(true);
    }

    @PutMapping("/update-sort-batch")
    @Operation(summary = "批量更新流程分类的排序")
    @Parameter(name = "ids", description = "分类编号列表", required = true, example = "1,2,3")
    @PreAuthorize("@ss.hasPermission('bpm:category:update')")
    public CommonResult<Boolean> updateCategorySortBatch(@RequestParam("ids") List<Long> ids) {
        categoryService.updateCategorySortBatch(ids);
        return success(true);
    }
```

**解读**：
- 第 28 行：`/bpm/category` 是分类管理的根路由
- 第 33 行：仅依赖 `BpmCategoryService`，不耦合其他 Service（**单一职责**）
- 第 38 行：`@PreAuthorize` 权限校验
- 第 55 行：拖拽排序接口（前端拖拽后调用）
- **关键设计**：所有写接口都走 ruoyi 的 `*ServiceImpl`，**不直接操作 MyBatis Mapper**

### 3.2 BpmCategoryDO 表结构

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/dal/dataobject/definition/BpmCategoryDO.java`（基于命名推断）
**核心字段**（推断）：

```java
@TableName("bpm_category")
@KeySequence("bpm_category_seq")
@Data
public class BpmCategoryDO extends BaseDO {
    private Long id;
    private String name;          // 中文名
    private String code;          // 英文 code
    private String icon;          // 图标
    private Integer sort;         // 排序
    private Integer status;       // 0=启用 1=禁用
}
```

**解读**：
- 继承 `BaseDO`（ruoyi 框架基础类，含 createTime、updateTime、creator 等）
- 用 `@KeySequence` + Oracle 序列兼容（如果使用 Oracle）
- **关键设计**：分类 ID 由 MyBatis Plus 雪花算法生成，**全局唯一**

### 3.3 SimpleModelUtils 中的 NodeConvert 体系

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/util/SimpleModelUtils.java`
**核心代码**（行 39-50）：

```java
public class SimpleModelUtils {

    private static final Map<BpmSimpleModelNodeTypeEnum, NodeConvert> NODE_CONVERTS = MapUtil.newHashMap();

    static {
        List<NodeConvert> converts = asList(new StartNodeConvert(), new EndNodeConvert(),
                new StartUserNodeConvert(), new ApproveNodeConvert(), new CopyNodeConvert(), new TransactorNodeConvert(),
                new DelayTimerNodeConvert(), new TriggerNodeConvert(),
                new ConditionBranchNodeConvert(), new ParallelBranchNodeConvert(), new InclusiveBranchNodeConvert(), new RouteBranchNodeConvert(),
                new ChildProcessConvert());
        converts.forEach(convert -> NODE_CONVERTS.put(convert.getType(), convert));
    }
```

**解读**：
- 静态块注册 12 种节点转换器：开始、结束、发起人、审批、抄送、办理人、定时器、触发器、条件分支、并行分支、包容分支、路由分支、子流程
- 每个 `NodeConvert` 处理一种 BPMN 节点类型
- **关键设计**：用 Map 替代 if-else，**新增节点类型只需写一个 NodeConvert 实现**

## 4. 关键要点总结

- 流程分类是 **ruoyi 自己的业务概念**（`BpmCategoryDO`），Flowable 不内置
- 字段：name（中文）、code（英文）、icon、sort、status
- 拖拽排序通过 `update-sort-batch` 接口实现
- 分类与 Model/ProcessDefinition 通过 `category` 字符串字段关联
- ruoyi 的"简化模型"用 `Map<Enum, NodeConvert>` 模式注册节点转换器，新增节点类型零修改

## 5. 练习题

### 练习 1：基础（必做）

回答下列问题：
1. ruoyi 的分类用哪个表？用哪个字段关联 Model？
2. `update-sort-batch` 接收什么参数？
3. 删除分类时如何校验"是否被引用"？

**参考答案**：见 `solutions/07-category.md`

### 练习 2：进阶

阅读 `SimpleModelUtils.NodeConvert` 接口（行 60+），找到 `ApproveNodeConvert` 实现。说明它转换的 BPMN 元素类型是？输出哪些 XML 属性？

### 练习 3：挑战（选做）

为 ruoyi 增加"分类图标"功能：前端展示分类时显示对应图标。要求后端：新增 `icon` 字段到 VO、DO、Mapper，并写出"按 sort 排序返回所有启用分类"接口。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/controller/admin/definition/BpmCategoryController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/util/SimpleModelUtils.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/dal/dataobject/definition/BpmCategoryDO.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
