# 11.5.4 接口 Mock：Mock.js / 本地 Mock

> 掌握前端 Mock 数据方案：Mock.js（随机数据）、本地 JSON、Vite Mock 插件，让前端开发不再依赖后端。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解前端 Mock 的意义（并行开发、演示、解耦）
- 掌握 Mock.js 的常用语法（生成随机数据）
- 在 Vite 项目中配置 mock 插件
- 在 ruoyi 中使用 Mock 数据

## 📚 前置知识

- Axios（详见 [Axios](./19-axios.md)）
- RESTful API 基础

## 1. 核心概念

### 1.1 什么是 Mock？

Mock = 在前端模拟后端接口的响应，让前端可以在**后端未完成**或**离线环境**下继续开发。

**典型场景**：
- 后端接口未就绪
- 演示项目（无真实后端）
- 单元测试（不依赖真实后端）
- 并行开发（前后端约定 API 后各自开发）

### 1.2 主流 Mock 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| **Mock.js** | 随机数据生成（姓名、手机号、地址） | 古老、最后更新慢 |
| **vite-plugin-mock** | Vite 原生集成、配置简单 | 仅 Vite 项目 |
| **本地 JSON** | 零依赖、简单 | 无动态逻辑 |
| **MSW (Mock Service Worker)** | 拦截真实 fetch、强大 | 学习曲线 |
| **Apifox / Apipost** | 团队协作、Mock + 文档 | 需平台 |

### 1.3 Mock.js 数据模板语法

```js
import Mock from 'mockjs'

Mock.mock({
  'list|10': [{
    'id|+1': 1,
    name: '@cname',           // 中文名
    email: '@email',
    date: '@date("yyyy-MM-dd")',
    avatar: '@image("200x200")',
    url: '@url',
    ip: '@ip',
    province: '@province'
  }]
})
```

**常用占位符**：

| 占位符 | 含义 |
|--------|------|
| `@cname` | 中文姓名 |
| `@name` | 英文名 |
| `@email` | 邮箱 |
| `@phone` | 手机号 |
| `@id` | 18 位身份证 |
| `@url` | URL |
| `@ip` | IP 地址 |
| `@date('yyyy-MM-dd')` | 日期 |
| `@time('HH:mm:ss')` | 时间 |
| `@datetime` | 日期时间 |
| `@province` / `@city` / `@county` | 省/市/县 |
| `@image('200x200')` | 图片 URL |
| `@paragraph` | 段落 |
| `@csentence(5, 10)` | 中文句子 |

### 1.4 数据模板规则

```js
// | 后面的语法：min-max 或者 count
'list|10': [{ ... }]              // 生成 10 个元素
'list|1-10': [{ ... }]            // 生成 1-10 个元素
'id|+1': 1                        // 自增 1
'age|18-30': 0                    // 18-30 随机整数
'score|60-100.1-2': 0             // 60-100，1-2 位小数
'name|3': 'tom'                   // 'tomtomtom'
'flag|1': true                    // 50% 概率 true
'flag|1-3': true                  // 1/4 概率 true
```

## 2. 代码示例

### 2.1 基础 Mock 数据

```js
import Mock from 'mockjs'

const data = Mock.mock({
  code: 0,
  msg: 'ok',
  'data|10': [{
    id: '@id',
    name: '@cname',
    email: '@email',
    'age|18-60': 0,
    createTime: '@datetime'
  }]
})

console.log(data)
// {
//   code: 0,
//   msg: 'ok',
//   data: [
//     { id: '440000201201011234', name: '张三', email: 'a@b.com', age: 25, createTime: '2024-01-01 12:00:00' },
//     ...
//   ]
// }
```

### 2.2 vite-plugin-mock 完整配置

```bash
pnpm add -D mockjs vite-plugin-mock
```

```ts
// vite.config.ts
import { viteMockServe } from 'vite-plugin-mock'

export default defineConfig({
  plugins: [
    viteMockServe({
      mockPath: 'mock',           // mock 文件目录
      enable: true,                // dev 启用
      logger: true                // 显示 mock 日志
    })
  ]
})
```

```ts
// mock/user.ts
import { MockMethod } from 'vite-plugin-mock'

export default [
  {
    url: '/api/system/user/page',
    method: 'get',
    response: ({ query }) => {
      return {
        code: 0,
        msg: 'ok',
        data: {
          list: Array.from({ length: 10 }, (_, i) => ({
            id: i + 1,
            username: `user${i + 1}`,
            nickname: Mock.Random.cname(),
            email: Mock.Random.email(),
            createTime: Mock.Random.datetime()
          })),
          total: 100
        }
      }
    }
  }
] as MockMethod[]
```

