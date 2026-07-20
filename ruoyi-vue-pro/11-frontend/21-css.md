# 11.4.4 UnoCSS / TailwindCSS

> 掌握原子化 CSS（UnoCSS / TailwindCSS），理解 ruoyi 前端为何大量使用 `class="!w-240px"` 这类写法。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解原子化 CSS 的设计思想
- 掌握 UnoCSS / TailwindCSS 的常用类
- 理解 ruoyi 中 `!w-240px`、`-mb-15px` 等写法的含义
- 在 ruoyi 中正确使用和定制 UnoCSS

## 📚 前置知识

- CSS 基础（选择器、盒模型）
- Vite（详见 [Vite](./18-vite.md)）

## 1. 核心概念

### 1.1 传统 CSS vs 原子化 CSS

**传统 CSS（写 class 名，复用规则）**：

```css
/* styles.css */
.button { padding: 8px 16px; background: blue; color: white; }
.card { padding: 20px; border-radius: 8px; }
```

```html
<button class="button">Click</button>
<div class="card">Hello</div>
```

**原子化 CSS（每个属性对应一个 class）**：

```html
<button class="px-4 py-2 bg-blue-500 text-white rounded">Click</button>
<div class="p-5 rounded-lg">Hello</div>
```

**原子化的优势**：
- 不需要想 class 名（`button-primary` 还是 `btn-main`？）
- CSS 体积小（不写自定义规则）
- 修改样式直接改 class，不用跳 CSS 文件

**原子化的劣势**：
- 模板可读性差（class 字符串很长）
- 学习曲线（要记很多简写）

### 1.2 TailwindCSS vs UnoCSS

| 维度 | TailwindCSS | UnoCSS |
|------|-------------|--------|
| 速度 | 中 | 极快（即时按需生成） |
| 配置 | 复杂（tailwind.config.js） | 灵活（preset） |
| 体积 | 略大 | 最小 |
| Vue 集成 | 良好 | 优秀 |
| ruoyi 采用 | 否 | **是** |

**UnoCSS 优势**：
- 即时按需生成（比 Tailwind 快 5x+）
- 预设兼容 Tailwind（可复用 Tailwind 的类名）
- Vite 插件秒级集成
- 自定义原子规则简单

### 1.3 常用原子类（Tailwind/UnoCSS 通用）

| 类名 | 效果 |
|------|------|
| `w-{n}` | 宽度 n 像素（或 `w-full`、`w-1/2`） |
| `h-{n}` | 高度 n 像素 |
| `p-{n}` | 内边距（`p-1`/`p-2`/`p-4`） |
| `px-{n}` / `py-{n}` | 水平/垂直内边距 |
| `m-{n}` | 外边距 |
| `mx-auto` | 水平居中 |
| `text-{size}` | 字体大小 |
| `text-{color}` | 文字颜色 |
| `bg-{color}` | 背景色 |
| `flex` / `grid` | 弹性/网格布局 |
| `items-center` | 交叉轴居中 |
| `justify-center` | 主轴居中 |
| `rounded` / `rounded-lg` | 圆角 |
| `shadow` | 阴影 |
| `hidden` / `block` | 显示控制 |

### 1.4 ruoyi 中的特殊用法

**`!` 前缀 = important**：

```html
<!-- 等价于：width: 240px !important -->
<div class="!w-240px">
```

**`-` 前缀 = 负值**：

```html
<!-- 等价于：margin-bottom: -15px -->
<div class="-mb-15px">
```

**响应式前缀**：

```html
<!-- 小屏 12 列，中屏 6 列，大屏 4 列 -->
<div class="w-full md:w-1/2 lg:w-1/3">响应式</div>
```

**hover 状态**：

```html
<button class="bg-blue-500 hover:bg-blue-700">悬停变色</button>
```

### 1.5 UnoCSS 配置

```ts
// uno.config.ts
import { defineConfig, presetUno, presetAttributify, presetIcons } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),           // Tailwind 兼容
    presetAttributify(),   // 属性化模式：<div text-red bg-blue>
    presetIcons({          // 图标
      scale: 1.2,
      cdn: 'https://registry.npmjs.org/@iconify-json/ep/'
    })
  ],
  theme: {
    colors: {
      primary: 'var(--el-color-primary)'
    },
  },
  shortcuts: {
    'flex-center': 'flex justify-center items-center'
  }
})
```

## 2. 代码示例

### 2.1 ruoyi 风格：搜索栏布局

```vue
<template>
  <el-form
    class="-mb-15px"           <!-- 负下边距，让表单紧贴下方表格 -->
    :model="queryParams"
    :inline="true"
    label-width="68px"
  >
    <el-form-item label="姓名">
      <el-input
        v-model="queryParams.name"
        placeholder="请输入"
        clearable
        class="!w-240px"      <!-- 强制 240px 宽度 -->
      />
    </el-form-item>
    <el-form-item>
      <el-button type="primary" plain>
        <Icon icon="ep:search" class="mr-5px" />  <!-- mr-5px = 右边距 5px -->
        搜索
      </el-button>
    </el-form-item>
  </el-form>
</template>
```

### 2.2 常见类名速查

```html
<!-- 布局 -->
<div class="flex items-center justify-between">
  <span>左</span>
  <span>右</span>
</div>

<!-- 间距 -->
<div class="p-4 m-2">上下左右 padding 16px，margin 8px</div>
<div class="px-4 py-2">水平 16px，垂直 8px</div>

<!-- 颜色 -->
<div class="bg-blue-500 text-white">蓝底白字</div>
<div class="text-red-500">红色字</div>

<!-- 尺寸 -->
<div class="w-1/2 h-32">宽度 50%，高度 128px</div>
```

### 2.3 Element Plus + 原子类结合

```vue
<el-button class="!w-full">全宽按钮</el-button>
<el-card class="shadow-lg">带阴影卡片</el-card>
<el-table class="!w-full stripe" />
```

### 2.4 常见错误：与传统 CSS 混淆

```vue
<!-- ❌ 错误：style 直接写内联样式（污染原子化） -->
<el-button style="margin-left: 10px">按钮</el-button>

<!-- ✅ 正确：用原子类 -->
<el-button class="ml-2.5">按钮</el-button>

<!-- 或者用 ! 前缀强制 important -->
<el-button class="!ml-2.5">按钮</el-button>
```

## 3. 关键要点总结

- 原子化 CSS = 每个 class 对应一个 CSS 属性（`p-4` = `padding: 16px`）
- ruoyi 用 **UnoCSS**（兼容 Tailwind 类名）
- `!` 前缀 = `!important`，用于覆盖组件库默认样式
- `-` 前缀 = 负值（如 `-mb-15px`）
- 响应式：`sm:` / `md:` / `lg:` 前缀
- UnoCSS 集成在 Vite 中，按需生成，零运行时
- 图标：`class="<Icon icon='ep:search' />"` 来自 Iconify

---

**文档版本**：v1.0
**最后更新**：2026-07-13
