# 11.4.1 Vite 构建工具

> 掌握 Vite 的核心特性（极速冷启动、HMR、按需编译），理解 ruoyi 前端为何选择 Vite。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Vite 与 Webpack 的差异（dev 启动速度）
- 掌握 Vite 的核心配置（vite.config.ts）
- 使用 Vite 的插件生态（unplugin-vue-components、unplugin-auto-import）
- 在 ruoyi 中配置代理、别名、构建优化

## 📚 前置知识

- ES Module 基础
- 命令行与 npm 基础

## 1. 核心概念

### 1.1 什么是 Vite？

Vite（法语"快"的意思）是 Vue 作者**尤雨溪**开发的下一代前端构建工具，特点：
- **极速冷启动**：基于浏览器原生 ES Module，无需打包
- **毫秒级 HMR**：热更新只更新改动模块
- **开箱即用 TS**：原生支持 TypeScript、JSX、CSS 预处理器
- **Rollup 打包**：生产环境用 Rollup（而非 Webpack），产物更精简

### 1.2 Vite vs Webpack 核心差异

| 维度 | Webpack | Vite |
|------|---------|------|
| Dev 启动 | 启动时打包全部模块 | 按需加载（利用浏览器 ESM） |
| 大型项目启动 | 慢（10s+） | 极快（< 1s） |
| HMR | 整模块替换 | 精确到组件级 |
| 配置复杂度 | 高（loader / plugin） | 低（插件统一接口） |
| 生产构建 | Webpack | Rollup |
| 生态 | 极丰富 | 快速发展 |

### 1.3 Vite 项目结构

```
yudao-ui-admin-vue3/
├── public/                  # 静态资源（不会被打包）
├── src/
│   ├── api/
│   ├── assets/              # 模块资源（会被打包）
│   ├── components/
│   ├── router/
│   ├── store/
│   ├── utils/
│   ├── views/
│   ├── App.vue
│   ├── main.ts
│   └── vite-env.d.ts
├── index.html               # 入口 HTML
├── vite.config.ts           # Vite 配置
├── tsconfig.json
├── package.json
└── env.d.ts
```

### 1.4 核心配置文件 vite.config.ts

```ts
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import path from 'node:path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())
  return {
    plugins: [
      vue(),
      AutoImport({ imports: ['vue', 'vue-router', 'pinia'] }),
      Components({ resolvers: [ElementPlusResolver()] })
    ],
    resolve: {
      alias: { '@': path.resolve(__dirname, 'src') }
    },
    server: {
      port: 3000,
      proxy: {
        '/admin-api': {
          target: env.VITE_BASE_URL,
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/admin-api/, '')
        }
      }
    },
    build: {
      target: 'es2020',
      sourcemap: false,
      rollupOptions: {
        output: {
          manualChunks: {
            vue: ['vue', 'vue-router', 'pinia'],
            element: ['element-plus']
          }
        }
      }
    }
  }
})
```

### 1.5 常用 Vite 插件

| 插件 | 作用 |
|------|------|
| `@vitejs/plugin-vue` | Vue SFC 支持（必需） |
| `unplugin-vue-components` | 自动按需引入组件 |
| `unplugin-auto-import` | 自动按需引入 API（ref/computed/useRouter） |
| `vite-plugin-svg-icons` | SVG 图标 |
| `@vitejs/plugin-legacy` | 兼容旧浏览器 |
| `vite-plugin-compression` | gzip / brotli 压缩 |

### 1.6 环境变量

```bash
# .env.development
VITE_BASE_URL=http://localhost:48080

# .env.production
VITE_BASE_URL=https://api.your-domain.com
```

```ts
// 在代码中使用
console.log(import.meta.env.VITE_BASE_URL)

// 注意：只有 VITE_ 前缀的变量才会暴露给客户端
```

## 2. 代码示例

### 2.1 基础配置

```ts
// vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    open: true  // 自动打开浏览器
  }
})
```

### 2.2 路径别名

```ts
// vite.config.ts
import path from 'node:path'

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  }
})
```

```json
// tsconfig.json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  }
}
```

```ts
// 使用
import request from '@/config/axios'  // 替代 ../../../config/axios
```

### 2.3 代理配置

```ts
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, '')
      }
    }
  }
})
```

```ts
// 请求时
fetch('/api/users')  // 实际请求 http://localhost:8080/users
```

### 2.4 自动按需引入

