# 11.5.2 请求拦截与统一错误处理

> 深入掌握 Axios 拦截器的高级用法：统一 loading、错误码映射、401 处理、防重复提交。

## 🎯 学习目标

完成本文档后，你将能够：
- 在拦截器中统一管理 loading 状态
- 实现 401 自动跳登录（带确认框）
- 实现防重复提交（短时间内同接口只发一次）
- 在 ruoyi 中正确处理业务异常码

## 📚 前置知识

- 11-frontend/19-axios.md
- Promise 链式调用

## 1. 核心概念

### 1.1 拦截器分类

```ts
// 请求拦截器（3 类用途）
request.interceptors.request.use(
  (config) => {
    // 1. 注入通用 header（token、tenantId、traceId）
    // 2. 开启 loading
    // 3. 防重复提交校验
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器（4 类用途）
request.interceptors.response.use(
  (response) => {
    // 1. 关闭 loading
    // 2. 拆业务包（拿 data）
    // 3. 业务码判断
    // 4. 401 处理
    return response
  },
  (error) => {
    // 网络异常 / HTTP 状态码错误
    return Promise.reject(error)
  }
)
```

### 1.2 业务异常码约定（ruoyi）

ruoyi 后端约定的状态码：

| code | 含义 | 前端处理 |
|------|------|---------|
| 0 | 成功 | 返回 data |
| 40101 | token 过期 | 弹确认框 → 重新登录 |
| 40102 | 无权限 | 提示"无权限访问" |
| 403 | 禁止访问 | 提示 |
| 500 | 系统异常 | 通用错误提示 |
| 1xx/2xx | 业务异常（如参数错误） | 用 msg 字段提示 |

### 1.3 loading 全局管理

```ts
let loadingCount = 0
let loadingInstance: any

function showLoading() {
  if (loadingCount === 0) {
    loadingInstance = ElLoading.service({ fullscreen: true })
  }
  loadingCount++
}

function hideLoading() {
  loadingCount--
  if (loadingCount === 0) {
    loadingInstance?.close()
  }
}
```

### 1.4 防重复提交

```ts
const pendingMap = new Map<string, AbortController>()

function addPending(config: any) {
  const key = `${config.method}:${config.url}`
  // 取消上一个同 key 请求
  if (pendingMap.has(key)) {
    pendingMap.get(key)?.abort()
  }
  const controller = new AbortController()
  config.signal = controller.signal
  pendingMap.set(key, controller)
}

function removePending(config: any) {
  const key = `${config.method}:${config.url}`
  pendingMap.delete(key)
}
```

## 2. 代码示例

### 2.1 完整拦截器：loading + 401 + 防重复

```ts
// utils/request.ts
import axios from 'axios'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import router from '@/router'
import { useUserStore } from '@/store/modules/user'

let loadingCount = 0
let loadingInstance: any
const pendingMap = new Map<string, AbortController>()

const request = axios.create({ baseURL: '/admin-api', timeout: 30000 })

request.interceptors.request.use((config: any) => {
  // 1. token
  const userStore = useUserStore()
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }

  // 2. loading
  showLoading()

  // 3. 防重复
  const key = `${config.method}:${config.url}`
  if (pendingMap.has(key)) pendingMap.get(key)?.abort()
  const controller = new AbortController()
  config.signal = controller.signal
  pendingMap.set(key, controller)

  return config
})

request.interceptors.response.use(
  (response) => {
    hideLoading()
    pendingMap.delete(`${response.config.method}:${response.config.url}`)

    if (response.config.responseType === 'blob') return response

    const res = response.data
    if (res.code === 0) return res.data

    if (res.code === 40101) {
      ElMessageBox.confirm('登录已过期', '提示', { type: 'warning' })
        .then(() => {
          userStore.logout()
          router.push('/login')
        })
      return Promise.reject(res)
    }

    ElMessage.error(res.msg || '请求失败')
    return Promise.reject(res)
  },
  (error) => {
    hideLoading()
    if (error.name === 'CanceledError') return Promise.reject(error)
    if (error.response?.status === 401) router.push('/login')
    ElMessage.error(error.message || '网络异常')
    return Promise.reject(error)
  }
)

function showLoading() {
  if (loadingCount === 0) loadingInstance = ElLoading.service()
  loadingCount++
}

function hideLoading() {
  loadingCount = Math.max(0, loadingCount - 1)
  if (loadingCount === 0) loadingInstance?.close()
}

export default request
```

