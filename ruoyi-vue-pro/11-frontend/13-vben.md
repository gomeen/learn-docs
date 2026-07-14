# 11.3.4 Vben Admin：ant-design-vue

> 了解 Vben Admin（基于 ant-design-vue 的 Vue3 后台模板），理解它与 Element Plus 版本的差异。

## 🎯 学习目标

完成本文档后，你将能够：
- 了解 Vben Admin 的定位与特点
- 掌握 ant-design-vue 的核心组件（a-table、a-form）
- 区分 Vben 版本与 Element Plus 版本的适用场景
- 能在 ruoyi 体系下选型

## 📚 前置知识

- 11-frontend/10-element-plus.md
- React/Vue 组件库基础知识

## 1. 核心概念

### 1.1 什么是 Vben Admin？

Vben Admin 是 ruoyi-vue-pro 提供的**另一套前端模板**，基于：
- **Vue 3** + **TypeScript** + **Vite**
- **ant-design-vue 4.x**（Ant Design 的 Vue 实现）
- 大量企业级最佳实践（封装、权限、国际化、主题）

**仓库地址**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vben/`

### 1.2 Vben 版本 vs Element Plus 版本

| 维度 | yudao-ui-admin-vue3 | yudao-ui-admin-vben |
|------|---------------------|---------------------|
| UI 库 | Element Plus | ant-design-vue |
| 风格 | 简洁、现代 | 企业级、商务 |
| 文档 | 中文友好（饿了么维护） | 中文/英文（Ant Design 体系） |
| 组件丰富度 | 高（80+） | 极高（100+，源自 Ant Design） |
| 主题定制 | CSS 变量 | ConfigProvider + Token |
| 上手难度 | 低 | 中 |
| 适用场景 | 中小型项目、快速开发 | 大型企业项目、深度定制 |

### 1.3 ant-design-vue 核心组件对照

| 业务场景 | Element Plus | ant-design-vue |
|---------|--------------|----------------|
| 按钮 | `el-button` | `a-button` |
| 输入框 | `el-input` | `a-input` |
| 表单 | `el-form` | `a-form` |
| 表格 | `el-table` | `a-table` |
| 分页 | `el-pagination` | `a-pagination` |
| 弹窗 | `el-dialog` | `a-modal` |
| 下拉 | `el-select` | `a-select` |
| 树 | `el-tree` | `a-tree` |
| 上传 | `el-upload` | `a-upload` |
| 图标 | 自定义 | `iconfont`（自带大量图标） |

### 1.4 Vben 版本的目录结构（约定）

```
yudao-ui-admin-vben/
├── src/
│   ├── api/                  # 接口定义（与 Vue3 版本一致）
│   ├── views/                # 页面（按业务模块组织）
│   ├── components/           # 自研组件（基于 ant-design-vue 二次封装）
│   ├── layouts/              # 布局（多套主题）
│   ├── router/
│   │   ├── routes/           # 静态路由 + 动态路由模块
│   │   └── guard/            # 路由守卫（权限）
│   ├── store/modules/        # Pinia store
│   ├── utils/                # 工具
│   ├── hooks/                # 自研 composables
│   ├── design/               # 主题、样式变量
│   └── settings/             # 项目配置（标题、logo、API 地址）
```

### 1.5 Vben 的"高级"特性

| 特性 | 说明 |
|------|------|
| 多套布局 | 默认、横向、纵向、混合 |
| 主题切换 | 明暗主题、主题色、紧凑模式 |
| 国际化 | 内置 vue-i18n + 多语言包 |
| 权限 | 数据权限 + 按钮权限 + 菜单权限 |
| 代码生成 | 后端配置后前端自动生成页面 |
| 多租户 | 顶部租户切换 |

## 2. 代码示例

### 2.1 ant-design-vue 按钮

```vue
<script setup lang="ts">
import { Button } from 'ant-design-vue'
</script>

<template>
  <a-button type="primary">主要按钮</a-button>
  <a-button type="default">默认按钮</a-button>
  <a-button type="dashed">虚线按钮</a-button>
  <a-button type="text">文字按钮</a-button>
  <a-button type="link">链接按钮</a-button>
  <a-button danger>危险按钮</a-button>
</template>
```

### 2.2 ant-design-vue 表单

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { Form, FormItem, Input, Button } from 'ant-design-vue'

const formRef = ref()
const formState = ref({ name: '', email: '' })

const rules = {
  name: [{ required: true, message: '姓名不能为空' }],
  email: [{ type: 'email', message: '邮箱格式不正确' }]
}

async function onFinish() {
  await formRef.value?.validate()
  console.log('提交', formState.value)
}
</script>

<template>
  <a-form ref="formRef" :model="formState" :rules="rules" label-width="100">
    <a-form-item label="姓名" name="name">
      <a-input v-model:value="formState.name" />
    </a-form-item>
    <a-form-item label="邮箱" name="email">
      <a-input v-model:value="formState.email" />
    </a-form-item>
    <a-form-item>
      <a-button type="primary" @click="onFinish">提交</a-button>
    </a-form-item>
  </a-form>
</template>
```

