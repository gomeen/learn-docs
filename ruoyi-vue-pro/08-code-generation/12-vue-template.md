# 3.3 ruoyi 的 Vue 模板

> 解读 ruoyi 各种前端技术栈的 Vue 模板差异和核心占位符。

## 🎯 学习目标

完成本文档后，你将能够：
- 列出 ruoyi 支持的 9 种前端技术栈
- 解释 Vue 模板（`index.vue.vm` / `form.vue.vm`）的核心结构
- 理解不同前端框架的模板组织方式
- 理解 Vue2 vs Vue3 模板的关键差异

## 📚 前置知识

- Velocity / Java 模板（详见 [Velocity](./10-velocity.md)、[Java 模板](./11-java-template.md)）
- Vue 3 基础（详见 [Vue3 基础](../11-frontend/01-vue3-basics.md)）
- Element Plus / Vben（详见 [Element Plus](../11-frontend/10-element-plus.md)、[Vben](../11-frontend/13-vben.md)）

## 1. 核心概念

### 1.1 9 种前端技术栈

| `CodegenFrontTypeEnum` 值 | 模板目录 | 框架 |
|--------------------------|---------|------|
| `VUE2_ELEMENT_UI(10)` | `codegen/vue/` | Vue2 + Element UI |
| `VUE3_ELEMENT_PLUS(20)` | `codegen/vue3/` | Vue3 + Element Plus |
| `VUE3_VBEN2_ANTD_SCHEMA(30)` | `codegen/vue3_vben/` | Vue3 + Vben2 + Antd + Schema |
| `VUE3_VBEN5_ANTD_SCHEMA(40)` | `codegen/vue3_vben5_antd/schema/` | Vben5 + Antd + Schema |
| `VUE3_VBEN5_ANTD_GENERAL(41)` | `codegen/vue3_vben5_antd/general/` | Vben5 + Antd + 常规 |
| `VUE3_VBEN5_ANTDV_NEXT_SCHEMA(42)` | `codegen/vue3_vben5_antdv_next/schema/` | Vben5 + Antdv Next + Schema |
| `VUE3_VBEN5_ANTDV_NEXT_GENERAL(43)` | `codegen/vue3_vben5_antdv_next/general/` | Vben5 + Antdv Next + 常规 |
| `VUE3_VBEN5_EP_SCHEMA(50)` | `codegen/vue3_vben5_ele/schema/` | Vben5 + Element Plus + Schema |
| `VUE3_VBEN5_EP_GENERAL(51)` | `codegen/vue3_vben5_ele/general/` | Vben5 + Element Plus + 常规 |
| `VUE3_ADMIN_UNIAPP_WOT(60)` | `codegen/vue3_admin_uniapp/` | Vue3 + Uniapp（移动端） |

### 1.2 模板组织差异

- **标准 vue2 / vue3**：API + views/index + views/form (+ vue3 多一个 import)
- **Schema 模式**（vben）：API + views/{data.ts, index, form, import} + modules
- **General 模式**（vben）：API + views/{index, form, import} + modules
- **Uniapp**：API + components + views/index + views/form/index + views/detail/index

### 1.3 主子表子组件命名

- 标准 vue2/vue3：放在 `views/${businessName}/components/`
- Vben 5：放在 `views/${businessName}/modules/`
- 命名规范：`${subSimpleClassName}Form.vue` / `${subSimpleClassName}List.vue`

## 2. 代码示例

### 2.1 Vue3 + Element Plus 列表页生成效果（简化）

```vue
<template>
  <ContentWrap>
    <!-- 搜索栏 -->
    <el-form :model="queryParams" ref="queryFormRef" :inline="true">
      <el-form-item label="字典名称" prop="name">
        <el-input v-model="queryParams.name" placeholder="请输入字典名称" clearable />
      </el-form-item>
      <el-form-item>
        <el-button @click="handleQuery"><Icon icon="ep:search" />搜索</el-button>
        <el-button @click="resetQuery"><Icon icon="ep:refresh" />重置</el-button>
      </el-form-item>
    </el-form>

    <!-- 列表 -->
    <el-table v-loading="loading" :data="list">
      <el-table-column label="字典编号" prop="id" />
      <el-table-column label="字典名称" prop="name" />
      <el-table-column label="字典类型" prop="type" />
      <el-table-column label="操作" align="center">
        <template #default="{ row }">
          <el-button link type="primary" @click="openForm('update', row.id)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </ContentWrap>
</template>
```

## 3. ruoyi 仓库源码解读

### 3.1 Vue3 index.vue.vm 核心片段

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/vue3/views/index.vue.vm`

```vue
<script setup lang="ts">
import { ref, reactive } from 'vue'
import * as ${classNameVar}Api from '@/api/${table.moduleName}/${table.businessName}/index'
import { DICT_TYPE, getIntDictOptions } from '@/utils/dict'

const loading = ref(true)
const list = ref<${classNameVar}Api.${simpleClassName}VO[]>([])
const queryParams = reactive({
  pageNo: 1,
  pageSize: 10,
  ... // 遍历 columns 中 listOperation=true 的字段
})

