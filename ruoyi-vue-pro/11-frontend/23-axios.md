# 11.5.1 Axios 封装

> 掌握 Axios 的二次封装（实例、拦截器、错误处理），理解 ruoyi 的 `@/config/axios` 约定。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Axios 实例化的好处（多 baseURL、不同拦截器）
- 封装通用的 request 实例（拦截器、错误提示）
- 处理文件下载、二进制响应
- 在 ruoyi 的 API 方法中使用封装的 request

## 📚 前置知识

- JavaScript Promise / async/await
- HTTP 基础（请求方法、状态码、headers）
- 拦截器（详见 [拦截器](./24-interceptor.md)）

## 1. 核心概念

### 1.1 为什么封装 Axios？

直接用 `axios.get(...)` 的问题：
- 每个请求都要写完整 URL
- 错误处理重复（`try/catch` 散落各处）
- token 注入重复（每个请求都要加 header）
- loading 状态混乱

封装后统一处理：
- 自动加 baseURL（前缀 `/admin-api`）
- 自动注入 token
- 自动处理 401（跳登录）
- 自动 ElMessage 错误提示

### 1.2 Axios 实例 vs 全局 axios

```ts
// ❌ 用全局 axios：所有请求共享一套配置
axios.defaults.baseURL = '/admin-api'
axios.get('/users')

// ✅ 创建实例：每个实例独立配置（多 baseURL 时特别有用）
const request = axios.create({ baseURL: '/admin-api' })
request.get('/users')
```

### 1.3 拦截器：请求与响应

```ts
// 请求拦截器：发请求前统一处理
request.interceptors.request.use(
  (config) => {
    // 加 token
    config.headers.Authorization = `Bearer ${getToken()}`
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：收到响应后统一处理
request.interceptors.response.use(
  (response) => {
    // 只返回业务 data，去掉外层包装
    return response.data
  },
  (error) => {
    // 统一错误处理
    if (error.response?.status === 401) {
      router.push('/login')
    }
    return Promise.reject(error)
  }
)
```

### 1.4 ruoyi 的请求约定

ruoyi 的后端约定**统一响应格式**：

```json
{
  "code": 0,            // 0 表示成功，其他都是错误
  "msg": "操作成功",
  "data": { ... }       // 业务数据
}
```

前端拦截器统一判断 `code === 0`。

### 1.5 文件下载与二进制

```ts
// 方式 1：responseType blob
const res = await request.get({ url: '/file/download', params: { id }, responseType: 'blob' })
const blob = new Blob([res])
const url = URL.createObjectURL(blob)
const a = document.createElement('a')
a.href = url
a.download = 'file.xlsx'
a.click()

// 方式 2：流式（用于大文件）
const res = await request.get({ url: '/file/stream', responseType: 'stream' })
```

## 2. 代码示例

### 2.1 基础封装

```ts
// utils/request.ts
import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios'

const request: AxiosInstance = axios.create({
  baseURL: '/admin-api',
  timeout: 30000
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('请求失败:', error)
    return Promise.reject(error)
  }
)

export default request
```

### 2.2 完整封装：统一业务处理

```ts
// utils/request.ts
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

interface ApiResult<T = any> {
  code: number
  msg: string
  data: T
}

const request = axios.create({ baseURL: '/admin-api', timeout: 30000 })

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

request.interceptors.response.use(
  (response) => {
    const res = response.data as ApiResult

    // 二进制响应（文件下载）直接返回
    if (response.config.responseType === 'blob') {
      return response.data
    }

    // 业务成功
    if (res.code === 0) {
      return res.data
    }

    // 业务失败：统一提示
    ElMessage.error(res.msg || '请求失败')

    // token 失效
    if (res.code === 401) {
      localStorage.removeItem('token')
      router.push('/login')
    }

    return Promise.reject(new Error(res.msg))
  },
  (error) => {
    if (error.response?.status === 401) {
      router.push('/login')
    } else {
      ElMessage.error(error.message || '网络异常')
    }
    return Promise.reject(error)
  }
)

export default request
```

### 2.3 在 API 模块中使用

```ts
// api/system/user.ts
import request from '@/utils/request'

export const UserApi = {
  getUserPage: (params: any) =>
    request.get({ url: '/system/user/page', params }),

  createUser: (data: any) =>
    request.post({ url: '/system/user/create', data }),

  updateUser: (data: any) =>
    request.put({ url: '/system/user/update', data }),

  deleteUser: (id: number) =>
    request.delete({ url: `/system/user/delete?id=${id}` })
}
```

**注意**：Axios 实例也支持 `request.get(config)` 形式（用对象传 config），ruoyi 用的就是这种风格。

### 2.4 文件下载封装

```ts
export function downloadFile(url: string, filename: string) {
  return request.get({ url, responseType: 'blob' }).then((blob: Blob) => {
    const a = document.createElement('a')
    const linkUrl = URL.createObjectURL(blob)
    a.href = linkUrl
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(linkUrl)
  })
}
```

### 2.5 常见错误：忘记处理 blob 响应

```ts
// ❌ 错误：拦截器对 blob 响应也走业务处理，损坏文件
request.interceptors.response.use((res) => {
  return res.data  // blob 也会被当业务对象处理
})

// ✅ 正确：blob 响应原样返回
request.interceptors.response.use((res) => {
  if (res.config.responseType === 'blob') return res.data
  const r = res.data
  if (r.code === 0) return r.data
  return Promise.reject(r)
})
```

## 3. 关键要点总结

- 封装 axios = 实例 + 拦截器（请求/响应）
- ruoyi 拦截器约定：业务 code = 0 成功，自动 ElMessage 错误提示
- `responseType: 'blob'` 处理文件下载
- ruoyi 自定义 `request.download()` 简化导出逻辑
- API 模块统一命名：`getXxxPage`、`createXxx`、`updateXxx`、`deleteXxx`
- 401 自动跳登录

---

**文档版本**：v1.0
**最后更新**：2026-07-13