### 2.3 ant-design-vue 表格

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface User { id: number; name: string; status: number }

const list = ref<User[]>([])
const loading = ref(false)
const pagination = ref({ total: 0, current: 1, pageSize: 10 })

async function getList() {
  loading.value = true
  try {
    const res = await api.getUserPage({
      pageNo: pagination.value.current,
      pageSize: pagination.value.pageSize
    })
    list.value = res.list
    pagination.value.total = res.total
  } finally {
    loading.value = false
  }
}

onMounted(getList)
</script>

<template>
  <a-table
    :dataSource="list"
    :loading="loading"
    :pagination="pagination"
    row-key="id"
    @change="(pag) => { pagination = pag; getList() }"
  >
    <a-table-column title="ID" dataIndex="id" />
    <a-table-column title="姓名" dataIndex="name" />
    <a-table-column title="状态" dataIndex="status">
      <template #default="{ record }">
        <a-tag :color="record.status === 1 ? 'green' : 'default'">
          {{ record.status === 1 ? '启用' : '禁用' }}
        </a-tag>
      </template>
    </a-table-column>
  </a-table>
</template>
```

### 2.4 Element Plus vs ant-design-vue 的关键差异

| 行为 | Element Plus | ant-design-vue |
|------|--------------|----------------|
| 组件前缀 | `el-` | `a-` |
| v-model 指令 | `v-model` | `v-model:value` |
| 表格数据 prop | `prop` | `dataIndex` |
| 表格列容器 | `<el-table-column>` | `<a-table-column>` |
| 插槽作用域 | `#default="scope"` | `#default="{ record }"` |
| 确认框 | `ElMessageBox.confirm` | `Modal.confirm` |
| 消息提示 | `ElMessage.success` | `message.success` |
| 表单 ref 类型 | `FormInstance` | `FormInstance` |

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 Vben 子项目位置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vben/`

```bash
# 公开仓库地址
# Gitee: https://gitee.com/yudaocode/yudao-ui-admin-vben
# GitHub: https://github.com/yudaocode/yudao-ui-admin-vben
```

**注意**：本仓库的 `yudao-ui-admin-vben` 目录是独立的 git submodule 仓库（只有 README.md），实际代码需要单独克隆。**但接口约定（`/src/api/`）与 Vue3 版本完全一致**。

### 3.2 接口对接的一致性

无论用 Vue3+Element Plus 还是 Vben+ant-design-vue，**后端 API 完全一致**：

```ts
// Vue3 版本（api/mes/wm/sn/index.ts）
export const WmSnApi = {
  getSnPage: async (params: any) => {
    return await request.get({ url: '/mes/wm/sn/page', params })
  }
}

// Vben 版本（api/mes/wm/sn/index.ts）—— 接口签名相同
export const getSnPage = (params: any) => {
  return requestClient.get('/mes/wm/sn/page', { params })
}
```

**好处**：业务后端只提供一套 REST 接口，前端选型自由。

### 3.3 Vben 版本的约定文件

根据公开约定，Vben 版本的关键约定文件：

```ts
// src/settings/projectSetting.ts
export default {
  title: '芋道管理后台',
  theme: 'light',                  // light / dark
  layout: 'default',               // default / mixin / side
  showBreadcrumb: true,
  showLogo: true,
  // ...
}
```

```ts
// src/api/system/user.ts（与 Vue3 版本方法名一致）
export const getUserInfo = () => {
  return requestClient.get('/system/user/get-info')
}
```

## 4. 关键要点总结

- Vben Admin = Vue3 + TypeScript + ant-design-vue + Vite
- 与 Element Plus 版本**接口一致**，仅 UI 层不同
- ant-design-vue 组件前缀 `a-`，v-model 用 `v-model:value`
- Vben 适合大型企业项目、深度定制、多主题
- Vue3+Element Plus 适合中小型项目、快速开发、中文社区
- **选型建议**：看团队熟悉度 + 设计风格偏好，两者都能撑起商业项目

## 5. 练习题

### 练习 1：基础（必做）

把 SN 码管理页（Element Plus 版本）改写为 ant-design-vue 版本：把 `el-form` 改成 `a-form`，`el-table` 改成 `a-table`，`el-button` 改成 `a-button`。注意 v-model 写法差异。

### 练习 2：进阶

对比 Element Plus 的 `Pagination` 和 ant-design-vue 的 `a-pagination`，列出 API 差异（参数名、事件名）。

### 练习 3：挑战（选做）

为 Vue3+Element Plus 版本写一套"主题切换"功能：明暗主题、紧凑模式、主题色（绿/蓝/紫），配置存 localStorage。

## 6. 参考资料

- yudao-ui-admin-vben 公开仓库：https://github.com/yudaocode/yudao-ui-admin-vben
- ant-design-vue 官方文档：https://antdv.com/zh-CN/docs/introduce
- Vben Admin 文档：https://doc.iocoder.cn/

---

**文档版本**：v1.0
**最后更新**：2026-07-13