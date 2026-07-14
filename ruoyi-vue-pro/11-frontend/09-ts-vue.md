# 11.2.3 组合式 API 与 TypeScript

> 掌握 Vue3 组合式 API + TypeScript 的结合用法：泛型 ref、defineProps 类型、模板 ref 类型。

## 🎯 学习目标

完成本文档后，你将能够：
- 给 `ref` / `reactive` 提供正确的类型（泛型 + 推断）
- 定义组件 props 类型（`defineProps<T>()`）和 emit 类型
- 给模板 ref 标注类型（`ref<HTMLInputElement>()`）
- 在 ruoyi 中编写类型安全的业务组件

## 📚 前置知识

- 11-frontend/01-vue3-basics.md
- 11-frontend/07-ts-basics.md
- 11-frontend/08-ts-interface.md

## 1. 核心概念

### 1.1 ref 的类型

```ts
import { ref } from 'vue'

// 方式 1：泛型指定（显式）
const count = ref<number>(0)
const list = ref<UserVO[]>([])
const user = ref<UserVO | null>(null)

// 方式 2：初始值推断（推荐）
const count = ref(0)          // 推断为 Ref<number>
const list = ref<UserVO[]>([]) // 必须显式，因为 [] 推断为 never[]

// 方式 3：Ref 类型显式声明
import type { Ref } from 'vue'
const count: Ref<number> = ref(0)
```

### 1.2 reactive 的类型

```ts
import { reactive } from 'vue'

// 推荐：定义接口，强类型
interface FormState {
  username: string
  password: string
  remember: boolean
}

const form = reactive<FormState>({
  username: '',
  password: '',
  remember: false
})

// 推断方式（少用，丢失类型保护）
const form = reactive({ username: '', password: '', remember: false })
```

### 1.3 模板 ref 的类型

模板 ref 默认是 `Ref<undefined>`，必须显式标注才能调用元素方法：

```vue
<script setup lang="ts">
import { ref } from 'vue'

// DOM 元素
const inputRef = ref<HTMLInputElement | null>(null)
inputRef.value?.focus()  // 可选链保护

// 组件实例
import { ElForm } from 'element-plus'
const formRef = ref<InstanceType<typeof ElForm>>()
formRef.value?.validate()
</script>

<template>
  <input ref="inputRef" />
  <el-form ref="formRef">...</el-form>
</template>
```

### 1.4 defineProps 类型化

```ts
// 方式 1：纯类型（运行时无校验）
const props = defineProps<{
  name: string
  age?: number
}>()

// 方式 2：接口（推荐，可复用）
interface Props {
  name: string
  age?: number
}
const props = defineProps<Props>()

// 方式 3：withDefaults 提供默认值
interface Props {
  name: string
  age?: number
  tags?: string[]
}
const props = withDefaults(defineProps<Props>(), {
  age: 18,
  tags: () => ['vip']  // 对象/数组用工厂函数
})
```

### 1.5 defineEmits 类型化

```ts
// 方式 1：对象形式
const emit = defineEmits<{
  (e: 'change', value: string): void
  (e: 'update:modelValue', value: string): void
}>()

// 方式 2：元组形式（Vue3.3+，更简洁）
const emit = defineEmits<{
  change: [value: string]
  'update:modelValue': [value: string]
}>()
```

### 1.6 组件类型导出

子组件导出 props 类型，父组件可以引用：

```ts
// Child.vue
export interface ChildProps {
  name: string
}
const props = defineProps<ChildProps>()
```

```ts
// Parent.vue
import Child, { type ChildProps } from './Child.vue'

// 用 ChildProps 约束其他 props
const props = defineProps<{
  title: string
  childProps: ChildProps
}>()
```

### 1.7 泛型组件

`<script setup generic="T">` 可以定义泛型组件：

```vue
<script setup lang="ts" generic="T extends { id: number }">
interface Props {
  list: T[]
  rowKey?: keyof T
}
const props = withDefaults(defineProps<Props>(), { rowKey: 'id' })
</script>

<template>
  <div v-for="item in list" :key="item[rowKey]">{{ item.id }}</div>
</template>
```

## 2. 代码示例

### 2.1 表单组件的类型化

```vue
<!-- Form.vue -->
<script setup lang="ts">
import { reactive } from 'vue'

interface FormState {
  username: string
  password: string
}

const form = reactive<FormState>({ username: '', password: '' })

const emit = defineEmits<{
  submit: [form: FormState]
}>()

function onSubmit() {
  emit('submit', form)
}
</script>

<template>
  <form @submit.prevent="onSubmit">
    <input v-model="form.username" />
    <input v-model="form.password" type="password" />
    <button type="submit">提交</button>
  </form>
</template>
```

### 2.2 模板 ref 类型

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'

const inputRef = ref<HTMLInputElement | null>(null)
const divRef = ref<HTMLDivElement | null>(null)

onMounted(() => {
  inputRef.value?.focus()
  console.log('div width:', divRef.value?.offsetWidth)
})
</script>

<template>
  <input ref="inputRef" />
  <div ref="divRef">Hello</div>
</template>
```

### 2.3 包装 el-form 的 ref

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { ElForm } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

const formRef = ref<FormInstance>()
const form = reactive({ name: '', email: '' })
const rules: FormRules = {
  name: [{ required: true, message: '不能为空', trigger: 'blur' }]
}

async function submit() {
  await formRef.value?.validate()  // 类型安全
}
</script>

<template>
  <el-form ref="formRef" :model="form" :rules="rules">
    <el-form-item label="姓名" prop="name">
      <el-input v-model="form.name" />
    </el-form-item>
  </el-form>
</template>
```

### 2.4 常见错误：模板 ref 未指定类型

