# 2.3 字典/枚举/用户组件

> 学习 ruoyi 代码生成器对字典、枚举、用户等"特殊字段"的组件配置。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释字典字段如何自动生成下拉框
- 解释"用户/部门"字段如何生成远程搜索下拉
- 解释"枚举"字段如何生成 radio/select
- 自定义一个新的"特殊组件"（如地区选择器）

## 📚 前置知识

- 类型映射 / 字段配置（详见 [类型映射](./04-type-mapping.md)、[字段配置](./07-field-config.md)）
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

## 3. 关键要点总结

- 字典字段 = `dictType` 不为空 → 自动用下拉框
- 字段名 `userId` / 注释含"用户" → 自动用 `UserSelect` 组件
- 字段名 `deptId` / 注释含"部门" → 自动用 `DeptSelect` 组件
- 字典数据通过 `getIntDictOptions` / `getStrDictOptions` / `getDictLabel` 三个函数获取
- 列表展示用 `<dict-tag>` 组件自动翻译

---

**文档版本**：v1.0
**最后更新**：2026-07-13
