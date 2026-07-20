# 11.2.3 组合式 API 与 TypeScript

> 掌握 Vue3 组合式 API + TypeScript 的结合用法：泛型 ref、defineProps 类型、模板 ref 类型。

## 🎯 学习目标

完成本文档后，你将能够：
- 给 `ref` / `reactive` 提供正确的类型（泛型 + 推断）
- 定义组件 props 类型（`defineProps<T>()`）和 emit 类型
- 给模板 ref 标注类型（`ref<HTMLInputElement>()`）
- 在 ruoyi 中编写类型安全的业务组件

## 📚 前置知识

- TypeScript 基础 / 接口（详见 [TS 基础](./08-ts-basics.md)、[TS 接口](./09-ts-interface.md)）
- Vue3 基础（详见 [Vue3 基础](./01-vue3-basics.md)）

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

## 3. 关键要点总结

- `ref<T>(value)` 显式泛型；`ref(value)` 自动推断（数组、对象推荐显式）
- 模板 ref 必须显式：`ref<HTMLInputElement | null>(null)`
- el-form ref 用 `ref<FormInstance>()` 或 `ref<InstanceType<typeof ElForm>>()`
- `defineProps<T>()` 和 `defineEmits<T>()` 都是编译时宏，类型完全擦除（不影响运行时）
- ruoyi 约定：VO 接口和 API 方法同文件，类型放在文件顶部
- `defineOptions({ name: 'Xxx' })` 给组件起名

---

**文档版本**：v1.0
**最后更新**：2026-07-13
