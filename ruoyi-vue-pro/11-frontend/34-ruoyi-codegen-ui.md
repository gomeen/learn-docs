# 11.6.6 代码生成器前端

> 了解 ruoyi 的代码生成器前端：可视化建表 → 一键生成前后端 CRUD 代码。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ruoyi 代码生成器的工作流
- 在代码生成器页面配置表结构
- 生成的前端代码长什么样
- 二次开发代码生成模板

## 📚 前置知识

- Axios（详见 [Axios](./23-axios.md)）
- 项目结构（详见 [Vue3 结构](./28-ruoyi-vue3-structure.md)）
- 代码生成后端（详见 [代码生成总览](../08-code-generation/01-overview.md)）

## 1. 核心概念

### 1.1 什么是代码生成器？

代码生成器 = 把"数据库表"自动变成"前后端 CRUD 代码"的工具。

**传统开发**：
```
设计表 → 写后端 Entity → 写 Mapper → 写 Service → 写 Controller →
写前端 API → 写前端 List 页 → 写前端 Form 页 → 测试
（重复 2-3 天）
```

**用代码生成器**：
```
设计表 → 在生成器页面配置字段 → 点"生成" → 下载 zip 包
（5 分钟搞定）
```

### 1.2 ruoyi 代码生成器的位置

```
yudao-ui-admin-vue3/src/views/infra/codegen/
├── index.vue                       # 表列表
├── preview.vue                     # 预览生成的代码
└── import.vue                      # 导入已有表
```

后端模块：`yudao-module-infra`（基础设施）+ `yudao-spring-boot-starter-codegen`

### 1.3 生成器工作流

```
1. 数据源管理
   ↓ 配置数据库连接（host/port/db/账号密码）
2. 导入表
   ↓ 选数据库 → 选表 → 导入到 yudao 数据库的 infra_codegen_table
3. 编辑表信息
   ↓ 表名/注释/作者/模板
4. 编辑字段信息
   ↓ 字段名/类型/注释/表单类型/查询条件/字典/必填
5. 生成代码
   ↓ 点"生成"按钮
6. 下载 zip
   ↓ infra_codegen_table 关联生成记录
7. 解压
   ↓ 把 controller/service/dao/vue 文件复制到项目
```

### 1.4 生成的内容

代码生成器会生成两套代码：

**后端（Java）**：
```
xxxController.java          # 控制器
xxxService.java             # 服务接口
xxxServiceImpl.java         # 服务实现
xxxDAO.java                 # MyBatis-Plus DAO
xxxDO.java                  # 数据库对象
xxxVO.java                  # 视图对象
xxxMapper.xml               # MyBatis XML
```

**前端（Vue3）**：
```
index.vue                   # 列表页
Form.vue                    # 表单弹窗
api.ts                      # 接口定义
types.ts                    # TypeScript 类型
```

## 2. 代码示例

### 2.1 生成的 API 文件示例

```ts
// 文件：src/api/mes/wm/productrecpt/index.ts
import request from '@/config/axios'

export interface ProductRecptVO {
  id: number
  code: string
  name: string
  // ...
}

export const ProductRecptApi = {
  getProductRecptPage: async (params: any) => {
    return await request.get({ url: '/mes/wm/product-recpt/page', params })
  },
  getProductRecpt: async (id: number) => {
    return await request.get({ url: '/mes/wm/product-recpt/get?id=' + id })
  },
  createProductRecpt: async (data: ProductRecptVO) => {
    return await request.post({ url: '/mes/wm/product-recpt/create', data })
  },
  updateProductRecpt: async (data: ProductRecptVO) => {
    return await request.put({ url: '/mes/wm/product-recpt/update', data })
  },
  deleteProductRecpt: async (id: number) => {
    return await request.delete({ url: '/mes/wm/product-recpt/delete?id=' + id })
  }
}
```

### 2.2 生成的列表页示例

