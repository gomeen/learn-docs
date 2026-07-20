# 11.4.2 ESLint + Prettier

> 掌握 ESLint（代码质量）+ Prettier（代码格式化）的协同使用，保证 ruoyi 项目的代码一致性。

## 🎯 学习目标

完成本文档后，你将能够：
- 配置 ESLint 检查 Vue/TS 代码
- 配置 Prettier 统一代码风格
- 让两者协同工作（不打架）
- 在 ruoyi 中执行 `pnpm lint:fix` 修复代码问题

## 📚 前置知识

- Vite（详见 [Vite](./18-vite.md)）
- npm/pnpm 命令行基础（详见 [pnpm](./20-pnpm.md)）

## 1. 核心概念

### 1.1 ESLint vs Prettier

| 工具 | 关注点 | 典型规则 |
|------|--------|---------|
| ESLint | 代码质量 | 未使用变量、`==` vs `===`、`any` 类型 |
| Prettier | 代码风格 | 缩进、换行、引号、尾逗号 |

**为什么两者并存？**
- ESLint 早期也能格式化，但和 Prettier 规则冲突
- 现在约定：**ESLint 管质量，Prettier 管格式**
- 用 `eslint-config-prettier` 关闭 ESLint 的格式规则，让 Prettier 接管

### 1.2 ESLint 配置（Flat Config）

ESLint 9.x 推荐 flat config（`eslint.config.js`）：

```js
// eslint.config.js
import vue from 'eslint-plugin-vue'
import ts from '@typescript-eslint/eslint-plugin'
import prettier from 'eslint-config-prettier'

export default [
  {
    files: ['**/*.{js,ts,vue}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: { console: 'readonly', process: 'readonly' }
    },
    rules: {
      'no-console': 'warn',
      'no-debugger': 'error',
      '@typescript-eslint/no-explicit-any': 'error'
    }
  },
  vue.configs['flat/recommended'],
  prettier  // 必须放最后
]
```

### 1.3 Prettier 配置

```json
// .prettierrc.json
{
  "semi": false,
  "singleQuote": true,
  "trailingComma": "none",
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "arrowParens": "always",
  "endOfLine": "lf"
}
```

| 选项 | 作用 | 常见取值 |
|------|------|---------|
| `semi` | 语句末尾分号 | `true` / `false` |
| `singleQuote` | 单引号 vs 双引号 | `true` / `false` |
| `trailingComma` | 尾逗号 | `'none'` / `'es5'` / `'all'` |
| `printWidth` | 每行最大字符 | `80` / `100` |
| `tabWidth` | 缩进空格数 | `2` / `4` |
| `arrowParens` | 箭头函数参数括号 | `'always'` / `'avoid'` |

### 1.4 关键规则

**TypeScript 严格规则**：

```js
rules: {
  '@typescript-eslint/no-explicit-any': 'error',           // 禁用 any
  '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
  '@typescript-eslint/explicit-function-return-type': 'off', // 允许省略返回类型
  '@typescript-eslint/no-non-null-assertion': 'warn'       // 慎用 !
}
```

**Vue 规则**：

```js
rules: {
  'vue/multi-word-component-names': 'off',       // 允许单字组件名
  'vue/no-v-html': 'error',                       // 禁止 v-html
  'vue/component-definition-name-casing': ['error', 'PascalCase']
}
```

### 1.5 package.json scripts

```json
{
  "scripts": {
    "lint": "eslint . --ext .vue,.js,.ts",
    "lint:fix": "eslint . --ext .vue,.js,.ts --fix",
    "format": "prettier --write \"src/**/*.{vue,ts,js,json,md}\"",
    "type-check": "vue-tsc --noEmit"
  }
}
```

## 2. 代码示例

### 2.1 ESLint 检查未使用变量

```ts
// ❌ ESLint 报错：'count' is defined but never used
function add(a: number, b: number): number {
  const count = a + b
  return a + b
}

// ✅ 修正：删除未使用变量
function add(a: number, b: number): number {
  return a + b
}
```

### 2.2 ESLint 检查 any

```ts
// ❌ ESLint 报错：Unexpected any. Specify a different type
function process(data: any): void {
  console.log(data)
}

// ✅ 修正：使用具体类型
interface DataType { id: number; name: string }
function process(data: DataType): void {
  console.log(data)
}
```

### 2.3 Prettier 格式化示例

```ts
// 格式化前
const  obj={a:1,b:2,c:function() { return  'hello' }}
function   fn( x,y ){return x+y}

// 格式化后（semi: false, singleQuote: true）
const obj = { a: 1, b: 2, c: () => 'hello' }
const fn = (x, y) => x + y
```

### 2.4 常见错误：ESLint 和 Prettier 冲突

```js
// ❌ 错误：Prettier 想加分号，ESLint 不让
// ESLint: 'semi': ['error', 'never']
// Prettier: 'semi': true

// ✅ 解决：用 eslint-config-prettier 关闭 ESLint 的格式规则
import prettier from 'eslint-config-prettier'
export default [
  // ... 其他配置
  prettier  // 必须在最后，覆盖 ESLint 的格式规则
]
```

## 3. 关键要点总结

- **ESLint = 代码质量**（不写 `any`、不用 `==`）
- **Prettier = 代码格式**（缩进、引号、换行）
- 用 `eslint-config-prettier` 关闭 ESLint 的格式规则（避免冲突）
- ruoyi 命令：`pnpm lint:fix` 修复 + `pnpm type-check` 类型检查
- CI 必须 `lint + type-check + build` 三步通过
- Vue 项目用 `eslint-plugin-vue`，TS 项目用 `@typescript-eslint`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
