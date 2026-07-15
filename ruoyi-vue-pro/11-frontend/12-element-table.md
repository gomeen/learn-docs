# 11.3.3 Table 组件：分页/排序/筛选

> 掌握 Element Plus 表格组件的高级用法：分页、排序、筛选、多选、行操作、列格式化，能在 ruoyi 中实现完整的 CRUD 列表。

## 🎯 学习目标

完成本文档后，你将能够：
- 配置 el-table 的分页（el-pagination）、排序、筛选
- 处理多选、单选、行操作
- 自定义列渲染（插槽、formatter）
- 实现完整的 ruoyi CRUD 列表页

## 📚 前置知识

- Element Plus / Form（详见 [Element Plus](./10-element-plus.md)、[Element Form](./11-element-form.md)）

## 1. 核心概念

### 1.1 el-table 三件套

```vue
<el-table
  :data="list"           <!-- 数据源 -->
  v-loading="loading"    <!-- 加载中遮罩 -->
  stripe                 <!-- 斑马纹 -->
  border                 <!-- 边框 -->
>
  <el-table-column prop="id" label="ID" width="80" />
  <el-table-column prop="name" label="姓名" />
  <el-table-column label="操作" width="180" fixed="right">
    <template #default="scope">
      <el-button @click="handleEdit(scope.row)">编辑</el-button>
    </template>
  </el-table-column>
</el-table>
```

### 1.2 表格列的常用配置

| 属性 | 作用 |
|------|------|
| `prop` | 字段名（自动取 row[prop]） |
| `label` | 列标题 |
| `width` | 列宽（像素） |
| `min-width` | 最小列宽 |
| `fixed` | 固定列（`'left'`/`'right'`） |
| `sortable` | 是否可排序 |
| `align` | 对齐方式 |
| `formatter` | 自定义格式化函数 |
| `show-overflow-tooltip` | 内容过长省略 |

### 1.3 排序

```vue
<el-table
  :data="list"
  @sort-change="onSortChange"   <!-- 排序变化 -->
>
  <el-table-column prop="createTime" label="创建时间" sortable="custom" />
</el-table>
```

```ts
const sortParams = ref({ orderByColumn: undefined, isAsc: undefined })

function onSortChange({ prop, order }) {
  sortParams.orderByColumn = prop
  sortParams.isAsc = order === 'ascending' ? 'asc' : 'desc'
  getList()
}
```

### 1.4 筛选（列头下拉）

```vue
<el-table-column prop="status" label="状态" :filters="[
  { text: '启用', value: 1 },
  { text: '禁用', value: 0 }
]" :filter-method="filterStatus" />
```

### 1.5 多选

```vue
<el-table
  :data="list"
  @selection-change="onSelectionChange"
>
  <el-table-column type="selection" width="55" />
  <el-table-column prop="name" label="姓名" />
</el-table>
```

```ts
const selection = ref<any[]>([])

function onSelectionChange(rows: any[]) {
  selection.value = rows
}

// 批量操作
function batchDelete() {
  const ids = selection.value.map(r => r.id).join(',')
  api.deleteBatch(ids)
}
```

### 1.6 格式化与插槽

```vue
<!-- 方式 1：formatter -->
<el-table-column
  prop="createTime"
  label="创建时间"
  :formatter="(row) => dateFormatter(row.createTime)"
/>

<!-- 方式 2：自定义插槽 -->
<el-table-column label="状态">
  <template #default="scope">
    <el-tag :type="scope.row.status === 1 ? 'success' : 'info'">
      {{ scope.row.status === 1 ? '启用' : '禁用' }}
    </el-tag>
  </template>
</el-table-column>
```

### 1.7 分页 el-pagination

```vue
<Pagination
  :total="total"
  v-model:page="queryParams.pageNo"
  v-model:limit="queryParams.pageSize"
  @pagination="getList"
/>
```

`<Pagination>` 是 ruoyi 封装的分页组件，内部封装了 `el-pagination` + 布局控制。

## 2. 代码示例