const getList = async () => {
  loading.value = true
  try {
    const data = await ${classNameVar}Api.get${simpleClassName}Page(queryParams)
    list.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}
</script>
```

**关键占位符**：
- `${classNameVar}` → `dictType`（变量名）
- `${simpleClassName}` → `DictType`
- `${table.moduleName}` → `system`
- `${table.businessName}` → `dict`

### 3.2 Vue3 form.vue.vm 关键片段

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/vue3/views/form.vue.vm`

```vue
<script setup lang="ts">
import * as ${classNameVar}Api from '@/api/${table.moduleName}/${table.businessName}/index'

const dialogVisible = ref(false)
const dialogTitle = ref('')
const formLoading = ref(false)
const formData = ref<${classNameVar}Api.${simpleClassName}VO>({} as any)
const formRules = reactive({
  // 遍历 columns 中 createOperation=true 的字段
  name: [{ required: true, message: '字典名称不能为空', trigger: 'blur' }],
  type: [{ required: true, message: '字典类型不能为空', trigger: 'blur' }],
  status: [{ required: true, message: '状态不能为空', trigger: 'change' }],
})
</script>

<template>
  <Dialog v-model="dialogVisible" :title="dialogTitle">
    <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px">
      <el-form-item label="字典名称" prop="name">
        <el-input v-model="formData.name" placeholder="请输入字典名称" />
      </el-form-item>
      <el-form-item label="状态" prop="status">
        <el-radio-group v-model="formData.status">
          <el-radio v-for="dict in getIntDictOptions(DICT_TYPE.COMMON_STATUS)"
                    :key="dict.value" :value="dict.value">{{ dict.label }}</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
  </Dialog>
</template>
```

### 3.3 Vue3 api.ts.vm 关键片段

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/vue3/api/api.ts.vm`

```typescript
import request from '@/config/axios'

export interface ${simpleClassName}VO {
  id: number
  // 遍历 columns 中 listOperationResult=true 的字段
  name: string
  type: string
  status: number
  createTime: string
}

// 查询字典类型分页
export const get${simpleClassName}Page = (params: PageParam) => {
  return request.get({ url: '/${table.moduleName}/${simpleClassName_strikeCase}/page', params })
}

// 查询字典类型详情
export const get${simpleClassName} = (id: number) => {
  return request.get({ url: '/${table.moduleName}/${simpleClassName_strikeCase}/get', params: { id } })
}

// 新增字典类型
export const create${simpleClassName} = (data: ${simpleClassName}VO) => {
  return request.post({ url: '/${table.moduleName}/${simpleClassName_strikeCase}/create', data })
}
```

**解读**：
- API 路径与后端 Controller 的 `@RequestMapping` 一一对应
- 路径用短横线分隔（`simpleClassName_strikeCase`）
- TS 接口 `${simpleClassName}VO` 与后端 RespVO 字段对应

### 3.4 Vben 5 Schema 模式的特殊之处

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/vue3_vben5_antd/schema/views/data.ts.vm`

```typescript
import { BasicColumn, FormSchema } from '@/components/Table'

// 列表字段定义
export const columns: BasicColumn[] = [
  { title: '字典编号', dataIndex: 'id', width: 100 },
  { title: '字典名称', dataIndex: 'name' },
  { title: '状态', dataIndex: 'status', dictClass: 'number', dictType: DICT_TYPE.COMMON_STATUS },
]

// 表单字段定义
export const formSchema: FormSchema[] = [
  { field: 'name', label: '字典名称', component: 'Input', required: true },
  { field: 'status', label: '状态', component: 'RadioGroup', componentProps: {
      options: getDictOptions(DICT_TYPE.COMMON_STATUS, 'number')
  }},
]
```

**解读**：
- **Schema 模式**用"配置对象"声明字段（不是手写模板）
- 一个 `BasicColumn[]` + 一个 `FormSchema[]` 就能生成完整页面
- 适合复杂业务页，开发效率高

## 4. 关键要点总结

- 9 种前端框架分 7 个模板目录（部分共用）
- **标准 vue3** 模板：`index.vue` + `form.vue` + `import.vue`（导入）
- **Vben 5** 模板分 `schema`（配置式）和 `general`（模板式）
- **Uniapp** 模板独立组织（`views/form/index.vue` 等）
- API 模板输出 **TypeScript 接口**和 **axios 请求函数**
- 字典字段在 Vue 端用 `DICT_TYPE.xxx` + `getIntDictOptions` / `getDictLabel`

## 5. 练习题

### 练习 1：基础（必做）

打开 `vue3/views/index.vue.vm`，列出所有 `${...}` 占位符（至少 5 个）。

### 练习 2：进阶

阅读 `vue3/api/api.ts.vm`，画出"创建"、"更新"、"删除" 三个 API 函数的**完整签名**（参数类型 + 返回类型）。

### 练习 3：挑战（选做）

新增一个前端框架 `VUE3_NUXT_SSR(70)`，需要在 `CodegenFrontTypeEnum` 加值、在 `CodegenEngine.FRONT_TEMPLATES` 注册 4 个模板（`api/api.ts` + `views/{index,form,import}.vue`）。列出需要修改的所有文件。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/vue3/views/index.vue.vm`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/vue3/views/form.vue.vm`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/vue3/api/api.ts.vm`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/vue3_vben5_antd/schema/views/data.ts.vm`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/enums/codegen/CodegenFrontTypeEnum.java`
- 官方文档：https://doc.iocoder.cn/codegen/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