### 2.2 API 模块的取消请求

```ts
export function createOrder(data: any) {
  const controller = new AbortController()
  const promise = request.post({
    url: '/order/create',
    data,
    signal: controller.signal
  })
  // @ts-ignore
  promise.cancel = () => controller.abort()
  return promise
}

// 使用
const p = createOrder(data)
setTimeout(() => p.cancel(), 5000)
```

### 2.3 常见错误：loading 计数泄漏

```ts
// ❌ 错误：loading 在 finally 中无条件 hide，可能少开多关
function fetch() {
  showLoading()
  return request.get(...).finally(() => hideLoading())  // 即使 show 没成功也 hide
}

// ✅ 正确：用计数器 + 确保 show/hide 配对
// 上面完整示例的做法
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 ruoyi 的统一异常处理约定

**约定**：所有 API 方法在组件中通过 `try/catch` 捕获，但**通用错误（401、500、网络异常）由拦截器统一处理**，业务异常由调用方处理。

**示例**：

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`
**核心代码**（行 154-163, 224-231）：

```ts
/** 查询列表 */
const getList = async () => {
  loading.value = true  // 表格局部 loading
  try {
    const data = await WmSnApi.getSnPage(queryParams)
    list.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

/** 删除按钮操作 */
const handleDelete = async (id: number) => {
  try {
    await message.delConfirm()
    await WmSnApi.deleteSnBatch(String(id))
    message.success('删除成功')
    await getList()
  } catch {}
}
```

**解读**：
- **第 3 行**：表格局部 `loading.value = true`（v-loading="loading"）
- **第 9 行**：`finally` 关闭 loading（无论成功失败）
- **第 16-22 行**：删除操作的 `try/catch` 只处理"用户取消确认框"的场景（catch 空块）
- **错误消息**：业务错误由 axios 拦截器统一 ElMessage 提示，这里不需要重复处理
- **成功消息**：业务成功时组件自己 `message.success()` 提示（拦截器不处理）

### 3.2 401 处理的常见模式

```ts
// 拦截器中：401 弹确认框
if (res.code === 40101) {
  ElMessageBox.confirm('登录已过期，是否重新登录？', '提示', {
    type: 'warning',
    confirmButtonText: '重新登录',
    cancelButtonText: '取消'
  }).then(() => {
    // 跳登录
  }).catch(() => {
    // 用户取消
  })
  return Promise.reject(res)
}
```

**为什么用确认框？** 因为可能在用户提交表单时 token 过期，直接跳登录会丢失用户输入；让用户确认更友好。

### 3.3 与本仓库代码的对照

本仓库 `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/api/mes/wm/sn/index.ts` 中的 `WmSnApi` 方法都返回 Promise，**没有 try/catch** —— 因为错误处理都集中在拦截器。

```ts
// API 层：纯函数，不处理错误
export const WmSnApi = {
  getSnPage: async (params: any) => {
    return await request.get({ url: '/mes/wm/sn/page', params })
  }
}

// 组件层：只关心业务成功
const data = await WmSnApi.getSnPage(queryParams)
list.value = data.list  // 直接用，不写错误处理
```

## 4. 关键要点总结

- 拦截器职责：注入 header、loading、业务码判断、401 处理
- ruoyi 业务码约定：`code === 0` 成功，`40101` token 过期
- 防重复：同 URL 同方法的 pending 请求 abort 上一个
- Loading 用计数器管理，避免泄漏
- 业务错误统一由拦截器提示，组件只关心成功逻辑
- 401 用 ElMessageBox.confirm 让用户确认，避免数据丢失

## 5. 练习题

### 练习 1：基础（必做）

实现 axios 拦截器：
- 请求时自动加 token
- 响应时统一 ElMessage 错误提示
- 401 自动跳登录

### 练习 2：进阶

为拦截器增加**重试机制**：网络异常（error.code === 'ERR_NETWORK'）自动重试 3 次，间隔 1s、2s、4s 指数退避。

### 练习 3：挑战（选做）

实现**请求合并**：3 个并发请求 `/user/get?id=1`、`/user/get?id=2`、`/user/get?id=3` 合并成 1 个 `/user/batch-get?ids=1,2,3`。提示：拦截器收集 100ms 内的同类请求，统一发送。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/api/mes/wm/sn/index.ts`
- Axios 拦截器文档：https://axios-http.com/zh/docs/interceptors

---

**文档版本**：v1.0
**最后更新**：2026-07-13