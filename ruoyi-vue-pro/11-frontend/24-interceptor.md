# 11.5.2 请求拦截与统一错误处理

> 深入掌握 Axios 拦截器的高级用法：统一 loading、错误码映射、401 处理、防重复提交。

## 🎯 学习目标

完成本文档后，你将能够：
- 在拦截器中统一管理 loading 状态
- 实现 401 自动跳登录（带确认框）
- 实现防重复提交（短时间内同接口只发一次）
- 在 ruoyi 中正确处理业务异常码

## 📚 前置知识

- Axios 封装（详见 [Axios](./23-axios.md)）
- Promise 链式调用
- JWT / Token 鉴权（请求头携带，详见 [JWT](../../_common/07-authentication/03-jwt.md)、[Token + Redis](../06-security/03-token-redis.md)）

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

## 3. 关键要点总结

- 拦截器职责：注入 header、loading、业务码判断、401 处理
- ruoyi 业务码约定：`code === 0` 成功，`40101` token 过期
- 防重复：同 URL 同方法的 pending 请求 abort 上一个
- Loading 用计数器管理，避免泄漏
- 业务错误统一由拦截器提示，组件只关心成功逻辑
- 401 用 ElMessageBox.confirm 让用户确认，避免数据丢失

---

**文档版本**：v1.0
**最后更新**：2026-07-13
