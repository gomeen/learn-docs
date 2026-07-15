# 11.1.1 Vue3 组合式 API：setup / ref / reactive

> 掌握 Vue3 的核心入口 `setup` 函数，理解 `ref` / `reactive` 的区别与使用场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Vue3 组合式 API 的设计思想（与 Vue2 选项式 API 的区别）
- 掌握 `ref` 和 `reactive` 的用法、区别与适用场景
- 能够在 `<script setup>` 语法中编写组合式代码
- 能看懂 ruoyi-vue-pro 的 Vue3 业务组件（如 `views/mes/wm/sn/index.vue`）

## 📚 前置知识

- JavaScript ES6+ 基础（箭头函数、解构、模块化）
- Vue2 基础（可选，便于对比）
- 计算属性 / 监听（详见 [computed/watch](./02-computed-watch.md)）

## 1. 核心概念

### 1.1 为什么需要组合式 API？

Vue2 的选项式 API 把代码按 `data` / `methods` / `computed` / `watch` 分块。当组件逻辑复杂时，**同一功能的代码被分散在多个选项里**，复用靠 mixin（命名冲突、维护性差）。

Vue3 的组合式 API 把同一功能的代码**集中在一起**（声明变量 → 计算属性 → 方法 → 监听），并天然支持**逻辑复用**（`useXxx` 函数）。

```text
选项式 API（Vue2）：                组合式 API（Vue3）：
┌─ data()       ──┐               ┌─ const count = ref(0) ──┐
├─ methods       ─┤               ├─ const double = computed ─┤
├─ computed      ─┼─ 同一逻辑      ├─ function inc()         ─┼─ 同一逻辑
├─ watch         ─┤               ├─ watch(count, ...)      ─┤
└─ mounted()     ─┘               └─ onMounted(...)         ─┘
```

### 1.2 `setup` 函数

`setup` 是组合式 API 的**统一入口**，在组件创建之前执行一次。

```ts
import { ref } from 'vue'

export default {
  setup() {
    const count = ref(0)
    function inc() { count.value++ }
    // 返回的东西才能在模板中使用
    return { count, inc }
  }
}
```

`<script setup>` 是**编译时语法糖**，更简洁（无需 return）：

```vue
<script setup lang="ts">
import { ref } from 'vue'
const count = ref(0)
function inc() { count.value++ }
</script>

<template>
  <button @click="inc">{{ count }}</button>
</template>
```

### 1.3 `ref` —— 基本类型与单一值的响应式

`ref` 把任意值包装成**响应式对象**（`.value` 访问）。模板中使用时**自动解包**（不用写 `.value`）。

```ts
const count = ref(0)          // number
const msg = ref('hello')      // string
const list = ref<number[]>([]) // 数组
const user = ref({ name: 'a' }) // 对象（依然建议 .value 访问）

count.value++  // 脚本中必须 .value
// 模板中：{{ count }} 不用 .value
```

**底层原理**：Vue3 用 `Proxy` 拦截 `.value` 的 get/set，触发依赖收集和更新。

### 1.4 `reactive` —— 对象的响应式

`reactive` 只能包装**对象**，把所有属性转为响应式（深度代理）。

```ts
import { reactive } from 'vue'

const state = reactive({
  count: 0,
  user: { name: 'tom', age: 18 }
})

state.count++           // 直接访问属性
state.user.name = 'jerry' // 嵌套也响应
```

### 1.5 `ref` vs `reactive` 选型

| 维度 | `ref` | `reactive` |
|------|-------|-----------|
| 包装值 | 任意值 | 仅对象 |
| 访问方式 | `.value`（脚本中） | 直接属性访问 |
| 解包行为 | 模板自动解包 | 模板直接使用 |
| 解构后是否丢失响应式 | **会**（需 `toRefs`） | **会**（丢失代理） |
| 替换整个值 | `count.value = 10` ✅ | ❌ 会丢失代理 |

**实战经验**：ruoyi-vue-pro 中绝大多数场景用 `ref`，仅在表单对象（多字段、强关联）时用 `reactive`。

## 2. 代码示例

### 2.1 计数器：ref 基础

```vue
<!-- 文件：Counter.vue -->
<script setup lang="ts">
import { ref } from 'vue'

const count = ref<number>(0)
const inc = () => count.value++
const dec = () => count.value--
</script>

<template>
  <div>
    <button @click="dec">-</button>
    <span>{{ count }}</span>
    <button @click="inc">+</button>
  </div>
</template>
```

