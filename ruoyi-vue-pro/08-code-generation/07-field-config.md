# 2.2 字段配置：列表/查询/表单

> 学习如何为每个字段配置"出现在哪些场景"以及"用什么查询条件"。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 `createOperation` / `updateOperation` / `listOperation` 三个开关的作用
- 解释 `listOperationCondition`（EQ/LIKE/BETWEEN）的实际 SQL 输出
- 在生成器前端配置"字段是否在列表展示"
- 自定义一个字段的"创建时不传"规则

## 📚 前置知识

- 总览 / 导入表 / 类型映射（详见 [总览](./01-overview.md)、[导入表](./03-table-import.md)、[类型映射](./04-type-mapping.md)）

## 1. 核心概念

### 1.1 字段的 3 个 CRUD 开关

每个字段在元数据中都有 3 个 `Boolean` 开关：

| 字段 | 决定 |
|------|------|
| `createOperation` | 是否在"创建"接口的入参 VO 出现 |
| `updateOperation` | 是否在"更新"接口的入参 VO 出现 |
| `listOperation` | 是否在"查询条件"出现（PageReqVO 字段） |
| `listOperationResult` | 是否在"返回结果 RespVO"出现 |

### 1.2 查询条件 7 种

| 条件 | SQL 模板 | 适用 |
|------|---------|------|
| `EQ` | `=` | 状态、类型 |
| `NE` | `!=` | 反向查询 |
| `GT/GTE/LT/LTE` | `>` `>=` `<` `<=` | 数值 |
| `LIKE` | `LIKE '%?%'` | 名称 |
| `BETWEEN` | `BETWEEN ? AND ?` | 时间区间 |

## 2. 代码示例

### 2.1 字段配置的"预期生成结果"

假设字段 `nickname VARCHAR(50)`：

| 开关 | 设置 | 效果 |
|------|------|------|
| createOperation | ✅ | `SaveReqVO` 包含 `nickname` |
| updateOperation | ✅ | `SaveReqVO` 包含 `nickname` |
| listOperation | ✅ | `PageReqVO` 包含 `nickname` |
| listOperationCondition | `LIKE` | 生成 `LIKE '%?%'` |
| listOperationResult | ✅ | `RespVO` 包含 `nickname` |

### 2.2 主键字段的默认处理

```java
// 在 CodegenBuilder 中
private static final Set<String> CREATE_OPERATION_EXCLUDE_COLUMN
    = Sets.newHashSet("id"); // 创建时不传 id

// 主键自动排除
column.setCreateOperation(
    !CREATE_OPERATION_EXCLUDE_COLUMN.contains(column.getJavaField())
    && !column.getPrimaryKey()
);
```

## 3. 关键要点总结

- 每个字段有 4 个开关：`createOperation` / `updateOperation` / `listOperation` / `listOperationResult`
- `BaseDO` 的字段（`id`/`creator`/`createTime`/...）默认**全部排除**，`createTime` 例外
- 查询条件默认 `EQ`，通过字段名后缀覆盖
- Vue 模板用 `v-if="column.listOperationResult"` 过滤字段

---

**文档版本**：v1.0
**最后更新**：2026-07-13
