# 小验证：MyBatis Starter / BaseMapper / 分页

> 覆盖：
- [mybatis starter 架构](./07-mybatis-starter.md)
- [MyBatis Plus](./08-mybatis-plus.md)
- [BaseMapper](./09-base-mapper.md)
- [分页插件](./10-pagination.md)
>
> 预计：30～45 分钟 · 改 ruoyi-vue-pro 仓库

## 背景

数据访问是 ruoyi 最常用路径：BaseMapper 与分页插件决定列表接口的默认姿势。

## 需求

在 `/Users/xu/code/github/ruoyi-vue-pro` 中：

1. 选一张系统表（如 `system_dict_type`），用现有 Mapper/Service 做一次分页查询，观察返回的 `PageResult` 结构。
2. 打开 SQL 日志，确认分页插件追加了 `LIMIT`（或对应方言）。
3. **小改动**：给某个已有查询增加一个安全的条件（如按 name 模糊），走 `LambdaQueryWrapper`，不写字符串拼接 SQL。
4. 定位 mybatis starter 的 AutoConfiguration 或分页插件注册处，记下类路径。
5. 说明 BaseMapper 提供了哪些常用 CRUD 方法（列 5 个即可）。

## 提示

- 用本地库，不要在生产库乱改数据。
- `PageParam` / `PageResult` 以项目实际类型为准。
- SQL 日志可在 yaml 中临时打开。

## 验收标准

- [ ] 分页接口或单测返回 total/list 正确
- [ ] SQL 日志可见分页语句
- [ ] 自写条件查询可运行且无 SQL 注入风险
- [ ] starter/分页插件入口路径已记录
- [ ] BaseMapper 常用方法说明到位

## 延伸（选做）

- 对比 `QueryWrapper` 与 `LambdaQueryWrapper` 的类型安全差异。
- 试一次 `selectBatchIds` / `selectByIds`。
