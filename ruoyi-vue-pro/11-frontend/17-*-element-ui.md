# 小验证：Element Plus / 表单表格 / Vben 对比

> 覆盖：
- [Element Plus](./12-element-plus.md)
- [表单](./13-element-form.md)
- [表格](./14-element-table.md)
- [Vben](./15-vben.md)
- [组件库对比](./16-ui-comparison.md)
>
> 预计：30～45 分钟 · 本地练习或改 yudao-ui

## 背景

管理端大量表单表格。用 Element Plus 做一个带校验的 CRUD 列表骨架，并理解 Vben 选型。

## 需求

1. 用 `el-table` 展示本地 mock 列表；`el-pagination` 切换页码。
2. `el-form` 弹窗新增/编辑，字段校验（必填、邮箱）。
3. 删除行需 `ElMessageBox.confirm`。
4. 表单 ref 类型使用合理 TS 写法（如 `InstanceType<typeof ElForm>`）。
5. 书面对比 Element Plus 与 Vben(ant-design-vue) 的选型点 3 条。

## 提示

- mock 可先不用真实 API。
- 可复用 `11-*-ts-ui` 的 `UserVO` / `PageResult`。
- Vben 版本以仓库实际 UI 工程为准。

## 验收标准

- [ ] 表格+分页可用
- [ ] 表单校验拦截非法输入
- [ ] 新增/编辑/删除闭环
- [ ] TS 类型无 any 泛滥
- [ ] 组件库对比 3 条

## 延伸（选做）

- 表格加筛选与排序。
- 同一页面用 a-table 再实现一版（Vben）。
