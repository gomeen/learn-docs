# 11.1.6 状态管理：Pinia

> 掌握 Pinia 的 store 定义、组合式风格、持久化，能在 ruoyi 中管理用户信息、字典、租户等全局状态。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Pinia 相比 Vuex 的优势（更轻量、TS 友好）
- 定义 state / getter / action 三件套
- 掌握 setup 风格的 store 写法
- 能看懂 ruoyi 的 `useUserStore` / `useDictStore` 等 store

## 📚 前置知识

- 11-frontend/01-vue3-basics.md
- 11-frontend/05-vue-router.md

## 1. 核心概念

### 1.1 为什么需要 Pinia？

Vuex（Vue2 时代）的痛点：
- mutation / action 概念分裂（同步/异步）
- TypeScript 支持差
- 模块嵌套深，store 体积臃肿

Pinia（Vue3 官方推荐）的优势：
- **极简 API**：state / getter / action 三件套，没有 mutation
- **天然 TS 友好**：自动推断类型
- **支持 Composition 风格**：可以像写 composable 一样写 store
- **支持多个 store**：按业务拆分（user、dict、permission、app）

### 1.2 Pinia 三件套

| 概念 | 作用 | 类似 Vuex |
|------|------|---------|
| `state` | 存储数据（ref） | `state` |
| `getter` | 派生值（computed） | `getter` |
| `action` | 改 state 的方法（function） | `mutation` + `action` |

### 1.3 Option 风格（Vuex 迁移友好）

```ts
// stores/user.ts
import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: '',
    userInfo: { id: 0, name: '' }
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
    userName: (state) => state.userInfo.name
  },
  actions: {
    setToken(token: string) { this.token = token },
    async fetchUserInfo() {
      const data = await api.getUserInfo()
      this.userInfo = data
    }
  }
})
```

### 1.4 Setup 风格（推荐，更灵活）

```ts
// stores/user.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  const token = ref('')
  const userInfo = ref({ id: 0, name: '' })

  const isLoggedIn = computed(() => !!token.value)
  const userName = computed(() => userInfo.value.name)

  function setToken(t: string) { token.value = t }
  async function fetchUserInfo() {
    userInfo.value = await api.getUserInfo()
  }

  // 必须返回 state + action（getter 已经是 ref，组件会自动解包）
  return { token, userInfo, isLoggedIn, userName, setToken, fetchUserInfo }
})
```

### 1.5 在组件中使用

```vue
<script setup lang="ts">
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// 读取
console.log(userStore.token, userStore.userName)

// 改 state
userStore.token = 'xxx'

// 调 action
await userStore.fetchUserInfo()
</script>
```

### 1.6 持久化

Pinia 默认**不持久化**，刷新页面 state 全清。常用插件 `pinia-plugin-persistedstate`：

```ts
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'

const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)
app.use(pinia)
```

```ts
// stores/user.ts
export const useUserStore = defineStore('user', () => {
  // ...
  return { token, userInfo, setToken, fetchUserInfo }
}, {
  persist: {
    key: 'user-store',
    storage: localStorage,
    paths: ['token']  // 只持久化 token
  }
})
```

## 2. 代码示例

### 2.1 计数器 store

```ts
// stores/counter.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useCounterStore = defineStore('counter', () => {
  const count = ref(0)
  const double = computed(() => count.value * 2)

  function inc() { count.value++ }
  function reset() { count.value = 0 }

  return { count, double, inc, reset }
})
```

```vue
<!-- Counter.vue -->
<script setup lang="ts">
import { useCounterStore } from '@/stores/counter'
import { storeToRefs } from 'pinia'

const store = useCounterStore()
const { count, double } = storeToRefs(store)  // 保持响应式

const inc = () => store.inc()
</script>

<template>
  <div>{{ count }} - {{ double }} <button @click="inc">+</button></div>
</template>
```

### 2.2 异步 action

```ts
export const useUserStore = defineStore('user', () => {
  const userInfo = ref<UserInfo>()
  const loading = ref(false)

  async function login(form: LoginForm) {
    loading.value = true
    try {
      const { token } = await api.login(form)
      return token
    } finally {
      loading.value = false
    }
  }

  return { userInfo, loading, login }
})
```

### 2.3 常见错误：解构 store 丢失响应式

