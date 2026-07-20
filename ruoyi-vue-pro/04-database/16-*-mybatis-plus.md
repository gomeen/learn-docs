# 小验证：MyBatis Plus 基础 CRUD 与条件构造

> 覆盖：
- [MyBatis vs MP](./11-mybatis-vs-mp.md)
- [BaseMapper](./12-base-mapper.md)
- [IService](./13-service-impl.md)
- [条件构造器](./14-query-wrapper.md)
- [分页](./15-mp-pagination.md)
>
> 预计：30～45 分钟 · 改 ruoyi-vue-pro 仓库

## 背景

MP 是 ruoyi 持久层默认姿势。先验证 Service 层 CRUD、条件构造与分页。

## 需求

在 `/Users/xu/code/github/ruoyi-vue-pro` 本地库：

1. 选一个简单 DO（如字典类型/配置），走 Service：新增 → 分页查询 → 更新 → 再查验证。
2. 写一个 `LambdaQueryWrapper` 多条件查询（eq + like + orderBy）。
3. 对比直接用 Mapper 与用 `IService` 的调用差异（各写一处或对照现有代码）。
4. 分页查询确认 `total` 与 `list` 正确。
5. 书面说明：相对原生 MyBatis，MP 在本项目中解决了哪 3 个痛点。

## 提示

- 测试数据用可识别前缀，方便清理。
- 优先用已有 Service，避免重复造轮子。
- 不要用字符串拼接条件。

## 验收标准

- [ ] 新增/查询/更新路径可运行
- [ ] 条件构造查询可运行
- [ ] 分页 total/list 正确
- [ ] Mapper vs IService 差异有说明
- [ ] MP 相对原生 MyBatis 的 3 个痛点说明到位

## 延伸（选做）

- 用 `updateBatchById` 批量更新。
- 试 `selectMaps` / `selectObjs` 各一次。
