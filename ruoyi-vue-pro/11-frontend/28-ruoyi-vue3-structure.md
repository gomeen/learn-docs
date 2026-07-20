# 11.6.1 yudao-ui-admin-vue3 项目结构

> 深入理解 yudao-ui-admin-vue3 项目的目录结构、模块划分、命名约定，能快速定位 ruoyi 业务代码。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 yudao-ui-admin-vue3 的完整目录结构
- 理解每个目录的职责（api、views、store、components 等）
- 在 ruoyi 仓库中快速定位任何业务代码
- 遵循 ruoyi 的命名约定开发新模块

## 📚 前置知识

- Vue3 基础（详见 [Vue3 基础](./01-vue3-basics.md)）
- Pinia（详见 [Pinia](./06-pinia.md)）
- Vue Router（详见 [Vue Router](./05-vue-router.md)）
- Axios 拦截器（详见 [拦截器](./24-interceptor.md)）

## 1. 核心概念

### 1.1 项目定位

**yudao-ui-admin-vue3** 是 ruoyi-vue-pro 的**主推前端模板**：
- 基于 Vue 3 + Vite + TypeScript
- UI 库：Element Plus
- 状态：Pinia
- HTTP：Axios
- 样式：UnoCSS

**仓库位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/`

**独立仓库地址**（推荐从此处拉代码）：
- https://github.com/yudaocode/yudao-ui-admin-vue3
- https://gitee.com/yudaocode/yudao-ui-admin-vue3

### 1.2 顶层目录结构

```
yudao-ui-admin-vue3/
├── public/                         # 静态资源（不会被打包）
│   └── favicon.ico
├── src/
│   ├── api/                        # 接口定义（按业务模块组织）
│   ├── assets/                     # 模块资源（会被打包）
│   ├── components/                 # 全局组件（ContentWrap、Pagination 等）
│   ├── composables/                # 组合式函数（useMessage 等）
│   ├── config/                     # 配置（axios、字典、主题）
│   ├── directives/                 # 自定义指令（v-hasPermi）
│   ├── layout/                     # 整体布局组件
│   ├── plugins/                    # Vue 插件
│   ├── router/                     # 路由
│   ├── store/                      # Pinia store
│   │   └── modules/                # 按业务拆分（user、dict、permission、app）
│   ├── styles/                     # 全局样式
│   ├── utils/                      # 工具函数
│   ├── views/                      # 页面组件（对应路由）
│   ├── App.vue                     # 根组件
│   ├── main.ts                     # 入口文件
│   └── vite-env.d.ts               # Vite 环境类型
├── types/                          # 全局类型
├── index.html                      # HTML 入口
├── vite.config.ts                  # Vite 配置
├── uno.config.ts                   # UnoCSS 配置
├── tsconfig.json                   # TS 配置
├── package.json
├── .env.development                # 开发环境变量
├── .env.production                 # 生产环境变量
├── .eslintrc.cjs                   # ESLint 配置
└── .prettierrc.json                # Prettier 配置
```

### 1.3 src/api/ 目录：接口层

```
src/api/
├── system/                         # 系统管理
│   ├── user.ts
│   ├── role.ts
│   ├── menu.ts
│   └── dict.ts
├── infra/                          # 基础设施
│   ├── file.ts
│   └── config.ts
├── bpm/                            # 工作流
├── mall/                           # 商城
├── mes/                            # MES（制造执行）
│   └── wm/                         # 仓库管理
│       ├── sn/                     # SN 码（本仓库有的代码）
│       └── productreceipt/         # 产品收货单
│           ├── index.ts            # 主表
│           ├── line/               # 行
│           └── detail/             # 明细
└── ...
```

**约定**：每个 API 模块导出 `XxxApi` 对象，每个方法对应一个 HTTP 接口。

### 1.4 src/views/ 目录：页面层

```
src/views/
├── system/                         # 系统管理页面
│   ├── user/                       # 用户管理
│   │   ├── index.vue               # 列表页
│   │   └── form.vue                # 表单弹窗
│   ├── role/
│   └── menu/
├── infra/
├── bpm/
├── mall/
├── mes/
│   └── wm/
│       └── sn/
│           └── index.vue           # SN 码列表
└── ...
```

**约定**：每个业务一个目录，包含 `index.vue`（列表）+ `form.vue`（表单）。

### 1.5 src/components/ 目录：全局组件

```
src/components/
├── ContentWrap/                    # 白色卡片容器
│   └── index.vue
├── Pagination/                     # 分页组件（封装 el-pagination）
│   └── index.vue
├── Icon/                           # 图标组件（基于 Iconify）
│   └── index.vue
└── ...
```

### 1.6 src/store/modules/ 目录：Pinia store

```
src/store/modules/
├── user.ts                         # 用户信息、token、权限
├── permission.ts                   # 路由、动态菜单
├── dict.ts                         # 字典
├── app.ts                          # 侧边栏、布局
└── tenant.ts                       # 多租户
```

### 1.7 src/router/ 目录：路由

```
src/router/
├── index.ts                        # 入口（导出 router 实例）
├── routes/                         # 路由配置
│   ├── index.ts                    # 静态路由
│   └── modules/                    # 按业务模块拆分
│       ├── system.ts
│       ├── infra.ts
│       ├── bpm.ts
│       └── ...
└── guard.ts                        # 路由守卫
```

### 1.8 src/composables/ 目录：组合式函数

```
src/composables/
├── useMessage.ts                   # 消息提示（封装 ElMessage）
├── useI18n.ts                      # 国际化（封装 vue-i18n）
├── useTable.ts                     # 表格通用逻辑（loading、page）
└── useDict.ts                      # 字典加载和获取
```

### 1.9 src/directives/ 目录：自定义指令

```
src/directives/
├── hasPermi.ts                     # v-hasPermi 按钮权限
└── index.ts                        # 统一注册
```

### 1.10 命名约定

| 类型 | 命名 | 示例 |
|------|------|------|
| 组件 | PascalCase | `UserForm.vue` |
| 工具/工具 | camelCase | `formatTime.ts` |
| 页面 | `index.vue` + `form.vue` | `user/index.vue` |
| VO 接口 | XxxVO | `UserVO` |
| API 对象 | XxxApi | `UserApi` |
| Store | useXxxStore | `useUserStore` |
| composable | useXxx | `useMessage` |

## 2. 代码示例

### 2.1 一个新模块的完整结构

以"设备管理"模块为例：

```
src/
├── api/
│   └── mes/
│       └── equipment/
│           ├── index.ts            # EquipmentApi
│           └── types.ts            # EquipmentVO
├── views/
│   └── mes/
│       └── equipment/
│           ├── index.vue           # 列表页
│           └── form.vue            # 表单弹窗
└── router/
    └── routes/
        └── modules/
            └── mes.ts              # 添加路由
