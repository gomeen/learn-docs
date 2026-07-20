# 小验证：TypeScript 基础与 Vue 结合

> 覆盖：
- [TS 基础](./08-ts-basics.md)
- [接口与泛型](./09-ts-interface.md)
- [TS + Vue](./10-ts-vue.md)
>
> 预计：30～45 分钟 · 本地练习或改 yudao-ui

## 背景

管理端以 TS + `<script setup lang="ts">` 为主。先把类型与组合式 API 打牢。

## 需求

1. 定义 `UserVO` 接口与分页 `PageResult<T>` 泛型。
2. 写一个 `ref`/`computed` 驱动的用户列表 composable（或组件 setup），对 `UserVO[]` 做过滤。
3. 给函数参数与返回值标注类型，避免 `any` 泛滥（允许少量边界 any）。
4. 演示可选链/空值合并处理可能为空的字段。
5. 说明 `interface` 与 `type` 在本练习中的选用理由（2～3 行）。

## 提示

- 优先在 yudao-ui 的 demo 页或独立 vite 项目练习。
- `defineProps`/`defineEmits` 使用类型声明。
- 不要关闭 `strict` 来“图省事”。

## 验收标准

- [ ] `UserVO` 与 `PageResult<T>` 定义正确
- [ ] 列表过滤逻辑可运行
- [ ] 类型标注完整，无明显 any 滥用
- [ ] 空值处理有实际代码
- [ ] interface vs type 说明到位

## 延伸（选做）

- 为 API 方法写 `Promise<PageResult<UserVO>>`。
- 试 `Pick` / `Partial` 工具类型改一处表单态。
