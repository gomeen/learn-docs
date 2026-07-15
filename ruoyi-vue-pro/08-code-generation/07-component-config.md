# 2.3 字典/枚举/用户组件

> 学习 ruoyi 代码生成器对字典、枚举、用户等"特殊字段"的组件配置。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释字典字段如何自动生成下拉框
- 解释"用户/部门"字段如何生成远程搜索下拉
- 解释"枚举"字段如何生成 radio/select
- 自定义一个新的"特殊组件"（如地区选择器）

## 📚 前置知识

- 类型映射 / 字段配置（详见 [类型映射](./04-type-mapping.md)、[字段配置](./06-field-config.md)）
- ruoyi 字典系统（详见 [字典管理](../07-business-modules/11-dict.md)）

## 1. 核心概念

### 1.1 三种"特殊字段"

| 特殊类型 | 标识 | 组件 | 数据源 |
|---------|------|------|--------|
| 字典 | `dictType != null` | `el-select` / `el-radio` | 后端 `dict-data` 接口 |
| 用户 | 字段名 = `userId` / 注释含"用户" | `UserSelect` 组件 | 后端 `user/simple-list` |
| 部门 | 字段名 = `deptId` / 注释含"部门" | `DeptSelect` 组件 | 后端 `dept/simple-list` |
| 枚举 | `dictType` 不为空且以 `time_`/`status_` 开头 | radio/select | 字典 |

### 1.2 字典的核心优势

字典 = 业务上**有限且固定的枚举值**。如：
- `common_status`（启用/禁用）
- `system_user_sex`（男/女）
- `system_menu_type`（目录/菜单/按钮）

字典的好处：
- 前端展示"启用"而不是 `0`
- 数据库存 `0`，避免魔法数字
- 字典项**可在线维护**，不需要改代码

## 2. 代码示例

### 2.1 Vue 端字典下拉框

```vue
<el-form-item label="状态" prop="status">
  <el-select v-model="formData.status" placeholder="请选择状态" clearable>
    <el-option
      v-for="dict in getIntDictOptions(DICT_TYPE.COMMON_STATUS)"
      :key="dict.value"
      :label="dict.label"
      :value="dict.value"
    />
  </el-select>
</el-form-item>
```

### 2.2 字典转换（数据库值 → 展示文本）

```javascript
// 在 Vue 组件中
getDictLabel(DICT_TYPE.COMMON_STATUS, row.status) // 返回 "启用"
```

## 3. ruoyi 仓库源码解读

### 3.1 字典关联字段

**位置**：`CodegenColumnDO.java` 行 89-94

```java
/**
 * 字典类型
 *
 * 关联 DictTypeDO 的 type 属性
 */
private String dictType;
```

**解读**：
- 字段类型为 `String`，存的是字典类型的 `type` 字段（如 `common_status`）
- 如果 `dictType` 不为空 → 该字段是"字典字段" → Vue 端用 `<el-select>` 而不是 `<el-input>`

### 3.2 字典用户选择器模板

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/vue3/views/form.vue.vm`
**关键代码片段**（简化）：

```vue
<!-- 表单字段渲染 -->
<el-form-item
  v-for="column in formColumns"
  :key="column.javaField"
  :label="column.columnComment"
  :prop="column.javaField"
>
  <!-- 1. 用户选择器 -->
  <UserSelect
    v-if="column.javaField === 'userId' || column.columnComment?.includes('用户')"
    v-model="formData[column.javaField]"
  />

  <!-- 2. 部门选择器 -->
  <DeptSelect
    v-else-if="column.javaField === 'deptId' || column.columnComment?.includes('部门')"
    v-model="formData[column.javaField]"
  />

  <!-- 3. 字典下拉框 -->
  <el-select
    v-else-if="column.dictType"
    v-model="formData[column.javaField]"
  >
    <el-option
      v-for="dict in getDictOptions(column.dictType)"
      :key="dict.value"
      :label="dict.label"
      :value="dict.value"
    />
  </el-select>

  <!-- 4. 默认：富文本/日期/输入框 -->
  <editor v-else-if="column.htmlType === 'editor'" v-model="formData[column.javaField]" />
  <el-date-picker v-else-if="column.htmlType === 'datetime'" v-model="formData[column.javaField]" />
  <el-input v-else v-model="formData[column.javaField]" />
</el-form-item>
```

**解读**：
- 通过 `v-if/v-else-if` 链式判断**优先级**：
  1. 用户/部门（特殊业务组件）
  2. 字典（数据驱动）
  3. 富文本/日期（特殊控件）
  4. 普通输入框（兜底）

### 3.3 列表字典展示

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/vue3/views/index.vue.vm`
**关键代码片段**：

```vue
<el-table-column :prop="column.javaField" :label="column.columnComment">
  <template #default="{ row }">
    <!-- 字典字段展示 -->
    <dict-tag
      v-if="column.dictType"
      :type="column.dictType"
      :value="row[column.javaField]"
    />
    <!-- 普通字段直接展示 -->
    <span v-else>{{ row[column.javaField] }}</span>
  </template>
</el-table-column>
```

**解读**：
- 列表中用 `<dict-tag>` 组件显示字典值对应的中文
- 这个组件是 ruoyi 提供的全局组件，会去缓存中查询 `dictDataMap.get(dictType).get(value)`

## 4. 关键要点总结

- 字典字段 = `dictType` 不为空 → 自动用下拉框
- 字段名 `userId` / 注释含"用户" → 自动用 `UserSelect` 组件
- 字段名 `deptId` / 注释含"部门" → 自动用 `DeptSelect` 组件
- 字典数据通过 `getIntDictOptions` / `getStrDictOptions` / `getDictLabel` 三个函数获取
- 列表展示用 `<dict-tag>` 组件自动翻译

## 5. 练习题

### 练习 1：基础（必做）

打开 `form.vue.vm`，画出"如果字段是 `phone`（普通字段）" 会命中哪个分支，最终渲染什么组件。

### 练习 2：进阶

新增一个"地区选择器"组件（`RegionSelect`），要求字段名以 `regionId` 结尾时自动使用它。需要修改 `form.vue.vm` 的哪一行？写出修改后的 v-if 链。

### 练习 3：挑战（选做）

设计一个 `column.dictType` 与 `column.htmlType` 联合判断的映射表（如：字典 + radio / 字典 + select），让用户可以决定字典是"下拉"还是"单选"。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/vue3/views/form.vue.vm`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/vue3/views/index.vue.vm`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/dal/dataobject/codegen/CodegenColumnDO.java`
- 官方文档：https://doc.iocoder.cn/codegen/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
