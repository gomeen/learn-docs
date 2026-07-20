# 2.4 流程分类与标签

> 理解 ruoyi 中"流程分类"（Category）的设计：用于对流程进行归类、便于管理和查询。

## 🎯 学习目标

完成本文档后，你将能够：
- 知道"流程分类"是 ruoyi 自己的业务概念（Flowable 不内置）
- 掌握 ruoyi `BpmCategoryDO` 的字段含义
- 了解"分类 + 标签"的组合用法
- 能用 `/bpm/category/*` 接口管理分类

## 📚 前置知识

- ruoyi BPM 模块结构（详见 [ruoyi 工作流](./03-ruoyi-workflow.md)）
- 流程设计与 category（详见 [Modeler](./05-modeler.md)）

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

## 3. 关键要点总结

- 流程分类是 **ruoyi 自己的业务概念**（`BpmCategoryDO`），Flowable 不内置
- 字段：name（中文）、code（英文）、icon、sort、status
- 拖拽排序通过 `update-sort-batch` 接口实现
- 分类与 Model/ProcessDefinition 通过 `category` 字符串字段关联
- ruoyi 的"简化模型"用 `Map<Enum, NodeConvert>` 模式注册节点转换器，新增节点类型零修改

---

**文档版本**：v1.0
**最后更新**：2026-07-13
