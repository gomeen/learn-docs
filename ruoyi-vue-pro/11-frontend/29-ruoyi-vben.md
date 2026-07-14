# 11.6.7 Vben 版本：ant-design-vue 实战

> 深入了解 Vben 版本（ant-design-vue）的实战开发，与 Element Plus 版本的差异点对照。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 Vben 版本和 Vue3+Element Plus 版本的实现差异
- 在 Vben 版本下编写 CRUD 页面
- 使用 Vben 自研的 `useTable` / `useForm` 等 composables
- 理解 ant-design-vue 的 API 风格

## 📚 前置知识

- 11-frontend/13-vben.md
- 11-frontend/19-axios.md
- 11-frontend/25-ruoyi-button-permission.md

## 1. 核心概念

### 1.1 Vben 版本的定位

`yudao-ui-admin-vben` 是 ruoyi-vue-pro 的**进阶前端**，定位于**大型企业项目**：
- Vue 3 + Vite + TypeScript
- **ant-design-vue 4.x**（替代 Element Plus）
- 大量自研 composables（`useTable`、`useForm`、`useMessage`）
- 高度模块化

### 1.2 与 Element Plus 版本的关键差异

| 维度 | Vue3+Element Plus | Vben+ant-design-vue |
|------|-------------------|---------------------|
| UI 组件前缀 | `el-` | `a-` |
| v-model | `v-model` | `v-model:value` |
| 表格数据 prop | `prop` | `dataIndex` |
| 表格插槽作用域 | `#default="scope"` | `#default="{ record }"` |
| 弹窗组件 | `el-dialog` | `a-modal` |
| 表单 ref 类型 | `FormInstance` | `FormInstance` |
| 消息提示 | `ElMessage` | `message` |
| 确认框 | `ElMessageBox` | `Modal.confirm` |

### 1.3 Vben 的特色 composables

| composable | 作用 |
|-----------|------|
| `useTable` | 表格通用逻辑（loading、分页、查询、刷新） |
| `useForm` | 表单通用逻辑（验证、提交、重置） |
| `useMessage` | 消息提示（封装 ant-design-vue message） |
| `useI18n` | 国际化 |
| `useDesign` | 获取组件作用域（用于 scoped CSS） |

### 1.4 目录约定

```
yudao-ui-admin-vben/
├── src/
│   ├── api/
│   │   └── mes/
│   │       └── wm/
│   │           ├── sn/
│   │           │   └── index.ts        # 与 Vue3 版本完全一致
│   │           └── productreceipt/
│   ├── views/
│   │   └── mes/
│   │       └── wm/
│   │           ├── sn/
│   │           │   ├── index.vue       # 列表页（用 a-table）
│   │           │   └── data.ts         # 表单 + 表格 + 搜索 schema
│   │           └── productrecpt/
│   ├── components/
│   │   ├── Table/                      # 通用表格组件（Vben 自研）
│   │   ├── Form/                       # 通用表单组件
│   │   └── Modal/                      # 通用弹窗
│   └── hooks/
│       ├── useTable.ts
│       └── useForm.ts
```

## 2. 代码示例

### 2.1 接口定义（与 Vue3 版本一致）

```ts
// src/api/mes/wm/sn/index.ts（Vben 版本）
import request from '@/utils/request'

export const getSnPage = (params: any) => {
  return request.get({ url: '/mes/wm/sn/page', params })
}

export const createSn = (data: any) => {
  return request.post({ url: '/mes/wm/sn/create', data })
}

export const updateSn = (data: any) => {
  return request.put({ url: '/mes/wm/sn/update', data })
}

export const deleteSn = (id: number) => {
  return request.delete({ url: `/mes/wm/sn/delete?id=${id}` })
}
```

**差异**：Vben 版本通常**每个方法单独 export**（不打包成对象），便于 tree-shaking。

### 2.2 列表页：Vben 风格

```vue
<!-- src/views/mes/wm/sn/index.vue -->
<script setup lang="ts">
import { columns, searchFormSchema } from './data'
import { getSnPage, deleteSn } from '@/api/mes/wm/sn'
import { useTable } from '@/hooks/useTable'

const message = useMessage()

const [registerTable] = useTable({
  api: getSnPage,
  columns,
  rowKey: 'id',
  // 搜索栏配置
  formConfig: {
    schemas: searchFormSchema,
    labelWidth: 100
  },
  // 操作列
  actionColumn: {
    width: 200,
    title: '操作',
    dataIndex: 'action'
  }
})

async function handleDelete(id: number) {
  await deleteSn(id)
  message.success('删除成功')
  // 自动刷新表格
}
</script>

<template>
  <div class="p-4">
    <BasicTable @register="registerTable">
      <template #toolbar>
        <a-button type="primary" @click="handleCreate">新增</a-button>
      </template>
      <template #bodyCell="{ column, record }">
        <template v-if="column.dataIndex === 'action'">
          <a-button type="link" size="small" @click="handleEdit(record)">编辑</a-button>
          <a-popconfirm @confirm="handleDelete(record.id)">
            <template #default><a-button type="link" size="small" danger>删除</a-button></template>
          </a-popconfirm>
        </template>
      </template>
    </BasicTable>
  </div>
</template>
```

### 2.3 data.ts：配置式表单 + 表格

