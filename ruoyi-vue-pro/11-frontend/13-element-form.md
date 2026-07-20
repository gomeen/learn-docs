# 11.3.2 表单组件与校验

> 掌握 Element Plus 表单组件（el-form、el-form-item、校验规则），能在 ruoyi 中实现复杂业务表单。

## 🎯 学习目标

完成本文档后，你将能够：
- 配置 el-form 的 model、rules、ref 三件套
- 编写同步校验、异步校验、自定义校验器
- 处理表单联动（一个字段变化影响其他字段）
- 在 ruoyi 中实现完整的"新增/编辑/详情"表单

## 📚 前置知识

- Element Plus 基础（详见 [Element Plus](./12-element-plus.md)）

## 1. 核心概念

### 1.1 el-form 的三件套

```vue
<el-form
  :model="formData"        <!-- 1. 绑定数据 -->
  :rules="formRules"       <!-- 2. 绑定校验规则 -->
  ref="formRef"            <!-- 3. 模板 ref，调 validate/resetFields -->
  label-width="100px"      <!-- 标签宽度 -->
  label-position="right"   <!-- 标签位置：right / top / left -->
>
  <el-form-item label="姓名" prop="name">  <!-- prop 必须与 rules 中的字段名一致 -->
    <el-input v-model="formData.name" />
  </el-form-item>
</el-form>
```

### 1.2 校验规则的 4 种写法

```ts
import type { FormRules } from 'element-plus'

const formRules: FormRules = {
  // 写法 1：单规则
  name: [
    { required: true, message: '姓名不能为空', trigger: 'blur' }
  ],

  // 写法 2：多规则
  email: [
    { required: true, message: '邮箱不能为空', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],

  // 写法 3：自定义校验器（validator）
  password: [
    { required: true, message: '密码不能为空' },
    {
      validator: (rule, value, callback) => {
        if (value.length < 6) callback(new Error('至少 6 位'))
        else callback()
      },
      trigger: 'blur'
    }
  ],

  // 写法 4：异步校验（用户名是否已注册）
  username: [
    {
      validator: async (rule, value) => {
        if (!value) return
        const exists = await api.checkUsername(value)
        if (exists) throw new Error('用户名已被占用')
      },
      trigger: 'blur'
    }
  ]
}
```

### 1.3 校验触发方式

| trigger | 何时触发校验 |
|---------|-------------|
| `'blur'` | 失焦时 |
| `'change'` | 值变化时 |
| `'blur change'` | 二者之一 |

### 1.4 表单方法

通过 `formRef` 调用：

```ts
const formRef = ref<FormInstance>()

// 整体校验
async function submit() {
  await formRef.value?.validate()  // 通过返回 Promise<true>，失败抛错
  // 校验通过，执行保存
}

// 部分校验
await formRef.value?.validateField(['name', 'email'])

// 重置整个表单（值+校验状态）
formRef.value?.resetFields()

// 清空校验状态
formRef.value?.clearValidate()
```

### 1.5 动态校验：新增/删除字段

```ts
// 动态添加规则
formRules.value.newField = [{ required: true, message: '新增字段必填' }]

// 删除规则
delete formRules.value.newField
```

### 1.6 表单联动

```vue
<script setup lang="ts">
const form = reactive({ type: 1, value: '' })

// type = 2 时 value 必填
const rules = computed<FormRules>(() => ({
  value: [
    { required: form.type === 2, message: '当类型为 2 时必填', trigger: 'change' }
  ]
}))
</script>
```

## 2. 代码示例

### 2.1 完整表单：用户注册

```vue
<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'

const formRef = ref<FormInstance>()
const form = reactive({
  username: '',
  password: '',
  confirm: '',
  email: ''
})

const rules: FormRules = {
  username: [
    { required: true, message: '用户名不能为空', trigger: 'blur' },
    { min: 3, max: 20, message: '长度 3-20', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '密码不能为空' },
    { min: 6, message: '至少 6 位', trigger: 'blur' }
  ],
  confirm: [
    { required: true, message: '请确认密码' },
    {
      validator: (_r, value, cb) => {
        if (value !== form.password) cb(new Error('两次密码不一致'))
        else cb()
      },
      trigger: 'blur'
    }
  ],
  email: [
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ]
}

async function onSubmit() {
  await formRef.value?.validate()
  console.log('提交', form)
}
</script>

<template>
  <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
    <el-form-item label="用户名" prop="username">
      <el-input v-model="form.username" />
    </el-form-item>
    <el-form-item label="密码" prop="password">
      <el-input v-model="form.password" type="password" />
    </el-form-item>
    <el-form-item label="确认密码" prop="confirm">
      <el-input v-model="form.confirm" type="password" />
    </el-form-item>
    <el-form-item label="邮箱" prop="email">
      <el-input v-model="form.email" />
    </el-form-item>
    <el-form-item>
      <el-button type="primary" @click="onSubmit">注册</el-button>
    </el-form-item>
  </el-form>
</template>
```

### 2.2 异步校验：检查用户名

```ts
const rules: FormRules = {
  username: [
    {
      validator: async (_r, value, callback) => {
        if (!value) return callback()
        // 防抖：500ms 内只请求一次
        clearTimeout(timer)
        await new Promise(r => setTimeout(r, 300))
        try {
          const exists = await api.checkUsernameExists(value)
          if (exists) callback(new Error('用户名已被占用'))
          else callback()
        } catch (e) {
          callback()  // 网络错误不阻断提交
        }
      },
      trigger: 'blur'
    }
  ]
}
```

### 2.3 表单联动：选类型决定是否显示字段

```vue
<script setup lang="ts">
import { reactive, computed } from 'vue'

const form = reactive({ type: 1, name: '', reason: '' })

const rules = computed<FormRules>(() => ({
  reason: [
    { required: form.type === 2, message: '请填写原因', trigger: 'change' }
  ]
}))
</script>

<template>
  <el-form :model="form" :rules="rules">
    <el-form-item label="类型">
      <el-select v-model="form.type">
        <el-option label="类型1" :value="1" />
        <el-option label="类型2" :value="2" />
      </el-select>
    </el-form-item>
    <el-form-item v-if="form.type === 2" label="原因" prop="reason">
      <el-input v-model="form.reason" />
    </el-form-item>
  </el-form>
</template>
```

### 2.4 常见错误：prop 与 v-model 字段不一致

```vue
<!-- ❌ 错误：prop="username" 但 v-model 绑定 user.name -->
<el-form-item label="姓名" prop="username">
  <el-input v-model="user.name" />  <!-- 校验永远不生效 -->
</el-form-item>

<!-- ✅ 正确：保持一致 -->
<el-form :model="user">
  <el-form-item label="姓名" prop="name">
    <el-input v-model="user.name" />
  </el-form-item>
</el-form>
```

## 3. 关键要点总结

- el-form 三件套：`:model`、`:rules`、`ref`
- 校验规则写在 `:rules` 中，prop 必须对应 `v-model` 的字段
- 校验触发：`'blur'`（失焦）、`'change'`（变化）
- `formRef.value.validate()` 必须 await，否则不会阻塞
- 动态校验用 `computed<FormRules>` 派生
- ruoyi 模式：弹窗打开前**先重置**，提交用 `try/finally` 关闭 loading
- 表单数据用 `ref<T>`，校验规则用 `reactive`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
