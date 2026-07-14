# 11.6.1 yudao-ui-admin-vue3 项目结构

> 深入理解 yudao-ui-admin-vue3 项目的目录结构、模块划分、命名约定，能快速定位 ruoyi 业务代码。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 yudao-ui-admin-vue3 的完整目录结构
- 理解每个目录的职责（api、views、store、components 等）
- 在 ruoyi 仓库中快速定位任何业务代码
- 遵循 ruoyi 的命名约定开发新模块

## 📚 前置知识

- 11-frontend/01-vue3-basics.md
- 11-frontend/06-pinia.md

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

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 本仓库 vue3 子项目结构

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/`

本仓库的 vue3 子项目是独立 git 仓库，目前只包含了 MES 模块的部分代码：

```
yudao-ui-admin-vue3/
├── README.md
└── src/
    ├── api/
    │   └── mes/
    │       └── wm/
    │           ├── sn/
    │           │   └── index.ts          # SN 码 API + VO
    │           └── productreceipt/
    │               ├── index.ts          # 收货单 API + VO
    │               ├── detail/
    │               │   └── index.ts      # 收货单明细 API + VO
    │               └── line/
    │                   └── index.ts      # 收货单行 API + VO
    └── views/
        └── mes/
            └── wm/
                └── sn/
                    └── index.vue         # SN 码列表页
```

### 3.2 接口层命名规范

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/api/mes/wm/sn/index.ts`
**核心代码**（行 1-45）：

```ts
import request from '@/config/axios'

// MES SN 码 VO
export interface WmSnVO {
  id: number
  snCode: string
  // ...
}

// MES SN 码生成 VO
export interface WmSnGenerateVO {
  itemId: number
  batchCode?: string
  workOrderId?: number
  snNum: number
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
- 第 3 行：VO 接口用 `WmSnVO`（`Wm` 前缀 = Warehouse Management 模块）
- 第 15 行：业务操作 VO 用 `WmSnGenerateVO`
- 第 25 行：API 对象导出 `WmSnApi`
- 第 35 行：删除用 `deleteSnBatch`（批量删除，参数是字符串 ID 列表）

### 3.3 页面层结构

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue`
**核心结构**（行 1-128）：

```vue
<template>
  <ContentWrap>
    <!-- 搜索工作栏 -->
    <el-form>...</el-form>
  </ContentWrap>

  <!-- 列表 -->
  <ContentWrap>
    <el-table>...</el-table>
    <Pagination />
  </ContentWrap>

  <!-- 生成对话框 -->
  <el-dialog>...</el-dialog>
</template>

<script setup lang="ts">
import { WmSnApi, WmSnVO, WmSnGenerateVO } from '@/api/mes/wm/sn'

defineOptions({ name: 'MesWmSn' })

// 状态
const loading = ref(true)
const list = ref<WmSnVO[]>([])
const queryParams = reactive({ ... })

// 方法
const getList = async () => { ... }
const handleQuery = () => { ... }
const openForm = () => { ... }
const submitForm = async () => { ... }
const handleDelete = async (id: number) => { ... }

onMounted(() => { getList() })
</script>
```

**解读**：
- 第 1 行：`<ContentWrap>` ruoyi 封装的白色卡片
- 第 7 行：表格 + `<Pagination>` 分页
- 第 13 行：`<el-dialog>` 表单弹窗
- 第 16 行：`defineOptions({ name: 'MesWmSn' })` 组件命名（路由 keep-alive 用）
- 第 28-30 行：`loading + list + queryParams` 标准三件套
- 第 39 行：`onMounted` 触发首屏查询

## 4. 关键要点总结

- **src/api/** = 接口定义，按业务模块目录组织
- **src/views/** = 页面组件，每模块 `index.vue + form.vue`
- **src/store/modules/** = Pinia store，按业务拆分
- **src/components/** = 全局通用组件（ContentWrap、Pagination）
- **src/composables/** = 组合式函数（useMessage、useDict）
- **src/router/routes/modules/** = 静态路由配置（按业务拆分）
- 命名约定：VO = XxxVO、API = XxxApi、Store = useXxxStore

## 5. 练习题

### 练习 1：基础（必做）

在 SN 码项目旁边新增一个"设备管理"模块：
- 创建 `src/api/mes/equipment/index.ts`
- 定义 `EquipmentVO` 接口和 `EquipmentApi` 对象（CRUD 方法）
- 创建 `src/views/mes/equipment/index.vue`（列表 + 表单弹窗）

### 练习 2：进阶

按 ruoyi 约定，把设备管理模块接入到路由和侧边栏菜单。

### 练习 3：挑战（选做）

为 ruoyi 项目写一份"新增模块代码生成脚本"：
- 输入：模块名 `equipment`、中文名 `设备管理`
- 输出：`api/equipment/index.ts`、`views/equipment/index.vue`、`router/modules/equipment.ts` 三个模板文件

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/`
- yudao-ui-admin-vue3 完整文档：https://doc.iocoder.cn/

---

**文档版本**：v1.0
**最后更新**：2026-07-13