```ts
// ❌ 错误：ref 未指定类型，类型是 Ref<undefined>
const inputRef = ref()
inputRef.value.focus()  // ❌ value 是 undefined，无 focus 方法

// ✅ 正确：ref<HTMLInputElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)
inputRef.value?.focus()  // 可选链保护
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 SN 码页：组合式 API + TS 实战

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`
**核心代码**（行 130-191）：

```ts
<script setup lang="ts">
import { dateFormatter } from '@/utils/formatTime'
import { WmSnApi, WmSnVO, WmSnGenerateVO } from '@/api/mes/wm/sn'

defineOptions({ name: 'MesWmSn' })

const message = useMessage()
const { t } = useI18n()

const loading = ref(true)
const list = ref<WmSnVO[]>([])
const total = ref(0)
const queryParams = reactive({
  pageNo: 1,
  pageSize: 10,
  snCode: undefined,
  itemId: undefined,
  batchCode: undefined,
  createTime: []
})
const queryFormRef = ref()
const exportLoading = ref(false)

// ... 省略方法 ...

const dialogVisible = ref(false)
const formLoading = ref(false)
const formData = ref<WmSnGenerateVO>({
  itemId: undefined,
  batchCode: undefined,
  workOrderId: undefined,
  snNum: 100
})
const formRules = reactive({
  itemId: [{ required: true, message: '物料不能为空', trigger: 'change' }],
  snNum: [{ required: true, message: '生成数量不能为空', trigger: 'blur' }]
})
const formRef = ref()
```

**解读**：
- 第 3 行：`import` 类型 + 值 —— TypeScript 中类型可以与值混合导入
- 第 6 行：`defineOptions({ name: 'MesWmSn' })` 给组件命名（keep-alive 用）
- 第 8-9 行：`useMessage` / `useI18n` 是 ruoyi 注入的 composables（返回 `ElMessage` 和 `t()` 函数）
- 第 11 行：`ref(true)` 自动推断为 `Ref<boolean>`
- 第 12 行：`ref<WmSnVO[]>([])` 显式泛型（因为 `[]` 默认是 `never[]`）
- 第 22 行：`queryFormRef = ref()` **未指定类型**，后续调用 `.resetFields()` 类型不安全
- 第 33-37 行：`formData` 用 `ref<WmSnGenerateVO>` 包装整个表单对象
- 第 38-41 行：`formRules` 用 `reactive`（因为 rules 是 Element Plus 校验规则对象）

### 3.2 API 定义：类型与代码同文件

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/api/mes/wm/sn/index.ts`
**核心代码**（行 1-29）：

```ts
import request from '@/config/axios'

// MES SN 码 VO
export interface WmSnVO {
  id: number
  snCode: string
  // ...
}

// MES SN 码生成 VO
export interface WmSnGenerateVO {
  itemId: number
  batchCode?: string
  workOrderId?: number
  snNum: number
}

// MES SN 码 API
export const WmSnApi = {
  // 生成 SN 码
  generateSnCodes: async (data: WmSnGenerateVO) => {
    return await request.post({ url: '/mes/wm/sn/generate', data })
  },

  // 查询 SN 码分页
  getSnPage: async (params: any) => {
    return await request.get({ url: '/mes/wm/sn/page', params })
  }
}
```

**解读**：
- 第 2 行：导入 Element Plus 风格的 axios 实例（已经封装好拦截器）
- 第 4-13 行：VO 接口与 API 方法**同文件定义**，方便维护
- 第 27 行：`async (data: WmSnGenerateVO)` —— 入参类型化，调用方写错字段名立刻报错
- 第 31 行：`params: any` —— 这里用了 any，**应该定义 `WmSnPageQuery` 接口** 替换

## 4. 关键要点总结

- `ref<T>(value)` 显式泛型；`ref(value)` 自动推断（数组、对象推荐显式）
- 模板 ref 必须显式：`ref<HTMLInputElement | null>(null)`
- el-form ref 用 `ref<FormInstance>()` 或 `ref<InstanceType<typeof ElForm>>()`
- `defineProps<T>()` 和 `defineEmits<T>()` 都是编译时宏，类型完全擦除（不影响运行时）
- ruoyi 约定：VO 接口和 API 方法同文件，类型放在文件顶部
- `defineOptions({ name: 'Xxx' })` 给组件起名

## 5. 练习题

### 练习 1：基础（必做）

为 `views/mes/wm/sn/index.vue` 的所有 `ref()` 加上正确的类型：
- `queryFormRef` 改为 `ref<FormInstance>()`
- `formRef` 改为 `ref<FormInstance>()`
- `list` 已经是 `ref<WmSnVO[]>`，补充 `Ref` 还是 `ref` 形式更好？

### 练习 2：进阶

实现一个泛型组件 `MyTable<T>`：

```vue
<script setup lang="ts" generic="T extends Record<string, any>">
interface Column { key: keyof T; label: string }
defineProps<{ data: T[]; columns: Column[] }>()
</script>
```

并用 `MyTable<UserVO>` 渲染用户列表。

### 练习 3：挑战（选做）

把 `WmSnApi` 重构为"接口定义 + 实现分离"：

```ts
// api/mes/wm/sn/types.ts
export interface WmSnApiType {
  create(data: WmSnVO): Promise<void>
  // ...
}

// api/mes/wm/sn/index.ts
export const WmSnApi: WmSnApiType = { ... }
```

好处：types 可以单独被后端 swagger 自动生成，前端只写实现。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/api/mes/wm/sn/index.ts`
- Vue3 官方：`defineProps` 类型 https://cn.vuejs.org/api/sfc-script-setup.html#defineprops
- Element Plus 类型定义：https://element-plus.org/zh-CN/guide/typescript.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13