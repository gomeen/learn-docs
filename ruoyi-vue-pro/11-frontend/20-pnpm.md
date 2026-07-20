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
- Vite（详见 [Vite](./18-vite.md)）

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

## 3. 关键要点总结

- pnpm 三大优势：**节省磁盘、安装快、无幽灵依赖**
- `pnpm-workspace.yaml` 声明 workspace 包含的子项目
- `pnpm --filter xxx <cmd>` 在指定子项目跑命令
- `pnpm -r <cmd>` 在所有子项目跑命令
- 跨项目引用用 `workspace:*` 协议
- ruoyi 用 pnpm 管理 5+ 个前端子项目
- 共享 devDependencies 放在根 `package.json`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
