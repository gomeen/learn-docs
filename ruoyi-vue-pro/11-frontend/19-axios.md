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

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 SN 码 API 模块：调用封装的 request

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/api/mes/wm/sn/index.ts`
**核心代码**（行 1-29）：

```ts
import request from '@/config/axios'

// MES SN 码 VO
export interface WmSnVO {
  id: number
  snCode: string
  // ...
}

// MES SN 码 API
export const WmSnApi = {
  // 生成 SN 码
  generateSnCodes: async (data: WmSnGenerateVO) => {
    return await request.post({ url: '/mes/wm/sn/generate', data })
  },

  // 查询 SN 码分页
  getSnPage: async (params: any) => {
    return await request.get({ url: '/mes/wm/sn/page', params })
  },

  // 批量删除 SN 码
  deleteSnBatch: async (ids: string) => {
    return await request.delete({ url: '/mes/wm/sn/delete-batch', params: { ids } })
  },

  // 导出 SN 码 Excel
  exportSnExcel: async (params: any) => {
    return await request.download({ url: '/mes/wm/sn/export-excel', params })
  }
}
```

**解读**：
- 第 1 行：`import request from '@/config/axios'` —— 导入 ruoyi 封装的 axios 实例
- 第 8 行：`request.post({ url, data })` —— 用对象传 config
- 第 14 行：`request.get({ url, params })` —— query 参数放 `params` 字段
- 第 18 行：`request.delete({ url, params })` —— 注意 DELETE 也支持 params（URL 上加 ?ids=）
- 第 23 行：`request.download()` —— **自定义方法**，用于触发文件下载（封装了 blob 处理）

### 3.2 收货单 API：完整的 CRUD 方法

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/api/mes/wm/productreceipt/index.ts`
**核心代码**（行 22-46）：

```ts
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
  },

  // 修改产品收货单
  updateProductRecpt: async (data: WmProductRecptVO) => {
    return await request.put({ url: '/mes/wm/product-recpt/update', data })
  },

  // 删除产品收货单
  deleteProductRecpt: async (id: number) => {
    return await request.delete({ url: '/mes/wm/product-recpt/delete?id=' + id })
  },

  // 提交产品收货单
  submitProductRecpt: async (id: number) => {
    return await request.put({ url: '/mes/wm/product-recpt/submit?id=' + id })
  }
}
```

**解读**：
- **统一命名**：`getXxxPage`（分页查询）、`getXxx`（详情）、`createXxx`（新增）、`updateXxx`（修改）、`deleteXxx`（删除）
- **业务动作**：`submitXxx`、`executeXxx`、`cancelXxx` —— 业务流程方法都用 PUT
- **URL 拼接**：`/get?id=` 直接拼到 URL 上，简单清晰
- **async/await 包裹**：保证返回 Promise

### 3.3 封装的 axios 约定（基于公开仓库）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/config/axios.ts`（约定）

```ts
import axios, { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/store/modules/user'
import router from '@/router'

interface ApiResult<T = any> {
  code: number
  msg: string
  data: T
}

const request = axios.create({
  baseURL: import.meta.env.VITE_BASE_URL + '/admin-api',
  timeout: 30000
})

// ============== 请求拦截器 ==============
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const userStore = useUserStore()
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`
    }
    // 租户 ID
    const tenantId = localStorage.getItem('tenantId')
    if (tenantId) config.headers['tenant-id'] = tenantId
    return config
  },
  (error) => Promise.reject(error)
)

// ============== 响应拦截器 ==============
request.interceptors.response.use(
  (response: AxiosResponse) => {
    // 文件下载直接返回
    if (response.config.responseType === 'blob') return response

    const res = response.data as ApiResult

    if (res.code === 0) return res.data

    // 40101: token 失效
    if (res.code === 40101) {
      ElMessageBox.confirm('登录状态已过期，请重新登录', '提示', {
        confirmButtonText: '重新登录',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        const userStore = useUserStore()
        userStore.logout()
        router.push('/login')
      })
      return Promise.reject(new Error(res.msg))
    }

    ElMessage.error(res.msg || '系统异常')
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

// ============== download 扩展方法 ==============
;(request as any).download = (config: any) => {
  return request({ ...config, responseType: 'blob' }).then((res: any) => {
    const blob = new Blob([res.data])
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = decodeURIComponent(res.headers['content-disposition']?.split('filename=')[1] || 'download')
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  })
}

export default request
```

## 4. 关键要点总结

- 封装 axios = 实例 + 拦截器（请求/响应）
- ruoyi 拦截器约定：业务 code = 0 成功，自动 ElMessage 错误提示
- `responseType: 'blob'` 处理文件下载
- ruoyi 自定义 `request.download()` 简化导出逻辑
- API 模块统一命名：`getXxxPage`、`createXxx`、`updateXxx`、`deleteXxx`
- 401 自动跳登录

## 5. 练习题

### 练习 1：基础（必做）

封装一个 axios 实例，要求：
- baseURL = `/admin-api`
- 请求拦截器自动加 token
- 响应拦截器：成功返回 data，失败 ElMessage 错误提示
- 文件下载方法

### 练习 2：进阶

为 ruoyi 的 axios 封装加**重试机制**：网络异常时自动重试 3 次（指数退避），3 次失败后才报错。

### 练习 3：挑战（选做）

实现**请求并发控制**：限制同时最多 5 个请求，超出的进入队列等待。提示：用 promise + 队列。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/api/mes/wm/sn/index.ts`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/api/mes/wm/productreceipt/index.ts`
- Axios 官方文档：https://axios-http.com/zh/docs/intro

---

**文档版本**：v1.0
**最后更新**：2026-07-13