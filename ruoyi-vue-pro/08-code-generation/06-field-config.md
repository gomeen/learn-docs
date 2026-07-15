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

## 3. ruoyi 仓库源码解读

### 3.1 字段 CRUD 默认值逻辑

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/inner/CodegenBuilder.java`
**核心代码**（行 145-180，简化）：

```java
private void processColumnOperation(CodegenColumnDO column) {
    // 1. createOperation: 排除主键 + 系统字段
    column.setCreateOperation(
        !CREATE_OPERATION_EXCLUDE_COLUMN.contains(column.getJavaField())
        && !column.getPrimaryKey()
    );
    // 2. updateOperation: 同上
    column.setUpdateOperation(
        !UPDATE_OPERATION_EXCLUDE_COLUMN.contains(column.getJavaField())
    );
    // 3. listOperation: 排除系统字段（但保留 createTime）
    column.setListOperation(
        !LIST_OPERATION_EXCLUDE_COLUMN.contains(column.getJavaField())
    );
    // 4. listOperationCondition: 按后缀推断
    if (column.getListOperation()) {
        for (var entry : COLUMN_LIST_OPERATION_CONDITION_MAPPINGS.entrySet()) {
            if (column.getJavaField().endsWith(entry.getKey())) {
                column.setListOperationCondition(entry.getValue().getCondition());
                break;
            }
        }
        // 默认 EQ
        if (column.getListOperationCondition() == null) {
            column.setListOperationCondition(CodegenColumnListConditionEnum.EQ.getCondition());
        }
    }
    // 5. listOperationResult: 默认 true（除非在排除集）
    column.setListOperationResult(
        !LIST_OPERATION_RESULT_EXCLUDE_COLUMN.contains(column.getJavaField())
    );
}
```

**解读**：
- 排除集合包含 `id` / `creator` / `createTime` / `updateTime` 等 BaseDO 字段
- `createTime` **保留**在 listOperation 和 listOperationResult 中（用户经常按时间筛选 / 查看）
- 查询条件默认 `EQ`，命中后缀规则才覆盖

### 3.2 排除集合的初始化

**位置**：`CodegenBuilder.java` 行 88-98

```java
static {
    // 1. 反射 BaseDO 获取所有字段
    Arrays.stream(ReflectUtil.getFields(BaseDO.class))
        .forEach(field -> BASE_DO_FIELDS.add(field.getName()));
    BASE_DO_FIELDS.add("tenantId"); // 多租户字段

    // 2. 把 BaseDO 字段加到所有排除集中
    CREATE_OPERATION_EXCLUDE_COLUMN.addAll(BASE_DO_FIELDS);
    UPDATE_OPERATION_EXCLUDE_COLUMN.addAll(BASE_DO_FIELDS);
    LIST_OPERATION_EXCLUDE_COLUMN.addAll(BASE_DO_FIELDS);
    LIST_OPERATION_EXCLUDE_COLUMN.remove("createTime"); // 重新加入
    LIST_OPERATION_RESULT_EXCLUDE_COLUMN.addAll(BASE_DO_FIELDS);
    LIST_OPERATION_RESULT_EXCLUDE_COLUMN.remove("createTime");
}
```

**解读**：
- 通过**反射**自动收集 `BaseDO` 的字段名（避免硬编码遗漏）
- `createTime` 是个例外：从排除集中**移除**回来，因为它是"时间筛选"和"列表展示"的常用字段

### 3.3 Vue 端字段配置的体现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/vue3/views/index.vue.vm`
**关键代码片段**（行 100-150 简化）：

```vue
<!-- 列表字段：遍历 columns.listOperationResult=true 的字段 -->
<el-table-column
  v-for="column in columns"
  :key="column.javaField"
  :label="column.columnComment"
  :prop="column.javaField"
  v-if="column.listOperationResult"
/>

<!-- 查询表单：遍历 columns.listOperation=true 的字段 -->
<el-form-item
  v-for="column in columns"
  :key="column.javaField"
  :label="column.columnComment"
  v-if="column.listOperation"
>
  <el-input v-if="column.htmlType === 'input'" v-model="queryParams[column.javaField]" />
  <el-select v-else-if="column.htmlType === 'select'" v-model="queryParams[column.javaField]">
    <el-option v-for="dict in getDictOptions(column.dictType)" :key="dict.value" :label="dict.label" :value="dict.value" />
  </el-select>
</el-form-item>
```

**解读**：
- Vue 模板中 `v-if="column.listOperationResult"` 是**核心开关**
- 字段的 HTML 控件类型由 `column.htmlType` 决定

## 4. 关键要点总结

- 每个字段有 4 个开关：`createOperation` / `updateOperation` / `listOperation` / `listOperationResult`
- `BaseDO` 的字段（`id`/`creator`/`createTime`/...）默认**全部排除**，`createTime` 例外
- 查询条件默认 `EQ`，通过字段名后缀覆盖
- Vue 模板用 `v-if="column.listOperationResult"` 过滤字段

## 5. 练习题

### 练习 1：基础（必做）

在 IDEA 中打开 `CodegenColumnDO.java`，给每个字段写一个简短注释（不超过 10 字）。

### 练习 2：进阶

假设表 `system_user` 有一个字段 `password`，你希望"它出现在 DB 但不出现在任何 VO"。如何配置？需要修改 `CodegenBuilder` 还是 `CodegenColumnDO` 的哪个字段？

### 练习 3：挑战（选做）

在 `CodegenBuilder` 中新增"按 JavaType 推断"逻辑：所有 `Boolean` 类型字段默认是 `listOperationCondition = EQ` 且 `htmlType = RADIO`。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/inner/CodegenBuilder.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/dal/dataobject/codegen/CodegenColumnDO.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/vue3/views/index.vue.vm`
- 官方文档：https://doc.iocoder.cn/codegen/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
