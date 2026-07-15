# 11.1.3 生命周期钩子

> 理解 Vue3 组件从创建到销毁的全过程，掌握组合式 API 下的生命周期钩子用法。

## 🎯 学习目标

完成本文档后，你将能够：
- 列出 Vue3 的所有生命周期钩子及其触发时机
- 掌握 `onMounted` / `onUnmounted` / `onUpdated` 等常用钩子
- 理解 `setup` 语法糖下的生命周期写法
- 能在 ruoyi 业务组件中正确使用 `onMounted` 加载初始数据

## 📚 前置知识

- Vue3 基础（详见 [Vue3 基础](./01-vue3-basics.md)）
- JavaScript 同步/异步基础

## 1. 核心概念

### 1.1 什么是生命周期？

组件从**创建 → 挂载 → 更新 → 销毁**经历一系列阶段，每个阶段提供"钩子函数"让开发者插入自定义逻辑。

```
创建阶段          挂载阶段        更新阶段        销毁阶段
─────────         ─────────       ─────────      ─────────
setup            onBeforeMount   onBeforeUpdate  onBeforeUnmount
                 onMounted       onUpdated       onUnmounted

                 onActivated    onBeforeUpdate  onDeactivated
                 (keep-alive)   (keep-alive)
```

### 1.2 Vue3 的生命周期钩子一览

| 钩子 | 触发时机 | 典型用途 |
|------|---------|---------|
| `onBeforeMount` | 组件挂载前 | 准备数据、修改初始 state |
| `onMounted` | 组件挂载完成 | 发请求、绑定 DOM 事件、初始化第三方库 |
| `onBeforeUpdate` | 数据变化、DOM 更新前 | 访问更新前的 DOM |
| `onUpdated` | DOM 更新后 | 操作更新后的 DOM |
| `onBeforeUnmount` | 组件销毁前 | 清理定时器、解绑事件 |
| `onUnmounted` | 组件销毁后 | 最终清理 |
| `onErrorCaptured` | 子组件抛错时 | 错误边界 |
| `onActivated` | keep-alive 激活 | 恢复滚动位置 |
| `onDeactivated` | keep-alive 停用 | 暂停定时器 |

### 1.3 Vue2 vs Vue3 钩子对比

| Vue2 | Vue3 组合式 API |
|------|---------------|
| `beforeCreate` | ❌ 不再需要（setup 替代） |
| `created` | ❌ 不再需要（setup 替代） |
| `beforeMount` | `onBeforeMount` |
| `mounted` | `onMounted` |
| `beforeUpdate` | `onBeforeUpdate` |
| `updated` | `onUpdated` |
| `beforeDestroy` | `onBeforeUnmount` |
| `destroyed` | `onUnmounted` |

### 1.4 组合式 API 的钩子必须在 setup 中同步调用

```ts
// ❌ 错误：在异步函数里调用
setTimeout(() => {
  onMounted(() => {}) // 报错：找不到当前组件实例
}, 100)

// ✅ 正确：同步注册
onMounted(() => {
  // 这里的回调才是异步执行
})
```

## 2. 代码示例

### 2.1 最常用：onMounted 加载数据

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'

const list = ref<any[]>([])

onMounted(async () => {
  const res = await fetch('/api/users')
  list.value = await res.json()
})
</script>
```

### 2.2 清理副作用：onUnmounted

```vue
<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const count = ref(0)
let timer: number | undefined

onMounted(() => {
  timer = window.setInterval(() => {
    count.value++
  }, 1000)
})

onUnmounted(() => {
  // 必须清理，否则组件销毁后定时器还在跑
  if (timer) clearInterval(timer)
})
</script>
```

### 2.3 操作更新后的 DOM

```vue
<script setup lang="ts">
import { ref, onMounted, onUpdated } from 'vue'

const list = ref<string[]>([])
const listRef = ref<HTMLDivElement>()

onMounted(() => {
  list.value = ['a', 'b', 'c']
})

onUpdated(() => {
  // DOM 已更新，可以安全访问子元素
  console.log('现在有', listRef.value?.children.length, '个子元素')
})
</script>

<template>
  <div ref="listRef">
    <div v-for="item in list" :key="item">{{ item }}</div>
  </div>
</template>
```

### 2.4 错误边界：onErrorCaptured

```vue
<!-- 文件：ErrorBoundary.vue -->
<script setup lang="ts">
import { onErrorCaptured, ref } from 'vue'

const error = ref<Error | null>(null)

onErrorCaptured((err) => {
  error.value = err
  // 返回 false 阻止错误继续向上传播
  return false
})
</script>

<template>
  <div v-if="error">出错了：{{ error.message }}</div>
  <slot v-else />
</template>
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 SN 码管理页：onMounted 触发初始查询

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`
**核心代码**（行 245-247）：

```vue
<script setup lang="ts">
// ... 中间省略

/** 查询列表 */
const getList = async () => {
  loading.value = true
  try {
    const data = await WmSnApi.getSnPage(queryParams)
    list.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

// ... 中间省略

onMounted(() => {
  getList()
})
</script>
```

**解读**：
- 第 245 行：`onMounted(() => getList())` —— 组件挂载后**立即查询第一页**
- **为什么用 onMounted 而不是 setup？** 因为 setup 阶段组件还没挂载，如果此时发请求并更新 DOM，可能出现"闪烁"；onMounted 保证 DOM 就绪
- **不需要 onUnmounted**：本组件没有定时器/全局事件，组件销毁时浏览器自动清理
- **模式**：这是 ruoyi 业务组件的**通用模式** —— `onMounted` 调 `getList()` 拉首屏数据

### 3.2 弹窗组件：watch + nextTick 控制聚焦

ruoyi 表单弹窗典型写法（在 onMounted 后让表单自动聚焦第一个字段）：

```ts
import { ref, onMounted, nextTick } from 'vue'

const formRef = ref()

onMounted(() => {
  nextTick(() => {
    // DOM 已就绪，可以调用 el-form 的方法
    formRef.value?.focus()
  })
})
```

**为什么需要 `nextTick`？**
- `onMounted` 触发时，组件挂载但子组件（el-form 内部）可能还没渲染完
- `nextTick` 等当前同步代码执行完 + DOM 更新完，再执行回调

## 4. 关键要点总结

- Vue3 的钩子都以 `onXxx` 形式导出，**必须在 setup 同步调用**
- 最常用：`onMounted`（拉数据）、`onUnmounted`（清理副作用）
- 钩子替代关系：`created` → 直接写在 setup 顶层；`beforeCreate` → 不需要
- 弹窗/对话框组件常用 `onMounted + nextTick` 操作 el-form
- ruoyi 业务组件的"开场"模式：`onMounted` 调首屏查询接口

## 5. 练习题

### 练习 1：基础（必做）

写一个倒计时组件，每秒减 1，归零后停止。要求：用 `onMounted` 启动定时器，`onUnmounted` 清理。

### 练习 2：进阶

为 SN 码管理页增加"离开页面前提示"：当用户输入了搜索关键字但未搜索时，切换路由弹出确认框。提示：使用 `onBeforeUnmount` + `watch` 检测 `queryParams` 是否被修改。

### 练习 3：挑战（选做）

实现一个 `useRequest` 组合式函数，封装"组件挂载时自动发请求" + "组件卸载时取消未完成的请求"。提示：用 `AbortController` + `onUnmounted`。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`
- Vue3 官方：生命周期钩子 https://cn.vuejs.org/api/composition-api-lifecycle.html
- Vue3 官方：`nextTick` https://cn.vuejs.org/api/general.html#nexttick

---

**文档版本**：v1.0
**最后更新**：2026-07-13