```ts
// src/views/mes/wm/sn/data.ts
import { FormSchema } from '@/components/Form'

// 搜索栏字段
export const searchFormSchema: FormSchema[] = [
  { field: 'snCode', label: 'SN 码', component: 'Input', colProps: { span: 6 } },
  { field: 'itemId', label: '物料 ID', component: 'Input', colProps: { span: 6 } },
  { field: 'createTime', label: '创建时间', component: 'DatePicker', colProps: { span: 8 } }
]

// 表格列
export const columns = [
  { title: 'SN 码', dataIndex: 'snCode', width: 180 },
  { title: '物料编码', dataIndex: 'itemCode', width: 120 },
  { title: '物料名称', dataIndex: 'itemName', width: 150 },
  { title: '规格型号', dataIndex: 'specification', width: 120 },
  { title: '批次号', dataIndex: 'batchCode', width: 120 },
  { title: '生成时间', dataIndex: 'createTime', width: 180 },
  { title: '操作', dataIndex: 'action', width: 120, fixed: 'right' }
]
```

### 2.4 useTable composable

```ts
// hooks/useTable.ts
export function useTable(options: UseTableOptions) {
  const tableData = ref<any[]>([])
  const loading = ref(false)
  const total = ref(0)
  const queryParams = reactive({ pageNo: 1, pageSize: 10 })

  async function fetchData() {
    loading.value = true
    try {
      const res = await options.api({ ...queryParams })
      tableData.value = res.list
      total.value = res.total
    } finally {
      loading.value = false
    }
  }

  function reload() { fetchData() }

  // 注册到全局的 BasicTable
  return [register, { reload }]
}
```

### 2.5 权限指令 v-hasPermi（Vben 版本）

```ts
// 引入 usePermission composable
import { usePermission } from '@/hooks/web/usePermission'

const { hasPermission } = usePermission()
</script>

<template>
  <a-button v-if="hasPermission('mes:wm-sn:create')" type="primary">
    新增
  </a-button>
</template>
```

Vben 版本**不用 v-hasPermi 指令**，而是用 `usePermission().hasPermission()` 函数式判断。

### 2.6 常见错误：组件前缀混用

```vue
<!-- ❌ 错误：混用 el 和 a 组件 -->
<a-form>
  <el-input v-model="value" />  <!-- 错！应该用 a-input -->
</a-form>

<!-- ✅ 正确：统一用 a 组件 -->
<a-form>
  <a-input v-model:value="value" />
</a-form>
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 Vben 仓库位置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vben/`

本仓库的 Vben 子项目是独立仓库（只有 README.md）。完整代码需从公开仓库获取：

```
# Gitee: https://gitee.com/yudaocode/yudao-ui-admin-vben
# GitHub: https://github.com/yudaocode/yudao-ui-admin-vben
```

### 3.2 接口定义一致性

虽然 Vben 版本的 UI 完全不同，但**接口定义方法签名一致**：

```ts
// 两个版本的请求 URL 完全相同：
// /mes/wm/sn/page
// /mes/wm/sn/get?id=xxx
// /mes/wm/sn/create
// /mes/wm/sn/update
// /mes/wm/sn/delete?id=xxx
```

**好处**：业务后端只提供一套 REST 接口，前端选型自由。

### 3.3 Vben 版本的特性

**1. 配置化开发**：

Vben 把"搜索表单"和"表格列"抽到 `data.ts` 里**纯配置**，模板只负责事件绑定：

```ts
// data.ts 配置搜索栏
export const searchFormSchema = [
  { field: 'snCode', label: 'SN 码', component: 'Input' }
]

// 模板只引用
<BasicForm :schemas="searchFormSchema" />
```

**好处**：模板非常简洁，复杂逻辑都在 composables 里。

**2. 权限用 composable**：

```ts
// Vue3+Element Plus 版本
<el-button v-hasPermi="['mes:wm-sn:create']">新增</el-button>

// Vben 版本
const { hasPermission } = usePermission()
<a-button v-if="hasPermission('mes:wm-sn:create')">新增</a-button>
```

**3. 路由组织**：

Vben 用"模块化路由"：

```
src/router/routes/modules/
├── bpm.ts
├── infra.ts
├── mes.ts
└── system.ts
```

每个文件是一个模块，里面声明路由 + meta + 权限。

### 3.4 与本仓库代码的关联

本仓库 `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/api/mes/wm/sn/index.ts` 是 Vue3+Element Plus 版本的接口定义。如果切换到 Vben 版本，**这段代码 90% 不变**，只需把 `WmSnApi` 对象改成单独 export 的函数。

## 4. 关键要点总结

- Vben 版本 = Vue3 + ant-design-vue + 大量自研 composables
- 接口定义方法名一致，URL 一致，只是代码组织方式不同
- Vben 用**配置化开发**：搜索表单、表格列都用 schema 配置
- Vben 用 `usePermission()` composable，Vue3 版本用 `v-hasPermi` 指令
- 选型：中小项目用 Vue3+Element Plus，大型企业项目用 Vben
- 后端 REST 接口完全一致，前端切换成本低

## 5. 练习题

### 练习 1：基础（必做）

把 SN 码管理页的 Vue3+Element Plus 版本**手动翻译**为 Vben+ant-design-vue 版本：把 `el-form` 改成 `a-form`、`el-table` 改成 `a-table`、`el-button` 改成 `a-button`。

### 练习 2：进阶

在 Vben 版本下实现"搜索栏 + 表格"的配置化开发：用 `searchFormSchema` 和 `columns` 数组声明所有字段，模板只引用。

### 练习 3：挑战（选做）

对比 Vben 的 `BasicTable` 组件和 Element Plus 的 `el-table`，列出 10 个 API 差异点（参数名、事件名、插槽名等）。

## 6. 参考资料

- yudao-ui-admin-vben 公开仓库：https://github.com/yudaocode/yudao-ui-admin-vben
- ant-design-vue 官方文档：https://antdv.com/
- Vben Admin 文档：https://doc.vben.pro/

---

**文档版本**：v1.0
**最后更新**：2026-07-13