### 2.2 表单：reactive 用法

```vue
<script setup lang="ts">
import { reactive } from 'vue'

const form = reactive({
  username: '',
  password: '',
  remember: false
})

function submit() {
  console.log(form.username, form.password, form.remember)
}
</script>

<template>
  <form @submit.prevent="submit">
    <input v-model="form.username" />
    <input v-model="form.password" type="password" />
    <input v-model="form.remember" type="checkbox" />
    <button type="submit">提交</button>
  </form>
</template>
```

### 2.3 常见错误：解构丢失响应式

```ts
// ❌ 错误：解构后 count 不再是响应式
const state = reactive({ count: 0 })
const { count } = state
count++ // 不会触发更新

// ✅ 正确：用 toRefs 保持响应式
import { toRefs } from 'vue'
const { count } = toRefs(state)
count.value++ // 触发更新
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 SN 码管理页：典型的 ref 组合式写法

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`
**核心代码**（行 130-152）：

```vue
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
```

**解读**：
- 第 11 行：`<script setup lang="ts">` —— 编译时语法糖 + TypeScript
- 第 13 行：`defineOptions({ name: 'MesWmSn' })` —— 给组件起名（用于 keep-alive、devtools）
- 第 16-17 行：`useMessage()` / `useI18n()` —— 全局注入的组合式函数（composables）
- 第 19-21 行：基本类型用 `ref`，模板自动解包
- 第 22-28 行：表单对象用 `reactive` 直接属性访问
- 第 30 行：`ref<Element>()` 用于持有 DOM 引用

### 3.2 产品收货单 API：接口对象的封装

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/api/mes/wm/productreceipt/index.ts`
**核心代码**（行 22-46）：

```ts
import request from '@/config/axios'

// MES 产品收货单 VO
export interface WmProductRecptVO {
  id: number
  code: string
  name: string
  // ...
}

// MES 产品收货单 API
export const WmProductRecptApi = {
  // 查询产品收货单分页
  getProductRecptPage: async (params: any) => {
    return await request.get({ url: '/mes/wm/product-recpt/page', params })
  },

  // 查询产品收货单详情
  getProductRecpt: async (id: number) => {
    return await request.get({ url: '/mes/wm/product-recpt/get?id=' + id })
  },

  // 新增产品收货单
  createProductRecpt: async (data: WmProductRecptVO) => {
    return await request.post({ url: '/mes/wm/product-recpt/create', data })
  }
}
```

**解读**：
- 第 8-18 行：用 `interface` 定义 VO（View Object）类型，对应后端 Java Bean
- 第 22 行：导出 `XxxApi` 对象（**约定式命名**），集中所有接口方法
- 每个方法都是 `async` 函数，统一通过 `@/config/axios` 封装的 `request` 实例发请求

## 4. 关键要点总结

- `<script setup>` 是 Vue3 推荐写法，无需 `return`，编译器自动暴露
- `ref(0)` 用于基本类型，`reactive({...})` 用于对象
- 模板中 `ref` 自动解包（不写 `.value`），脚本中必须写 `.value`
- 解构 `reactive` 对象会丢失响应式，用 `toRefs` 解决
- ruoyi-vue-pro 的组件遵循"基本类型 ref / 表单对象 reactive"的混用模式

## 5. 练习题

### 练习 1：基础（必做）

用 Vue3 组合式 API 写一个 TodoList 组件，支持添加、删除、勾选完成。
要求：`list` 用 `ref<Todo[]>`、`newTitle` 用 `ref<string>`，勾选状态切换实时更新。

### 练习 2：进阶

阅读 `views/mes/wm/sn/index.vue`，列出该组件用到的所有响应式变量，并判断哪些用 `ref`、哪些用 `reactive`，说明原因。

### 练习 3：挑战（选做）

把 `views/mes/wm/sn/index.vue` 中的 `queryParams` 改写为 `ref` 版本（提示：用 `ref<QueryParams>` 整体包装），并解释这样做可能带来的代价。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/api/mes/wm/sn/index.ts`
- Vue3 官方文档：组合式 API 入门 https://cn.vuejs.org/guide/extras/composition-api-faq.html
- Vue3 `ref` 详解：https://cn.vuejs.org/api/reactivity-core.html#ref

---

**文档版本**：v1.0
**最后更新**：2026-07-13