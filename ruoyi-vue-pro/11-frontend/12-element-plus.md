# 11.3.1 Element Plus 基础组件

> 掌握 Element Plus 常用组件（Button、Input、Dialog、Message）的用法，能在 ruoyi 中快速搭建业务页面。

## 🎯 学习目标

完成本文档后，你将能够：
- 使用 Element Plus 的常用基础组件
- 理解 `v-model` / `slot` / `event` 在 Element Plus 中的约定
- 调用全局方法（ElMessage、ElMessageBox、ElNotification）
- 能在 ruoyi 中用 Element Plus 组件搭建 CRUD 页面

## 📚 前置知识

- Vue3 基础（详见 [Vue3 基础](./01-vue3-basics.md)）
- Vue 模板语法基础

## 1. 核心概念

### 1.1 什么是 Element Plus？

Element Plus 是基于 Vue 3 的桌面端 UI 组件库，由饿了么团队维护。**ruoyi-vue-pro 默认使用 Element Plus**。

特点：
- 组件丰富（80+ 组件，覆盖表格、表单、弹窗、菜单等）
- 主题可定制（CSS 变量）
- TypeScript 原生支持
- Tree-shaking 友好（按需导入）

### 1.2 安装与按需引入

```bash
pnpm install element-plus
```

```ts
// main.ts（ruoyi 实际风格）
import { ElButton, ElInput, ElForm, ElMessage } from 'element-plus'
import 'element-plus/dist/index.css'

// 全局注册（简单）
app.use(ElementPlus)

// 按需注册（性能好，推荐）
app.use(ElButton).use(ElInput).use(ElForm)
```

### 1.3 全局方法

Element Plus 的 `ElMessage`、`ElMessageBox`、`ElNotification` 是**全局函数**，组件内部用 `useMessage` 包装：

```ts
import { ElMessage, ElMessageBox } from 'element-plus'

// 简单提示
ElMessage.success('操作成功')
ElMessage.error('操作失败')
ElMessage.warning('警告')

// 确认弹框
try {
  await ElMessageBox.confirm('确定删除？', '提示', { type: 'warning' })
  // 用户点击确定
} catch {
  // 用户点击取消
}

// 通知（带标题）
ElNotification({
  title: '通知',
  message: '你有一条新消息',
  type: 'success'
})
```

### 1.4 常用组件一览

| 组件 | 用途 | 关键 props |
|------|------|-----------|
| `el-button` | 按钮 | `type`、`size`、`loading`、`disabled` |
| `el-input` | 输入框 | `v-model`、`placeholder`、`clearable`、`prefix-icon` |
| `el-select` / `el-option` | 下拉选择 | `v-model` |
| `el-form` / `el-form-item` | 表单 | `:model`、`:rules`、`ref` |
| `el-table` / `el-table-column` | 表格 | `:data`、`:columns`、`stripe`、`border` |
| `el-dialog` | 弹窗 | `v-model`、`title`、`width` |
| `el-pagination` | 分页 | `:total`、`v-model:current-page`、`v-model:page-size` |
| `el-date-picker` | 日期选择 | `v-model`、`type`、`value-format` |
| `el-menu` / `el-sub-menu` / `el-menu-item` | 导航菜单 | `default-active` |
| `el-tag` | 标签 | `type`、`effect` |
| `el-tree` | 树形控件 | `:data`、`node-key` |

### 1.5 v-model 与组件

Element Plus 组件几乎全部支持 `v-model`：

```vue
<el-input v-model="form.name" />
<el-select v-model="form.sex">
  <el-option label="男" :value="1" />
  <el-option label="女" :value="2" />
</el-select>
<el-switch v-model="form.enable" />
<el-date-picker v-model="form.date" type="date" />
```

### 1.6 插槽

复杂内容用 `<template #xxx>` 插槽：

```vue
<el-table :data="list">
  <el-table-column label="操作">
    <template #default="scope">
      <!-- scope.row 当前行数据，scope.$index 当前行下标 -->
      <el-button @click="handleEdit(scope.row)">编辑</el-button>
      <el-button type="danger" @click="handleDelete(scope.row)">删除</el-button>
    </template>
  </el-table-column>
</el-table>
```

## 2. 代码示例

### 2.1 用户卡片（基础组件组合）

```vue
<script setup lang="ts">
import { ref } from 'vue'

const name = ref('')
const sex = ref<number>(1)
const enable = ref(true)
</script>

<template>
  <el-form label-width="80px">
    <el-form-item label="姓名">
      <el-input v-model="name" placeholder="请输入姓名" clearable />
    </el-form-item>
    <el-form-item label="性别">
      <el-select v-model="sex">
        <el-option label="男" :value="1" />
        <el-option label="女" :value="2" />
      </el-select>
    </el-form-item>
    <el-form-item label="启用">
      <el-switch v-model="enable" />
    </el-form-item>
    <el-form-item>
      <el-button type="primary" @click="onSubmit">提交</el-button>
      <el-button @click="onReset">重置</el-button>
    </el-form-item>
  </el-form>
</template>
```

### 2.2 删除确认弹框

```vue
<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm(
      `确定删除 ID 为 ${id} 的记录？`,
      '提示',
      { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' }
    )
    // 调删除 API
    await api.delete(id)
    ElMessage.success('删除成功')
  } catch {
    // 用户取消，无需处理
  }
}
</script>
```

### 2.3 弹窗组件

```vue
<script setup lang="ts">
import { ref } from 'vue'

const visible = ref(false)
const form = ref({ name: '' })

function open() { visible.value = true }
function close() { visible.value = false }
</script>

<template>
  <el-button @click="open">打开弹窗</el-button>
  <el-dialog v-model="visible" title="编辑用户" width="500px">
    <el-input v-model="form.name" />
    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" @click="onSave">保存</el-button>
    </template>
  </el-dialog>
</template>
```

### 2.4 常见错误：忘记引入样式

```ts
// ❌ 错误：只引入了组件，没引入样式
import { ElButton } from 'element-plus'
app.use(ElButton)

// ✅ 正确：样式必须导入
import 'element-plus/dist/index.css'
```

## 3. 关键要点总结

- Element Plus = Vue3 桌面端组件库，ruoyi 默认使用
- 几乎所有组件都支持 `v-model`
- 全局方法：`ElMessage.success/error`、`ElMessageBox.confirm`、`ElNotification`
- `el-form` 用 `:model + :rules + ref` 三件套做校验
- `el-dialog` 的 footer 用 `<template #footer>` 插槽
- ruoyi 二次封装：`useMessage()` 返回的对象有 `delConfirm()`、`exportConfirm()` 等业务方法
- 图标用 `<Icon icon="ep:xxx" />`（基于 Iconify）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