```ts
// ❌ 错误：解构后 count 不再响应
const store = useCounterStore()
const { count } = store  // 普通 number

// ✅ 正确：用 storeToRefs
const { count } = storeToRefs(store)  // Ref<number>

// action 可以直接解构（方法本身不是响应式）
const { inc } = store  // ✅ OK
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 ruoyi 的 Pinia store 约定结构

虽然本仓库的 vue3 子项目是独立 git 仓库（只包含了 MES 模块的 src），但根据公开约定，典型 store 结构如下：

```
src/store/modules/
├── user.ts          # 用户信息、token、权限
├── permission.ts    # 路由、动态菜单
├── dict.ts          # 字典（label/value 转换）
├── app.ts           # 侧边栏折叠、布局大小
└── tenant.ts        # 多租户切换
```

### 3.2 user store（典型实现）

```ts
// store/modules/user.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { loginApi, logoutApi, getUserInfoApi } from '@/api/login'

export const useUserStore = defineStore('user', () => {
  const token = ref('')
  const userInfo = ref<UserVO>()
  const permissions = ref<string[]>([])

  const isLoggedIn = computed(() => !!token.value)
  const roles = computed(() => userInfo.value?.roles ?? [])

  async function login(form: LoginForm) {
    const { token: t } = await loginApi(form)
    token.value = t
  }

  async function fetchUserInfo() {
    const data = await getUserInfoApi()
    userInfo.value = data.user
    permissions.value = data.permissions
  }

  async function logout() {
    await logoutApi()
    token.value = ''
    userInfo.value = undefined
    permissions.value = []
  }

  return { token, userInfo, permissions, isLoggedIn, roles, login, fetchUserInfo, logout }
}, {
  persist: {  // 持久化 token
    key: 'user-store',
    storage: localStorage,
    paths: ['token']
  }
})
```

**解读**：
- **Setup 风格**：用 `ref/computed/function` 写 state/getter/action
- **`persist`**：只持久化 token（userInfo 和 permissions 每次启动从后端拉）
- **典型三方法**：login（设置 token）、fetchUserInfo（拉用户信息+权限）、logout（清空）
- **permissions 数组**：存的是 `['mes:wm-sn:query', 'system:user:create']` 这样的权限字符串，配合 `v-hasPermi` 指令做按钮级权限控制

### 3.3 字典 store（典型实现）

```ts
// store/modules/dict.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getDictDataListApi } from '@/api/system/dict'

/**
 * 字典存储：
 * dictMap = { 'sys_user_sex': [{value: 1, label: '男'}, {value: 2, label: '女'}], ... }
 */
export const useDictStore = defineStore('dict', () => {
  const dictMap = ref<Record<string, DictDataVO[]>>({})

  async function loadDict(dictType: string) {
    if (dictMap.value[dictType]) return  // 已加载过，不重复请求
    const list = await getDictDataListApi(dictType)
    dictMap.value[dictType] = list
  }

  function getDict(dictType: string) {
    return dictMap.value[dictType] ?? []
  }

  return { dictMap, loadDict, getDict }
})
```

```vue
<!-- 使用 -->
<script setup lang="ts">
const dictStore = useDictStore()

await dictStore.loadDict('sys_user_sex')
const sexOptions = computed(() => dictStore.getDict('sys_user_sex'))
</script>

<template>
  <el-select v-model="form.sex">
    <el-option v-for="o in sexOptions" :key="o.value" :label="o.label" :value="o.value" />
  </el-select>
</template>
```

**解读**：
- **懒加载**：第一次用某个字典才发请求
- **缓存**：dictMap 存到 store，避免重复请求
- **典型 ruoyi 模式**：`<el-select>` 显示"用户性别"等枚举值时，**全部走字典**，不硬编码

## 4. 关键要点总结

- Pinia = Vuex 的继任者，没有 mutation，action 可以直接改 state
- 推荐 **Setup 风格**写 store（`ref + computed + function`）
- 解构 store 用 `storeToRefs` 保持响应式
- 持久化用 `pinia-plugin-persistedstate`
- ruoyi 典型 store：`useUserStore`（用户+token+权限）、`useDictStore`（字典）、`usePermissionStore`（路由）

## 5. 练习题

### 练习 1：基础（必做）

实现 `useCounterStore`，包含 `count` state、`inc/dec/reset` actions、`double` getter，并用 `storeToRefs` 在组件中使用。

### 练习 2：进阶

实现 `useCartStore`：购物车商品数组、添加/删除商品 action、总价 getter。要求**持久化到 localStorage**。

### 练习 3：挑战（选做）

为 ruoyi 实现 `usePermissionStore`：登录后调用 `fetchMenus()` 拉菜单树，存储 `dynamicRoutes`，暴露 `loadDynamicRoutes()` action 动态 `router.addRoute`。

## 6. 参考资料

- yudao-ui-admin-vue3 公开仓库约定：https://github.com/yudaocode/yudao-ui-admin-vue3
- Pinia 官方文档：https://pinia.vuejs.org/zh/
- pinia-plugin-persistedstate：https://prazdevs.github.io/pinia-plugin-persistedstate/zh/

---

**文档版本**：v1.0
**最后更新**：2026-07-13