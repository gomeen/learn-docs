# 11.2.2 接口与泛型

> 掌握 TypeScript 的接口继承、泛型函数、泛型接口，能在 ruoyi 中定义可复用的"通用 API 封装"和"通用分页组件"。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 interface 继承（extends）和声明合并
- 编写泛型函数、泛型接口、泛型约束
- 用泛型实现通用 CRUD 工具
- 能看懂 ruoyi 中 `Api<XxxVO, XxxQueryVO>` 风格的类型

## 📚 前置知识

- TypeScript 基础（详见 [TS 基础](./08-ts-basics.md)）

## 1. 核心概念

### 1.1 interface 继承

```ts
interface Animal {
  name: string
  age: number
}

// 继承单个接口
interface Dog extends Animal {
  breed: string  // 品种
}

const d: Dog = { name: '旺财', age: 3, breed: '柴犬' }

// 继承多个接口
interface Pet { owner: string }
interface Dog extends Animal, Pet {
  breed: string
}
```

### 1.2 接口合并（Declaration Merging）

同名的 `interface` 会自动合并：

```ts
interface User { id: number }
interface User { name: string }  // 自动合并
// User = { id: number; name: string }

const u: User = { id: 1, name: 'tom' }
```

**注意**：`type` 不支持合并，重复声明会报错。

### 1.3 泛型基础

泛型 = **类型的参数化**，让函数/接口能适配多种类型而不丢失类型信息。

```ts
// 不带泛型：用 any 丢失类型
function identity(arg: any): any { return arg }

// 带泛型：调用时才知道类型
function identity<T>(arg: T): T { return arg }

const a = identity<number>(123)   // T = number
const b = identity('hello')        // 自动推断 T = string
```

### 1.4 泛型约束

```ts
// 约束 T 必须有 length 属性
interface HasLength { length: number }

function logLen<T extends HasLength>(arg: T): void {
  console.log(arg.length)
}

logLen('hello')      // ✅ string 有 length
logLen([1, 2, 3])    // ✅ array 有 length
logLen(123)          // ❌ number 没有 length
```

### 1.5 泛型接口

```ts
interface ApiResponse<T> {
  code: number
  msg: string
  data: T
}

interface User { id: number; name: string }

const res: ApiResponse<User> = {
  code: 0,
  msg: 'ok',
  data: { id: 1, name: 'tom' }
}

// 嵌套泛型：列表响应
interface PageResp<T> {
  list: T[]
  total: number
}

const page: PageResp<User> = {
  list: [{ id: 1, name: 'tom' }],
  total: 1
}
```

### 1.6 泛型函数 + 默认值

```ts
// 默认 T = unknown
function process<T = unknown>(data: T): T {
  return data
}

// 默认值 + 约束
function request<T = any, R = ApiResponse<T>>(url: string): Promise<R> {
  return fetch(url).then(r => r.json())
}
```

### 1.7 keyof 与 typeof

```ts
interface User { id: number; name: string; email: string }

// keyof：取所有键的联合类型
type UserKeys = keyof User  // 'id' | 'name' | 'email'

function getProp<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key]
}

const u = { id: 1, name: 'tom', email: 'a@b.com' }
getProp(u, 'name')   // 类型推断为 string
getProp(u, 'xx')     // ❌ 报错：xx 不在 keyof User 中

// typeof：取值的类型
const config = { api: '/api', timeout: 5000 }
type Config = typeof config  // { api: string; timeout: number }
```

## 2. 代码示例

### 2.1 通用分页响应

```ts
// types/common.ts
export interface PageQuery {
  pageNo: number
  pageSize: number
}

export interface PageResp<T> {
  list: T[]
  total: number
}

// 用法
interface UserQuery extends PageQuery { keyword?: string }
const q: UserQuery = { pageNo: 1, pageSize: 10, keyword: 'tom' }

interface UserVO { id: number; name: string }
const res: PageResp<UserVO> = { list: [], total: 0 }
```

### 2.2 通用 CRUD API 类型

```ts
// types/crud.ts
export interface CrudApi<Create, Update = Partial<Create>, Resp = Create, Q extends PageQuery = PageQuery> {
  create: (data: Create) => Promise<void>
  update: (data: Update) => Promise<void>
  delete: (id: number) => Promise<void>
  get: (id: number) => Promise<Resp>
  page: (query: Q) => Promise<PageResp<Resp>>
}
```

```ts
// 使用
interface WmSnCreateVO { snCode: string; itemId: number }
interface WmSnQueryVO extends PageQuery { snCode?: string }

const WmSnApi: CrudApi<WmSnCreateVO, Partial<WmSnCreateVO>, WmSnCreateVO, WmSnQueryVO> = {
  create: async (data) => { ... },
  update: async (data) => { ... },
  delete: async (id) => { ... },
  get: async (id) => { ... },
  page: async (query) => { ... }
}
```

### 2.3 泛型组件 props

```vue
<!-- TableColumn<T>：泛型表格列定义 -->
<script setup lang="ts" generic="T extends Record<string, any>">
interface Column {
  key: keyof T
  label: string
  width?: number
}

interface Props {
  data: T[]
  columns: Column[]
}

defineProps<Props>()
</script>

<template>
  <el-table :data="data">
    <el-table-column v-for="col in columns" :key="col.key" :prop="col.key" :label="col.label" />
  </el-table>
</template>
```

```vue
<!-- 使用 -->
<MyTable :data="users" :columns="[
  { key: 'id', label: 'ID' },
  { key: 'name', label: '姓名' }
]" />
```

### 2.4 常见错误：泛型约束不够

```ts
// ❌ 错误：T 没有约束，访问 length 报错
function logLen<T>(arg: T) {
  console.log(arg.length)
}

// ✅ 正确：约束 T 至少有 length
function logLen<T extends { length: number }>(arg: T) {
  console.log(arg.length)
}
```

## 3. 关键要点总结

- `interface` 可继承 (`extends`)、可合并（同 interface 名自动合并）
- 泛型让类型可参数化：`function identity<T>(arg: T): T`
- 泛型约束：`T extends Xxx` 限制 T 必须满足的形状
- `keyof T` 取出对象所有键的联合，`T[K]` 取出对应值的类型
- ruoyi 的 VO 定义遵循"接口 + VO 后缀 + 字段类型显式标注"的约定
- 进阶：可以用泛型定义通用 `CrudApi<C, U, R, Q>` 接口约束 API 形状

---

**文档版本**：v1.0
**最后更新**：2026-07-13
