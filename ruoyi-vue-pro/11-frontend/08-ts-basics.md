# 11.2.1 TypeScript 基础类型

> 掌握 TypeScript 的基础类型系统，能在 ruoyi 业务组件中正确定义变量、函数参数、接口类型。

## 🎯 学习目标

完成本文档后，你将能够：
- 列出 TS 的所有基础类型（string、number、boolean、array、tuple 等）
- 掌握类型注解、类型推断、类型断言
- 掌握 `interface` 和 `type` 的区别
- 能看懂 ruoyi 业务代码中所有 `interface XxxVO {}` 定义

## 📚 前置知识

- JavaScript ES6+ 基础
- Vue3 基础（详见 [Vue3 基础](./01-vue3-basics.md)）

## 1. 核心概念

### 1.1 为什么要用 TypeScript？

```js
// 纯 JS：编辑器不会提示错误，运行时才崩
function getUser(id) { return fetch(`/api/user/${id}`).then(r => r.json()) }
const u = getUser(123)
console.log(u.nam)  // ❌ typo，运行后 undefined
```

```ts
// TS：编辑器实时提示
function getUser(id: number): Promise<User> { ... }
const u = await getUser(123)
console.log(u.nam)  // ✅ 编辑器红线：Property 'nam' does not exist
```

**核心收益**：
- 编译期发现错误（不用等到运行时）
- IDE 自动补全 + 重构
- 类型即文档（看类型就知道函数需要什么、返回什么）

### 1.2 基础类型

| 类型 | 示例 | 说明 |
|------|------|------|
| `string` | `'hello'` | 字符串 |
| `number` | `123`, `3.14` | 数字（int/float 不分） |
| `boolean` | `true`, `false` | 布尔 |
| `null` | `null` | 空 |
| `undefined` | `undefined` | 未定义 |
| `symbol` | `Symbol('id')` | 唯一值 |
| `bigint` | `100n` | 大整数 |
| `any` | 任意 | ⚠️ 尽量避免 |
| `unknown` | 任意 | 比 any 安全，需要类型守卫 |
| `void` | `undefined` | 函数无返回值 |
| `never` | `throw / 死循环` | 永不返回 |

### 1.3 数组与元组

```ts
// 数组：两种写法等价
const list1: number[] = [1, 2, 3]
const list2: Array<number> = [1, 2, 3]

// 元组：固定长度和类型
const tuple: [string, number] = ['tom', 18]

// 对象数组
interface User { id: number; name: string }
const users: User[] = [{ id: 1, name: 'tom' }]
```

### 1.4 类型注解 vs 类型推断

```ts
// 注解：显式声明类型
let count: number = 10

// 推断：根据值自动推导（推荐，简洁）
let count = 10  // 自动推断为 number
```

### 1.5 类型断言（as）

当你比 TS 更确定类型时，用 `as` 强制指定：

```ts
const el = document.querySelector('#app') as HTMLDivElement
el.innerHTML = 'hello'

// 访问可能为 null 的属性
const input = document.querySelector('input')
;(input as HTMLInputElement).value  // 加括号避免和下一行混淆
```

### 1.6 联合类型与交叉类型

```ts
// 联合：值可以是多种类型之一
let id: string | number = 123
id = 'abc'  // OK

// 类型守卫
if (typeof id === 'string') {
  id.toUpperCase()  // TS 知道这里是 string
}

// 交叉：合并多个类型
type A = { name: string }
type B = { age: number }
type AB = A & B  // { name: string; age: number }
const p: AB = { name: 'tom', age: 18 }
```

### 1.7 常用工具类型

```ts
interface User { id: number; name: string; email: string }

type PartialUser = Partial<User>          // 所有字段可选
type RequiredUser = Required<User>        // 所有字段必填
type PickUser = Pick<User, 'id' | 'name'> // 选取部分字段
type OmitUser = Omit<User, 'email'>       // 排除部分字段
type ReadonlyUser = Readonly<User>        // 所有字段只读

// Record：构造对象类型
type Dict = Record<string, User>  // { [key: string]: User }
```

## 2. 代码示例

### 2.1 基础类型与函数

```ts
// 函数参数与返回值都加类型
function add(a: number, b: number): number {
  return a + b
}

// 可选参数 + 默认值
function greet(name: string, greeting?: string): string {
  return `${greeting ?? 'Hello'}, ${name}`
}

// 箭头函数
const multiply = (a: number, b: number): number => a * b
```

### 2.2 接口定义对象

```ts
interface UserVO {
  id: number
  username: string
  email?: string      // 可选
  readonly createdAt: Date  // 只读
}

const user: UserVO = {
  id: 1,
  username: 'tom',
  createdAt: new Date()
}

// user.createdAt = new Date()  // ❌ 只读属性不能赋值
```

### 2.3 type 与 interface 的区别

```ts
// interface：可扩展、可合并
interface Animal { name: string }
interface Animal { age: number }  // 合并：Animal = { name, age }
const a: Animal = { name: 'tom', age: 1 }

// type：可表达 union、intersection、复杂类型
type Status = 'pending' | 'success' | 'error'  // 字面量联合
type Pair = [string, number]
```

**实践**：描述对象结构用 `interface`，表达 union/复杂类型用 `type`。

### 2.4 常见错误：隐式 any

```ts
// ❌ 错误：参数没有类型，TS 推断为 any（关闭 strict 时）
function process(data) { return data.id }

// ✅ 正确：加类型
function process(data: { id: number }) { return data.id }

// ✅ 推荐：定义接口
interface ProcessData { id: number }
function process(data: ProcessData) { return data.id }
```

## 3. 关键要点总结

- TS 核心价值：编译期类型检查 + IDE 提示
- 基础类型：`string/number/boolean/null/undefined/array/tuple/object`
- 接口 `interface` 描述对象结构，可合并、可扩展
- 类型别名 `type` 表达 union / 交叉 / 复杂类型
- `Partial<T>` / `Required<T>` / `Pick<T, K>` / `Omit<T, K>` 是常用工具类型
- ruoyi 中所有 VO 用 `interface` 定义，所有 API 方法都标注参数类型

---

**文档版本**：v1.0
**最后更新**：2026-07-13