```ts
// 配置后，无需手动 import
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

plugins: [
  AutoImport({ resolvers: [ElementPlusResolver()] }),
  Components({ resolvers: [ElementPlusResolver()] })
]
```

```vue
<!-- 不需要 import 就能用 -->
<template>
  <el-button>点我</el-button>
</template>
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 ruoyi 的 Vite 配置（约定）

虽然本仓库 vue3 子项目是独立仓库，但根据公开约定，典型配置为：

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/vite.config.ts`

```ts
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { createSvgIconsPlugin } from 'vite-plugin-svg-icons'
import path from 'node:path'

export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, process.cwd())
  return {
    base: './',
    plugins: [
      vue(),
      AutoImport({
        imports: ['vue', 'vue-router', 'pinia'],
        resolvers: [ElementPlusResolver()],
        dts: 'src/auto-imports.d.ts'
      }),
      Components({
        resolvers: [ElementPlusResolver()],
        dts: 'src/components.d.ts'
      }),
      createSvgIconsPlugin({ iconDirs: [path.resolve(__dirname, 'src/assets/icons')] })
    ],
    resolve: {
      alias: { '@': path.resolve(__dirname, 'src') }
    },
    server: {
      host: '0.0.0.0',
      port: 3000,
      open: true,
      proxy: {
        '/admin-api': {
          target: env.VITE_BASE_URL,
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/admin-api/, '')
        },
        '/app-api': {
          target: env.VITE_BASE_URL,
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/app-api/, '')
        }
      }
    },
    build: {
      target: 'es2015',
      cssCodeSplit: true,
      sourcemap: false,
      minify: 'esbuild',
      rollupOptions: {
        output: {
          manualChunks: {
            'vue-vendor': ['vue', 'vue-router', 'pinia'],
            'element-plus': ['element-plus']
          }
        }
      }
    }
  }
})
```

**解读**：
- **第 27 行**：`alias: { '@': path.resolve(__dirname, 'src') }` —— `@/` 指向 `src/`
- **第 32-36 行**：dev server 监听 `0.0.0.0:3000`，自动打开浏览器
- **第 37-44 行**：所有 `/admin-api`、`/app-api` 请求代理到后端
- **第 48 行**：构建目标 ES2015（兼容性最好）
- **第 51 行**：用 esbuild 压缩（速度快）
- **第 52-58 行**：手动分包，vue 核心和 Element Plus 各自打包成单独 chunk（缓存友好）

### 3.2 后端代理的妙用

ruoyi 前端约定：
- 前端所有请求发 `/admin-api/xxx`
- Vite 代理把 `/admin-api` 替换为空，请求转发到后端

这样：
- 前端代码统一 `/admin-api/...` 路径
- 切换环境（开发/测试/生产）只需改 `VITE_BASE_URL`

## 4. 关键要点总结

- Vite 核心优势：dev 启动毫秒级、HMR 精确到组件
- 配置三件套：`plugins`、`resolve.alias`、`server.proxy`
- 自动按需：`unplugin-auto-import`（API）+ `unplugin-vue-components`（组件）
- ruoyi 用 `/admin-api` 前缀统一所有请求，通过 Vite 代理转发
- 生产构建用 Rollup，支持 `manualChunks` 手动分包
- 环境变量必须 `VITE_` 前缀才能在客户端访问

## 5. 练习题

### 练习 1：基础（必做）

初始化一个 Vue3 + Vite + TypeScript 项目，配置 `@/` 别名指向 `src/`，启动 dev server 验证。

### 练习 2：进阶

在 SN 码管理项目中，配置：
- `VITE_BASE_URL` 环境变量（指向 `http://localhost:48080`）
- `/admin-api` 代理到 `VITE_BASE_URL`
- 安装 `unplugin-auto-import` 实现 ref/computed 自动引入

### 练习 3：挑战（选做）

为 SN 码项目实现"按环境切换后端地址"：
- `.env.development`：本地开发
- `.env.staging`：测试环境
- `.env.production`：生产环境
- `pnpm dev` / `pnpm build:staging` / `pnpm build:prod` 三条命令

## 6. 参考资料

- yudao-ui-admin-vue3 公开仓库约定：https://github.com/yudaocode/yudao-ui-admin-vue3
- Vite 官方文档：https://cn.vitejs.dev/
- unplugin-auto-import：https://github.com/antfu/unplugin-auto-import
- unplugin-vue-components：https://github.com/antfu/unplugin-vue-components

---

**文档版本**：v1.0
**最后更新**：2026-07-13