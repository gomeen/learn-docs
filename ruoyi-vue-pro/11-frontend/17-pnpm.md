# 11.4.3 pnpm workspace

> 掌握 pnpm 的优势（节省磁盘、速度快、严格依赖）和 workspace 多包管理，能在 ruoyi 中管理多个前端项目。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 pnpm 相比 npm/yarn 的优势
- 使用 pnpm workspace 管理多个子项目
- 配置 `pnpm-workspace.yaml`
- 在 ruoyi 的 `yudao-ui/` 目录下管理 5 个子项目

## 📚 前置知识

- npm 基础
- Vite（详见 [Vite](./15-vite.md)）

## 1. 核心概念

### 1.1 什么是 pnpm？

pnpm（performant npm）是新一代 Node 包管理器，特点：
- **节省磁盘**：所有项目共用同一份依赖（hard link + 内容寻址存储）
- **极快安装**：比 npm/yarn 快 2-3 倍
- **严格依赖**：避免"幽灵依赖"（子项目的依赖被父项目错误使用）
- **monorepo 友好**：原生支持 workspace

### 1.2 pnpm vs npm/yarn 对比

| 维度 | npm | yarn | pnpm |
|------|-----|------|------|
| 安装速度 | 慢 | 中 | 快 |
| 磁盘占用 | 大 | 大 | 小（共享） |
| 幽灵依赖 | 有 | 有 | **无** |
| monorepo | Lerna 配合 | workspaces | 原生 |
| lock 文件 | package-lock.json | yarn.lock | pnpm-lock.yaml |

### 1.3 幽灵依赖问题

```bash
# npm/yarn：
# 项目 A 安装了 vue，vue 依赖 vue-router
# 项目 A 可以直接 import vue-router，即使自己没装

# pnpm：
# 必须自己安装 vue-router 才能用
# 避免了版本不一致的隐患
```

### 1.4 pnpm workspace 基础

`pnpm-workspace.yaml` 声明 workspace：

```yaml
# pnpm-workspace.yaml
packages:
  - 'yudao-ui-admin-vue3'
  - 'yudao-ui-admin-vben'
  - 'yudao-ui-admin-vue2'
  - 'yudao-ui-admin-uniapp'
  - 'yudao-ui-mall-uniapp'
  - 'yudao-ui-shop-ant-design'
```

### 1.5 常用命令

```bash
# 在根目录安装所有子项目依赖
pnpm install

# 给指定子项目加依赖
pnpm --filter yudao-ui-admin-vue3 add element-plus
pnpm --filter yudao-ui-admin-vue3 add -D @types/node

# 跨子项目引用
pnpm --filter yudao-ui-admin-vue3 add @yudao-ui/shared@workspace:*

# 在指定子项目跑命令
pnpm --filter yudao-ui-admin-vue3 dev
pnpm --filter yudao-ui-admin-vue3 build

# 所有子项目跑同一命令
pnpm -r dev
pnpm -r build

# 清理
pnpm clean
```

### 1.6 .npmrc 常用配置

```ini
# .npmrc
auto-install-peers=true      # 自动安装 peer 依赖
strict-peer-dependencies=false
shamefully-hoist=false       # 不提升依赖（避免幽灵依赖）
```

## 2. 代码示例

### 2.1 基础使用

```bash
# 安装
npm install -g pnpm

# 初始化项目
pnpm init

# 安装依赖
pnpm add vue
pnpm add -D typescript

# 删除
pnpm remove vue

# 跑 script
pnpm dev
pnpm build
```

### 2.2 创建 workspace

```bash
# 1. 创建根目录
mkdir yudao-ui-monorepo
cd yudao-ui-monorepo

# 2. 创建 pnpm-workspace.yaml
cat > pnpm-workspace.yaml << 'EOF'
packages:
  - 'packages/*'
EOF

# 3. 创建子项目
mkdir -p packages/admin-vue3
cd packages/admin-vue3
pnpm init
```

```yaml
# pnpm-workspace.yaml
packages:
  - 'packages/*'
```

```json
// packages/admin-vue3/package.json
{
  "name": "@yudao/admin-vue3",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "vite build"
  }
}
```

```bash
# 根目录跑 install（自动安装所有子项目）
cd ..
pnpm install

# 在子项目加依赖
pnpm --filter @yudao/admin-vue3 add element-plus
```

### 2.3 共享依赖

```json
// 根目录 package.json：所有子项目共享的依赖
{
  "name": "yudao-ui-monorepo",
  "devDependencies": {
    "typescript": "^5.0.0",
    "eslint": "^8.0.0"
  }
}
```

子项目自动继承根目录的 devDependencies。

### 2.4 跨项目引用

```yaml
# pnpm-workspace.yaml
packages:
  - 'packages/*'
```