### 2.1 完整 CRUD 表格

```vue
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'

interface User { id: number; name: string; status: number; createTime: string }

const list = ref<User[]>([])
const total = ref(0)
const loading = ref(false)
const selection = ref<User[]>([])
const queryParams = reactive({ pageNo: 1, pageSize: 10, name: '' })

async function getList() {
  loading.value = true
  try {
    const res = await api.getUserPage(queryParams)
    list.value = res.list
    total.value = res.total
  } finally {
    loading.value = false
  }
}

onMounted(getList)

function onSelection(rows: User[]) {
  selection.value = rows
}

async function handleDelete(id: number) {
  await ElMessageBox.confirm(`确定删除 ID=${id}？`)
  await api.delete(id)
  ElMessage.success('删除成功')
  await getList()
}

async function batchDelete() {
  if (selection.value.length === 0) return ElMessage.warning('请先选择')
  const ids = selection.value.map(r => r.id).join(',')
  await api.deleteBatch(ids)
  ElMessage.success('删除成功')
  await getList()
}
</script>

<template>
  <el-table :data="list" v-loading="loading" stripe @selection-change="onSelection">
    <el-table-column type="selection" width="55" />
    <el-table-column prop="id" label="ID" width="80" />
    <el-table-column prop="name" label="姓名" />
    <el-table-column label="状态">
      <template #default="scope">
        <el-tag :type="scope.row.status === 1 ? 'success' : 'info'">
          {{ scope.row.status === 1 ? '启用' : '禁用' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="createTime" label="创建时间" width="180" />
    <el-table-column label="操作" width="120" fixed="right">
      <template #default="scope">
        <el-button link type="danger" @click="handleDelete(scope.row.id)">删除</el-button>
      </template>
    </el-table-column>
  </el-table>

  <el-pagination
    :total="total"
    v-model:current-page="queryParams.pageNo"
    v-model:page-size="queryParams.pageSize"
    :page-sizes="[10, 20, 50, 100]"
    layout="total, sizes, prev, pager, next, jumper"
    @current-change="getList"
    @size-change="getList"
  />
</template>
```

### 2.2 服务端排序

```vue
<el-table :data="list" @sort-change="onSortChange">
  <el-table-column prop="createTime" label="创建时间" sortable="custom" />
  <el-table-column prop="price" label="价格" sortable="custom" />
</el-table>
```

```ts
function onSortChange({ prop, order }: { prop: string; order: 'ascending' | 'descending' | null }) {
  queryParams.orderByColumn = prop
  queryParams.isAsc = order === 'ascending' ? 'asc' : order === 'descending' ? 'desc' : undefined
  getList()
}
```

### 2.3 常见错误：本地分页 vs 服务端分页

```vue
<!-- ❌ 错误：所有数据一次返回，前端分页（数据量大时卡） -->
<el-table :data="allData">
  <el-pagination :total="allData.length" />
</el-pagination>

<!-- ✅ 正确：服务端分页，传 pageNo/pageSize 拉数据 -->
<el-table :data="currentPage">
  <el-pagination
    :total="total"
    v-model:current-page="queryParams.pageNo"
    @current-change="getList"
  />
</el-pagination>
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 SN 码列表：完整表格 + 分页

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`
**核心代码**（行 73-108）：

```vue
<!-- 列表 -->
<ContentWrap>
  <el-table v-loading="loading" :data="list" stripe>
    <el-table-column label="SN 码" align="center" prop="snCode" min-width="180" />
    <el-table-column label="物料编码" align="center" prop="itemCode" min-width="120" />
    <el-table-column label="物料名称" align="center" prop="itemName" min-width="150" />
    <el-table-column label="规格型号" align="center" prop="specification" min-width="120" />
    <el-table-column label="批次号" align="center" prop="batchCode" min-width="120" />
    <el-table-column
      label="生成时间"
      align="center"
      prop="createTime"
      :formatter="dateFormatter"
      width="180px"
    />
    <el-table-column label="操作" align="center" width="120" fixed="right">
      <template #default="scope">
        <el-button
          link
          type="danger"
          @click="handleDelete(scope.row.id)"
          v-hasPermi="['mes:wm-sn:delete']"
        >
          删除
        </el-button>
      </template>
    </el-table-column>
  </el-table>
  <!-- 分页 -->
  <Pagination
    :total="total"
    v-model:page="queryParams.pageNo"
    v-model:limit="queryParams.pageSize"
    @pagination="getList"
  />
</ContentWrap>
```

