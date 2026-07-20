# 11.1.4 组件通信：props / emits / provide/inject

> 掌握 Vue3 组件间数据传递的 4 种方式，能在 ruoyi 业务组件中合理拆分组件并传递数据。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 props（父→子）、emits（子→父）、v-model、provide/inject
- 掌握 TypeScript 下的 props 类型定义（接口、`withDefaults`）
- 能在 ruoyi 中拆分大型列表页（搜索栏 + 表格 + 分页）

## 📚 前置知识

- Vue3 基础（详见 [Vue3 基础](./01-vue3-basics.md)）
- TypeScript 接口（详见 [TS 接口](./09-ts-interface.md)）

## 1. 核心概念

### 1.1 4 种通信方式概览

```
父组件  ──props──▶  子组件     （数据下行）
父组件  ◀──emits──  子组件     （事件上行）
祖组件  ──provide──▶ 后代组件  （跨级注入）
任意组件 ◀──pinia──▶ 任意组件   （全局共享，下一节讲）
```

### 1.2 props：父传子

**TypeScript 推荐写法**：用 `interface` 定义 props 类型。

```vue
<!-- 子组件 UserCard.vue -->
<script setup lang="ts">
interface Props {
  name: string
  age?: number          // 可选
  tags?: string[]       // 可选数组
}

const props = withDefaults(defineProps<Props>(), {
  age: 18,
  tags: () => ['vip']
})

console.log(props.name) // 直接访问
</script>

<template>
  <div>{{ name }} - {{ age }} 岁 - {{ tags }}</div>
</template>
```

**关键点**：
- `defineProps<Props>()` 是**编译时宏**，不需要 import
- `withDefaults` 提供默认值；**对象/数组默认值必须用工厂函数**（`() => []`）
- 模板中无需 `props.xxx`，直接 `{{ name }}`

### 1.3 emits：子传父

```vue
<!-- 子组件 -->
<script setup lang="ts">
const emit = defineEmits<{
  (e: 'change', value: string): void
  (e: 'delete', id: number): void
}>()

function handleClick() {
  emit('change', 'hello')
}
</script>
```

```vue
<!-- 父组件使用 -->
<UserCard @change="onChange" @delete="onDelete" />
```

### 1.4 v-model：双向绑定的语法糖

`v-model` 本质是 `:modelValue` + `@update:modelValue`。

```vue
<!-- 子组件 -->
<script setup lang="ts">
const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()
</script>

<template>
  <input
    :value="modelValue"
    @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
  />
</template>
```

```vue
<!-- 父组件 -->
<MyInput v-model="username" />
```

### 1.5 provide / inject：跨级通信

适合**祖→孙**的全局数据（如主题、用户信息）。

```ts
// 祖组件
import { provide, ref } from 'vue'
const theme = ref('dark')
provide('theme', theme)
```

```ts
// 孙组件
import { inject, Ref } from 'vue'
const theme = inject<Ref<string>>('theme', ref('light'))
```

**注意**：inject 的值**默认不是响应式的**！需要传 `ref` 进去才能保持响应。

### 1.6 插槽 slot：内容分发

```vue
<!-- 子组件 Card.vue -->
<template>
  <div class="card">
    <header><slot name="header" /></header>
    <main><slot /></main>
  </div>
</template>
```

```vue
<!-- 父组件 -->
<Card>
  <template #header>标题</template>
  <p>这是默认插槽内容</p>
</Card>
```

## 2. 代码示例

### 2.1 父传子：用户卡片

```vue
<!-- UserCard.vue -->
<script setup lang="ts">
interface Props {
  user: { id: number; name: string; email: string }
  showEmail?: boolean
}

withDefaults(defineProps<Props>(), { showEmail: true })
</script>

<template>
  <div class="user-card">
    <h3>{{ user.name }}</h3>
    <p v-if="showEmail">{{ user.email }}</p>
  </div>
</template>
```

```vue
<!-- Parent.vue -->
<UserCard :user="currentUser" :show-email="false" />
```

### 2.2 子传父：计数器

```vue
<!-- Counter.vue -->
<script setup lang="ts">
const count = ref(0)
const emit = defineEmits<{
  (e: 'reachTen', value: number): void
}>()

watch(count, (n) => {
  if (n >= 10) emit('reachTen', n)
})
</script>

<template>
  <button @click="count++">{{ count }}</button>
</template>
```

### 2.3 v-model：自定义输入框

```vue
<!-- TrimInput.vue -->
<script setup lang="ts">
const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

function onInput(e: Event) {
  const v = (e.target as HTMLInputElement).value.trim()
  emit('update:modelValue', v)
}
</script>

<template>
  <input :value="modelValue" @input="onInput" />
</template>
```

### 2.4 常见错误：解构 props 丢失响应式

```ts
// ❌ 错误：解构后 props 不再响应
const props = defineProps<{ count: number }>()
const { count } = props  // count 是普通变量

// ✅ 正确 1：不解构
console.log(props.count)

// ✅ 正确 2：用 toRef / toRefs 保持响应
import { toRef } from 'vue'
const count = toRef(props, 'count')
```

## 3. 关键要点总结

- `defineProps<T>()` 和 `defineEmits<T>()` 是编译时宏
- 默认值用 `withDefaults`，对象/数组用工厂函数
- 解构 props 丢失响应式，用 `toRef` / `toRefs`
- `v-model` = `:modelValue` + `@update:modelValue`
- `provide/inject` 适合跨级共享，但默认不是响应式
- ruoyi 的"大组件"模式：搜索栏/表格/分页写在同一文件，靠模板 ref + v-model 通信

---

**文档版本**：v1.0
**最后更新**：2026-07-13