```json
// packages/shared/package.json
{ "name": "@yudao/shared", "version": "1.0.0" }
```

```json
// packages/admin-vue3/package.json
{
  "dependencies": {
    "@yudao/shared": "workspace:*"   // 引用 workspace 内的包
  }
}
```

```ts
// 在 admin-vue3 中使用
import { formatDate } from '@yudao/shared'
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 ruoyi 的前端 monorepo 结构

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/`

```
yudao-ui/
├── pnpm-workspace.yaml        # workspace 配置
├── package.json                # 根 package.json
├── .npmrc
└── (各子项目)
    ├── yudao-ui-admin-vue3/        # Vue3 + Element Plus
    ├── yudao-ui-admin-vben/        # Vue3 + ant-design-vue
    ├── yudao-ui-admin-vue2/        # Vue2 + Element UI
    ├── yudao-ui-admin-uniapp/      # 移动端（uni-app）
    └── yudao-ui-mall-uniapp/       # 商城 H5
```

**典型 `pnpm-workspace.yaml`**：

```yaml
packages:
  - 'yudao-ui-admin-vue3'
  - 'yudao-ui-admin-vben'
  - 'yudao-ui-admin-vue2'
  - 'yudao-ui-admin-uniapp'
  - 'yudao-ui-mall-uniapp'
  - 'yudao-ui-shop-ant-design'
```

**典型根 `package.json`**：

```json
{
  "name": "yudao-ui",
  "private": true,
  "scripts": {
    "dev:vue3": "pnpm --filter yudao-ui-admin-vue3 dev",
    "dev:vben": "pnpm --filter yudao-ui-admin-vben dev",
    "dev:uniapp": "pnpm --filter yudao-ui-admin-uniapp dev:mp-weixin",
    "build:vue3": "pnpm --filter yudao-ui-admin-vue3 build",
    "build:vben": "pnpm --filter yudao-ui-admin-vben build"
  },
  "devDependencies": {
    "prettier": "^3.0.0",
    "eslint": "^8.50.0",
    "typescript": "^5.3.0"
  }
}
```

### 3.2 子项目代码的引用约定

虽然本仓库的 vue3 子项目是独立仓库，但根据 ruoyi 的约定，**接口定义**（`src/api/`）在 5 个子项目间**完全一致**：

```ts
// src/api/mes/wm/sn/index.ts（在 Vue3 版本和 Vben 版本中完全一致）
export const WmSnApi = {
  generateSnCodes: async (data: WmSnGenerateVO) => {
    return await request.post({ url: '/mes/wm/sn/generate', data })
  }
}
```

**好处**：
- 后端只提供一套 REST 接口
- 前端选哪个 UI 框架都行
- 切换前端框架不影响后端

### 3.3 与本仓库代码的对照

本仓库 `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/views/mes/wm/sn/index.vue` 是子项目之一的源码。如果用 pnpm workspace 管理：

```bash
# 在根目录
cd /Users/xu/code/github/ruoyi-vue-pro/yudao-ui

# 一次性安装所有子项目
pnpm install

# 进入子项目开发
pnpm dev:vue3  # 等价于 cd yudao-ui-admin-vue3 && pnpm dev
```

## 4. 关键要点总结

- pnpm 三大优势：**节省磁盘、安装快、无幽灵依赖**
- `pnpm-workspace.yaml` 声明 workspace 包含的子项目
- `pnpm --filter xxx <cmd>` 在指定子项目跑命令
- `pnpm -r <cmd>` 在所有子项目跑命令
- 跨项目引用用 `workspace:*` 协议
- ruoyi 用 pnpm 管理 5+ 个前端子项目
- 共享 devDependencies 放在根 `package.json`

## 5. 练习题

### 练习 1：基础（必做）

在一个空目录初始化 pnpm workspace：
- 创建 `pnpm-workspace.yaml`
- 创建 2 个子项目 `app1` 和 `app2`
- 在 `app1` 安装 vue，`app2` 安装 react
- 跑通 `pnpm --filter app1 dev`

### 练习 2：进阶

在 ruoyi 的 `yudao-ui/` 根目录创建 `pnpm-workspace.yaml`，把 5 个子项目声明进去，验证 `pnpm -r ls` 能列出所有子项目。

### 练习 3：挑战（选做）

抽离一个共享的 `@yudao/shared` 包，包含：
- `formatDate(date, pattern)`
- `useRequest<T>(url)` 通用请求 hook
- 在 `admin-vue3` 和 `admin-vben` 中通过 `workspace:*` 引用

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/` 目录结构
- pnpm 官方文档：https://pnpm.io/zh/
- pnpm workspace：https://pnpm.io/zh/workspaces

---

**文档版本**：v1.0
**最后更新**：2026-07-13