**解读**：
- 第 1 行：`<ContentWrap>` 是 ruoyi 封装的卡片容器
- 第 3 行：`:data="list"` 数据源，`stripe` 斑马纹
- 第 4-10 行：每列用 `prop` 直接取字段，`min-width` 让列宽自适应
- 第 11-16 行：`生成时间` 列用 `:formatter="dateFormatter"` 格式化
- 第 17 行：操作列 `fixed="right"` 固定在最右
- 第 18 行：`<template #default="scope">` 自定义列内容
- 第 19-26 行：行内删除按钮（带 `v-hasPermi` 权限控制）
- 第 28-32 行：`<Pagination>` 是 ruoyi 封装的分页组件

### 3.2 分页封装组件约定

根据 ruoyi 公开约定，`Pagination.vue` 的实现大致是：

```vue
<!-- components/Pagination/index.vue -->
<script setup lang="ts">
interface Props {
  total: number
  page?: number       // 当前页
  limit?: number      // 每页大小
  pageSizes?: number[]
  layout?: string
}
const props = withDefaults(defineProps<Props>(), {
  pageSizes: () => [10, 20, 30, 50, 100],
  layout: 'total, sizes, prev, pager, next, jumper'
})

const emit = defineEmits<{
  pagination: []
  'update:page': [page: number]
  'update:limit': [limit: number]
}>()
</script>

<template>
  <el-pagination
    :total="total"
    :current-page="page"
    :page-size="limit"
    :page-sizes="pageSizes"
    :layout="layout"
    @current-change="(p) => emit('update:page', p)"
    @size-change="(s) => emit('update:limit', s)"
    @current-change="emit('pagination')"
  />
</template>
```

**解读**：
- 封装目的：统一分页布局、减少模板代码
- `v-model:page` 双向绑定当前页（外层改 `queryParams.pageNo`）
- `v-model:limit` 双向绑定每页大小
- `@pagination` 通知外层重新查询
- **三层绑定**：v-model + emit，外部写起来像 `:total + v-model + @pagination` 三件套

## 4. 关键要点总结

- el-table 三件套：`:data`、列定义、`v-loading`
- 列的 `prop` 取字段，复杂内容用 `<template #default="scope">`
- 多选：`type="selection" + @selection-change`
- 服务端排序：列加 `sortable="custom"`，@sort-change 回调带 prop/order
- 分页用 el-pagination（ruoyi 二次封装为 `<Pagination>`）
- **永远用服务端分页**，不要前端分页
- 行内操作按钮用 `fixed="right"` 列 + `link` 按钮样式

## 5. 练习题

### 练习 1：基础（必做）

为 SN 码列表增加"按 SN 码 / 创建时间排序"功能：
- `snCode` 列加 `sortable="custom"`
- `createTime` 列加 `sortable="custom"`
- `@sort-change` 回调中把排序参数合并到 `queryParams`，再调 `getList`

### 练习 2：进阶

实现"批量删除"：
- 表格加 `type="selection"` 列
- 顶部加"批量删除"按钮（`v-hasPermi="['mes:wm-sn:delete']"`）
- 选中行后，调 `deleteSnBatch(ids.join(','))`

### 练习 3：挑战（选做）

实现"表格列设置"功能：用户可选择显示/隐藏某些列，配置存 localStorage。提示：用 ref 存储 `visibleColumns`，表格 v-for 渲染。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`
- Element Plus Table 文档：https://element-plus.org/zh-CN/component/table.html
- Element Plus Pagination 文档：https://element-plus.org/zh-CN/component/pagination.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13