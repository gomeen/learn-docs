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

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 SN 码页面：完整的 Element Plus 组件应用

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`
**核心代码**（行 1-72，搜索栏）：

```vue
<template>
  <ContentWrap>
    <el-form
      class="-mb-15px"
      :model="queryParams"
      ref="queryFormRef"
      :inline="true"
      label-width="68px"
    >
      <el-form-item label="SN 码" prop="snCode">
        <el-input
          v-model="queryParams.snCode"
          placeholder="请输入 SN 码"
          clearable
          @keyup.enter="handleQuery"
          class="!w-240px"
        />
      </el-form-item>
      <el-form-item label="物料ID" prop="itemId">
        <el-input
          v-model="queryParams.itemId"
          placeholder="请输入物料ID"
          clearable
          @keyup.enter="handleQuery"
          class="!w-240px"
        />
      </el-form-item>
      <el-form-item label="创建时间" prop="createTime">
        <el-date-picker
          v-model="queryParams.createTime"
          value-format="YYYY-MM-DD HH:mm:ss"
          type="daterange"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          :default-time="[new Date('1 00:00:00'), new Date('1 23:59:59')]"
          class="!w-240px"
        />
      </el-form-item>
      <el-form-item>
        <el-button @click="handleQuery">
          <Icon icon="ep:search" class="mr-5px" /> 搜索
        </el-button>
        <el-button @click="resetQuery">
          <Icon icon="ep:refresh" class="mr-5px" /> 重置
        </el-button>
        <el-button
          type="primary"
          plain
          @click="openForm()"
          v-hasPermi="['mes:wm-sn:create']"
        >
          <Icon icon="ep:plus" class="mr-5px" /> 生成 SN 码
        </el-button>
      </el-form-item>
    </el-form>
  </ContentWrap>
</template>
```

**解读**：
- 第 2 行：`<ContentWrap>` 是 ruoyi 自定义的白色卡片容器（自带 padding 和 margin）
- 第 4 行：`-mb-15px` 是 UnoCSS/Tailwind 的原子类（负 margin-bottom）
- 第 6 行：`:model="queryParams"` 绑定响应式对象
- 第 7 行：`ref="queryFormRef"` 模板 ref，调 `resetFields()` 用
- 第 17 行：`@keyup.enter="handleQuery"` 回车触发搜索
- 第 19 行：`class="!w-240px"` 是 UnoCSS 原子类（`!` 前缀表示 important）
- 第 32-37 行：`el-date-picker` 范围选择，`value-format` 统一格式
- 第 39 行：`type="daterange"` 是范围模式
- 第 41-42 行：`:default-time` 设置默认时分秒
- 第 53 行：`v-hasPermi` 是 ruoyi 自定义指令，做按钮权限控制
- 第 55 行：`<Icon icon="ep:xxx" />` 是 ruoyi 包装的图标组件

### 3.2 弹窗表单

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`
**核心代码**（行 111-127）：

```vue
<el-dialog :title="'生成 SN 码'" v-model="dialogVisible" width="600px">
  <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px">
    <el-form-item label="物料ID" prop="itemId">
      <el-input-number v-model="formData.itemId" :min="1" controls-position="right" class="!w-full" />
    </el-form-item>
    <el-form-item label="批次号" prop="batchCode">
      <el-input v-model="formData.batchCode" placeholder="请输入批次号" maxlength="100" />
    </el-form-item>
    <el-form-item label="生成数量" prop="snNum">
      <el-input-number v-model="formData.snNum" :min="1" :max="1000" />
    </el-form-item>
  </el-form>
  <template #footer>
    <el-button @click="dialogVisible = false">取消</el-button>
    <el-button type="primary" @click="submitForm" :loading="formLoading">确定</el-button>
  </template>
</el-dialog>
```

**解读**：
- 第 1 行：`v-model="dialogVisible"` 双向控制弹窗显示
- 第 2 行：`:rules="formRules"` 绑定校验规则
- 第 4 行：`prop="itemId"` 与 rules 的字段名一一对应
- 第 5 行：`el-input-number` 是数字输入框，`controls-position="right"` 按钮在右
- 第 14 行：`<template #footer>` 是 `el-dialog` 的 footer 插槽
- 第 16 行：`:loading="formLoading"` 提交时按钮显示 loading

### 3.3 删除确认（useMessage 模式）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`
**核心代码**（行 224-231）：

```ts
/** 删除按钮操作 */
const handleDelete = async (id: number) => {
  try {
    await message.delConfirm()
    await WmSnApi.deleteSnBatch(String(id))
    message.success('删除成功')
    await getList()
  } catch {}
}
```

**解读**：
- 第 4 行：`message.delConfirm()` 是 ruoyi 封装的确认框（默认提示语：确定删除？）
- 第 5 行：调删除 API
- 第 6 行：`message.success()` 是成功提示
- 第 8 行：`catch {}` —— 用户取消时不做任何事（vs 直接 `try`/`catch` 抛错）

## 4. 关键要点总结

- Element Plus = Vue3 桌面端组件库，ruoyi 默认使用
- 几乎所有组件都支持 `v-model`
- 全局方法：`ElMessage.success/error`、`ElMessageBox.confirm`、`ElNotification`
- `el-form` 用 `:model + :rules + ref` 三件套做校验
- `el-dialog` 的 footer 用 `<template #footer>` 插槽
- ruoyi 二次封装：`useMessage()` 返回的对象有 `delConfirm()`、`exportConfirm()` 等业务方法
- 图标用 `<Icon icon="ep:xxx" />`（基于 Iconify）

## 5. 练习题

### 练习 1：基础（必做）

用 Element Plus 组件搭一个"用户反馈表单"：姓名、邮箱、问题类型（下拉）、问题描述（textarea）、提交按钮。

### 练习 2：进阶

为 SN 码页的"导出 Excel"按钮增加确认弹框（用 `useMessage().exportConfirm()`），确认后调用 `exportSnExcel` 接口，并显示 loading。

### 练习 3：挑战（选做）

为 Element Plus 自定义主题色：把主色从 `#409EFF` 改为 `#1890ff`（蓝），通过 CSS 变量覆盖（提示：`:root { --el-color-primary: #1890ff }`）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`
- Element Plus 官方文档：https://element-plus.org/zh-CN/
- Element Plus 组件总览：https://element-plus.org/zh-CN/component/overview.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13