```vue
<!-- 文件：src/views/mes/wm/productrecpt/index.vue -->
<script setup lang="ts">
import { dateFormatter } from '@/utils/formatTime'
import { ProductRecptApi } from '@/api/mes/wm/productrecpt'
import Form from './Form.vue'

defineOptions({ name: 'MesWmProductRecpt' })

const message = useMessage()
const { t } = useI18n()

const loading = ref(true)
const list = ref([])
const total = ref(0)
const queryParams = reactive({
  pageNo: 1,
  pageSize: 10,
  code: undefined,
  name: undefined
})
const queryFormRef = ref()
const exportLoading = ref(false)
const dialogVisible = ref(false)

const getList = async () => {
  loading.value = true
  try {
    const data = await ProductRecptApi.getProductRecptPage(queryParams)
    list.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

const handleQuery = () => {
  queryParams.pageNo = 1
  getList()
}

const resetQuery = () => {
  queryFormRef.value.resetFields()
  handleQuery()
}

const openForm = () => {
  dialogVisible.value = true
}

onMounted(() => { getList() })
</script>

<template>
  <ContentWrap>
    <el-form :model="queryParams" ref="queryFormRef" :inline="true">
      <el-form-item label="单据编号" prop="code">
        <el-input v-model="queryParams.code" placeholder="请输入单据编号" clearable class="!w-240px" />
      </el-form-item>
      <el-form-item label="单据名称" prop="name">
        <el-input v-model="queryParams.name" placeholder="请输入单据名称" clearable class="!w-240px" />
      </el-form-item>
      <el-form-item>
        <el-button @click="handleQuery"><Icon icon="ep:search" />搜索</el-button>
        <el-button @click="resetQuery"><Icon icon="ep:refresh" />重置</el-button>
        <el-button type="primary" @click="openForm" v-hasPermi="['mes:wm-product-recpt:create']">
          <Icon icon="ep:plus" />新增
        </el-button>
        <el-button type="success" @click="handleExport" v-hasPermi="['mes:wm-product-recpt:export']">
          <Icon icon="ep:download" />导出
        </el-button>
      </el-form-item>
    </el-form>
  </ContentWrap>

  <ContentWrap>
    <el-table v-loading="loading" :data="list" stripe>
      <el-table-column label="单据编号" prop="code" />
      <el-table-column label="单据名称" prop="name" />
      <!-- ... -->
      <el-table-column label="操作" fixed="right">
        <template #default="scope">
          <el-button link type="primary" @click="openForm(scope.row.id)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <Pagination :total="total" v-model:page="queryParams.pageNo" v-model:limit="queryParams.pageSize" @pagination="getList" />
  </ContentWrap>

  <Form ref="formRef" @success="getList" />
</template>
```

### 2.3 生成的表单页示例

```vue
<!-- 文件：src/views/mes/wm/productrecpt/Form.vue -->
<script setup lang="ts">
import { ProductRecptApi } from '@/api/mes/wm/productrecpt'

const dialogVisible = ref(false)
const dialogTitle = ref('')
const formLoading = ref(false)
const formData = ref({})
const formRules = reactive({})
const formRef = ref()

const emit = defineEmits(['success'])

const open = async (id?: number) => {
  dialogVisible.value = true
  if (id) {
    dialogTitle.value = '编辑'
    const data = await ProductRecptApi.getProductRecpt(id)
    formData.value = data
  } else {
    dialogTitle.value = '新增'
    formData.value = {}
  }
}

defineExpose({ open })

const submit = async () => {
  await formRef.value.validate()
  formLoading.value = true
  try {
    if (formData.value.id) {
      await ProductRecptApi.updateProductRecpt(formData.value)
    } else {
      await ProductRecptApi.createProductRecpt(formData.value)
    }
    message.success('保存成功')
    dialogVisible.value = false
    emit('success')
  } finally {
    formLoading.value = false
  }
}
</script>

<template>
  <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
    <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px">
      <el-form-item label="单据编号" prop="code">
        <el-input v-model="formData.code" />
      </el-form-item>
      <el-form-item label="单据名称" prop="name">
        <el-input v-model="formData.name" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="submit" :loading="formLoading">确定</el-button>
    </template>
  </el-dialog>
</template>
```

### 2.4 常见错误：生成的代码不修改就用

```ts
// ❌ 错误：生成代码直接用，但缺少业务校验
const submit = async () => {
  await ProductRecptApi.updateProductRecpt(formData.value)
}

// ✅ 正确：在生成的代码基础上加业务逻辑
const submit = async () => {
  if (!formData.value.warehouseId) {
    ElMessage.error('请选择仓库')
    return
  }
  await ProductRecptApi.updateProductRecpt(formData.value)
}
```

## 3. 关键要点总结

- 代码生成器 = 数据库表 → 前后端 CRUD 代码（5 分钟生成完整模块）
- ruoyi 位置：`views/infra/codegen/` + 后端 `yudao-module-infra` 模块
- 工作流：配置数据源 → 导入表 → 编辑字段 → 生成代码 → 下载 zip
- 生成的内容：Java 后端（Controller/Service/DAO）+ Vue3 前端（List/Form/API）
- **生成代码作为起点**，业务逻辑仍需手动补充
- 可以改写 `.vm` 模板定制生成风格

---

**文档版本**：v1.0
**最后更新**：2026-07-13