```

### 2.2 api/equipment/index.ts 模板

```ts
import request from '@/config/axios'
import type { EquipmentVO, EquipmentQuery } from './types'

export const EquipmentApi = {
  getPage: async (query: EquipmentQuery) => {
    return await request.get({ url: '/mes/equipment/page', params: query })
  },
  get: async (id: number) => {
    return await request.get({ url: `/mes/equipment/get?id=${id}` })
  },
  create: async (data: EquipmentVO) => {
    return await request.post({ url: '/mes/equipment/create', data })
  },
  update: async (data: EquipmentVO) => {
    return await request.put({ url: '/mes/equipment/update', data })
  },
  delete: async (id: number) => {
    return await request.delete({ url: `/mes/equipment/delete?id=${id}` })
  }
}
```

## 3. 关键要点总结

- **src/api/** = 接口定义，按业务模块目录组织
- **src/views/** = 页面组件，每模块 `index.vue + form.vue`
- **src/store/modules/** = Pinia store，按业务拆分
- **src/components/** = 全局通用组件（ContentWrap、Pagination）
- **src/composables/** = 组合式函数（useMessage、useDict）
- **src/router/routes/modules/** = 静态路由配置（按业务拆分）
- 命名约定：VO = XxxVO、API = XxxApi、Store = useXxxStore

---

**文档版本**：v1.0
**最后更新**：2026-07-13