### 2.3 拦截真实请求

```js
// 启动时拦截 /admin-api/* 请求
import Mock from 'mockjs'

Mock.mock(/\/admin-api\/system\/user\/page/, 'get', () => {
  return {
    code: 0,
    msg: 'ok',
    data: { list: [...], total: 100 }
  }
})
```

### 2.4 常见错误：Mock 路径与生产 URL 不一致

```ts
// ❌ 错误：mock 用 /api，但生产用 /admin-api
mock: '/api/user/page'
prod: '/admin-api/user/page'  // 切换环境时失败

// ✅ 正确：保持 URL 一致，只切换 baseURL
mock: '/admin-api/user/page'
prod: '/admin-api/user/page'
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 ruoyi 的 Mock 约定

ruoyi 前端约定：当后端未提供接口时，可临时用 mock 拦截。**生产环境不启用 mock**。

**典型 mock 目录**（约定）：

```
yudao-ui-admin-vue3/
├── mock/                       # mock 文件
│   ├── user.ts
│   ├── role.ts
│   └── ...
└── vite.config.ts
```

### 3.2 通过请求前缀切换 mock

```ts
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      // 真实后端
      '/admin-api-real': {
        target: 'http://localhost:48080',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/admin-api-real/, '')
      }
    }
  }
})
```

前端代码判断：开发时用 `/admin-api`（被 mock 拦截），生产时用 `/admin-api-real`（代理到真后端）。

### 3.3 与本仓库代码的对照

本仓库 `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/api/mes/wm/sn/index.ts` 是真实接口定义。开发时如果后端未就绪：

```ts
// 临时 mock：拦截 /mes/wm/sn/page
import Mock from 'mockjs'

Mock.mock(/\/admin-api\/mes\/wm\/sn\/page/, 'get', () => ({
  code: 0,
  msg: 'ok',
  data: {
    list: Array.from({ length: 10 }, (_, i) => ({
      id: i + 1,
      snCode: `SN${String(i + 1).padStart(6, '0')}`,
      itemId: 100 + i,
      itemCode: `ITEM${i}`,
      itemName: Mock.Random.cname(),
      specification: '标准',
      batchCode: `BATCH${i}`,
      workOrderId: 1,
      createTime: Mock.Random.datetime()
    })),
    total: 100
  }
}))
```

**解读**：
- 前端 `WmSnApi.getSnPage(queryParams)` 不需要改任何代码
- mock 拦截后立即返回假数据
- 后端就绪后删除 mock 即可

### 3.4 使用 MSW（更现代的方案）

```bash
pnpm add -D msw
npx msw init public/ --save
```

```ts
// mocks/handlers.ts
import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/admin-api/mes/wm/sn/page', () => {
    return HttpResponse.json({
      code: 0,
      data: { list: [...], total: 0 }
    })
  })
]

// mocks/browser.ts
import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'
export const worker = setupWorker(...handlers)

// main.ts
if (import.meta.env.DEV) {
  const { worker } = await import('./mocks/browser')
  await worker.start()
}
```

## 4. 关键要点总结

- Mock 让前端**并行开发**、**离线演示**、**解耦后端**
- Mock.js 提供丰富的随机数据占位符（@cname、@email、@datetime）
- vite-plugin-mock 是 Vite 项目的标准 mock 方案
- MSW（Mock Service Worker）是更现代的方案，拦截真实 fetch
- mock URL 与生产 URL 保持一致，只切换拦截逻辑
- 生产环境**不打包 mock**（通过 `if (import.meta.env.DEV)` 判断）

## 5. 练习题

### 练习 1：基础（必做）

用 Mock.js 生成 20 条用户数据：
- id 自增 1-20
- 姓名随机中文
- 邮箱随机
- 年龄 18-60 随机
- 注册时间随机

### 练习 2：进阶

为 SN 码 API 配置 vite-plugin-mock：
- 拦截 `/admin-api/mes/wm/sn/page`
- 返回 10 条随机 SN 码数据
- 拦截 `/admin-api/mes/wm/sn/generate`，返回 `{ code: 0, data: true }`

### 练习 3：挑战（选做）

用 MSW 实现完整的 mock：拦截 ruoyi 所有 CRUD API（增删改查分页），并支持"延迟 500ms 模拟网络"。

## 6. 参考资料

- yudao-ui-admin-vue3 公开约定：https://github.com/yudaocode/yudao-ui-admin-vue3
- Mock.js 文档：http://mockjs.com/
- vite-plugin-mock：https://github.com/vbenjs/vite-plugin-mock
- MSW：https://mswjs.io/

---

**文档版本**：v1.0
**最后更新**：2026-07-13