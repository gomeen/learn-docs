# 11.1.2 计算属性与侦听器：computed / watch

> 掌握 Vue3 的派生值（computed）和副作用侦听（watch），能在 ruoyi 业务中正确处理"表格勾选数"、"搜索参数变化"等场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `computed` 的缓存机制与适用场景
- 区分 `watch` 的 4 种触发方式（immediate、deep、once、flush）
- 区分 `watch` 与 `watchEffect` 的取舍
- 能看懂 ruoyi 中表格多选、字典加载、表单联动等逻辑

## 📚 前置知识

- Vue3 基础（详见 [Vue3 基础](./01-vue3-basics.md)）
- ES6 解构、箭头函数

## 1. 核心概念

### 1.1 `computed`：基于响应式数据的派生值

`computed` 返回一个**只读的响应式 ref**，值由计算函数得出，并自动缓存。

```ts
import { ref, computed } from 'vue'

const count = ref(1)
const double = computed(() => count.value * 2)

console.log(double.value) // 2
count.value = 5
console.log(double.value) // 10
```

**核心特性**：
- **缓存**：依赖不变时，多次访问返回同一结果（不重新计算）
- **懒求值**：只有被访问时才计算
- **只读**：要改用 `get/set` 形式或 `ref`

### 1.2 `computed` vs 方法

```ts
// ❌ 方法：每次访问都重新计算
function getDouble() { return count.value * 2 }

// ✅ computed：有缓存，count 不变则直接返回上次的值
const double = computed(() => count.value * 2)
```

### 1.3 `watch`：侦听响应式数据的变化

`watch(source, callback, options)` 在响应式数据变化时执行**副作用**（发请求、改 DOM、存 localStorage 等）。

```ts
import { ref, watch } from 'vue'

const id = ref(1)
watch(id, (newVal, oldVal) => {
  console.log(`id 从 ${oldVal} 变成 ${newVal}`)
  fetchData(newVal)
})
```

**4 个重要选项**：

| 选项 | 作用 |
|------|------|
| `immediate: true` | 立即执行一次回调（初始值也算变化） |
| `deep: true` | 深度遍历对象（嵌套属性也侦听） |
| `once: true` | 只触发一次后自动停止 |
| `flush: 'post'` | 在 DOM 更新后触发，默认 `'pre'`（组件更新前） |

### 1.4 `watch` 的多种 source 写法

```ts
// 1) 单个 ref
watch(count, (n) => console.log(n))

// 2) getter 函数（推荐用于派生值）
watch(() => form.username, (n) => console.log(n))

// 3) 多个源（数组）
watch([count, name], ([n1, n2]) => console.log(n1, n2))

// 4) 整个 reactive 对象（默认 deep）
watch(state, (n, o) => console.log(n), { deep: true })
```

### 1.5 `watchEffect`：自动收集依赖

```ts
import { watchEffect } from 'vue'

// 自动追踪回调内用到的所有响应式变量
watchEffect(() => {
  console.log(count.value, name.value)
})
```

**与 `watch` 的区别**：
- `watch`：显式声明侦听谁，可访问 oldValue
- `watchEffect`：自动收集依赖，**立即执行一次**，但拿不到 oldValue

## 2. 代码示例

### 2.1 computed：购物车总价

```vue
<script setup lang="ts">
import { ref, computed } from 'vue'

interface CartItem { name: string; price: number; qty: number }

const cart = ref<CartItem[]>([
  { name: '苹果', price: 5, qty: 2 },
  { name: '香蕉', price: 3, qty: 5 }
])

const total = computed(() =>
  cart.value.reduce((sum, item) => sum + item.price * item.qty, 0)
)

const totalQty = computed(() =>
  cart.value.reduce((sum, item) => sum + item.qty, 0)
)
</script>

<template>
  <div>共 {{ totalQty }} 件，合计 ¥{{ total }}</div>
</template>
```

### 2.2 watch：搜索参数变化时重新查列表

```vue
<script setup lang="ts">
import { ref, watch } from 'vue'

const keyword = ref('')
const list = ref<any[]>([])

watch(keyword, async (newKw) => {
  // 防抖可以加 lodash.debounce
  const res = await fetch(`/api/search?q=${newKw}`)
  list.value = await res.json()
}, { immediate: true })
</script>
```

### 2.3 watch：对象深度侦听

```ts
import { reactive, watch } from 'vue'

const form = reactive({ username: '', profile: { age: 0 } })

// 默认对 reactive 是深度的，不需要 deep: true
watch(form, (n) => {
  console.log('form 变了', JSON.stringify(n))
})

// 只侦听某个嵌套字段（推荐，性能更好）
watch(() => form.profile.age, (n) => console.log('age:', n))
```

### 2.4 常见错误：watch 回调里修改原值

```ts
// ❌ 无限循环：watch 里改自己
watch(count, (n) => { count.value++ })

// ✅ 用 nextTick 或者通过中间变量
let local = 0
watch(count, (n) => { local = n + 1; console.log(local) })
```

## 3. 关键要点总结

- `computed` 用于**派生值**（有缓存、只读）
- `watch` 用于**副作用**（发请求、存本地、跳路由）
- 侦听 reactive 对象**默认是深度的**，侦听单个字段推荐用 getter 函数
- `watchEffect` 适合"自动追踪若干个依赖"但不需要 oldValue 的场景
- 搜索/分页：按钮触发用命令式调用；输入即搜用 `watch` + `debounce`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
