# 11.1.4 组件通信：props / emits / provide/inject

> 掌握 Vue3 组件间数据传递的 4 种方式，能在 ruoyi 业务组件中合理拆分组件并传递数据。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 props（父→子）、emits（子→父）、v-model、provide/inject
- 掌握 TypeScript 下的 props 类型定义（接口、`withDefaults`）
- 能在 ruoyi 中拆分大型列表页（搜索栏 + 表格 + 分页）

## 📚 前置知识

- 11-frontend/01-vue3-basics.md
- TypeScript 接口基础

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

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 SN 码页面：典型"大组件"模式

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`
**核心代码**（行 1-72，搜索栏）：

```vue
<template>
  <ContentWrap>
    <!-- 搜索工作栏 -->
    <el-form
      class="-mb-15px"
      :model="queryParams"
      ref="queryFormRef"
      :inline="true"
      label-width="68px"
    >
      <el-form-item label="SN 码" prop="snCode">
        <el-input
          v-model="queryParams.snCode"
          placeholder="请输入 SN 码"
          clearable
          @keyup.enter="handleQuery"
          class="!w-240px"
        />
      </el-form-item>
      <!-- ... 省略其他表单项 ... -->
      <el-form-item>
        <el-button @click="handleQuery">搜索</el-button>
        <el-button @click="resetQuery">重置</el-button>
        <el-button type="primary" plain @click="openForm()" v-hasPermi="['mes:wm-sn:create']">
          生成 SN 码
        </el-button>
      </el-form-item>
    </el-form>
  </ContentWrap>
</template>
```

**解读**：
- 第 2 行：`<ContentWrap>` 是 ruoyi 封装好的布局组件，**用 slot 分发内容**
- 第 6 行：`:model="queryParams"` 是 Element Plus 表单的 props 绑定（父传子）
- 第 7 行：`ref="queryFormRef"` 是模板 ref（用于调 `resetFields` 等方法）
- 第 16 行：`@keyup.enter="handleQuery"` 是事件监听（子传父的一种）
- **设计模式**：搜索栏、表格、分页都写在**同一个大组件**里（≈ 250 行），靠 v-model + ref 通信

### 3.2 弹窗表单：父子通信 + ref 调用

```vue
<!-- 同一文件 line 111-127 -->
<el-dialog :title="'生成 SN 码'" v-model="dialogVisible" width="600px">
  <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px">
    <el-form-item label="物料ID" prop="itemId">
      <el-input-number v-model="formData.itemId" :min="1" />
    </el-form-item>
    <!-- ... -->
  </el-form>
  <template #footer>
    <el-button @click="dialogVisible = false">取消</el-button>
    <el-button type="primary" @click="submitForm" :loading="formLoading">确定</el-button>
  </template>
</el-dialog>
```

```ts
// line 190-207：表单 ref 控制
const formRef = ref()
const formData = ref<WmSnGenerateVO>({ itemId: undefined, snNum: 100 })

/** 重置表单 */
const resetForm = () => {
  formData.value = { itemId: undefined, snNum: 100 }
  formRef.value?.resetFields()  // 调用 el-form 子组件方法
}

/** 提交表单 */
const submitForm = async () => {
  await formRef.value.validate()  // 调用 el-form 的 validate 方法
  // ...
}
```

**解读**：
- `formRef` 是模板 ref（line 190），指向 `<el-form>` 实例
- 通过 `formRef.value.validate()` / `formRef.value.resetFields()` 调用子组件方法 —— **这是父子通信的另一种形式（命令式调用）**
- 比 emit 更直接：父组件知道子组件有这两个方法，直接调

## 4. 关键要点总结

- `defineProps<T>()` 和 `defineEmits<T>()` 是编译时宏
- 默认值用 `withDefaults`，对象/数组用工厂函数
- 解构 props 丢失响应式，用 `toRef` / `toRefs`
- `v-model` = `:modelValue` + `@update:modelValue`
- `provide/inject` 适合跨级共享，但默认不是响应式
- ruoyi 的"大组件"模式：搜索栏/表格/分页写在同一文件，靠模板 ref + v-model 通信

## 5. 练习题

### 练习 1：基础（必做）

写一个 `SearchForm` 子组件，接受 `fields: FormField[]` props，emit `search` 和 `reset` 事件。父组件传入不同字段即可复用。

### 练习 2：进阶

把 SN 码页面的搜索栏**抽离**为独立组件 `SnSearchForm.vue`，通过 `v-model` 双向绑定 `queryParams`。父子如何传值？组件大小能减小多少？

### 练习 3：挑战（选做）

用 `provide/inject` 实现"全站主题切换"：根组件 provide 一个 `theme` ref，任何深层子组件 inject 后能切换并实时响应。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`
- Vue3 官方：`defineProps` https://cn.vuejs.org/api/sfc-script-setup.html#defineprops
- Element Plus `el-form` https://element-plus.org/zh-CN/component/form.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13