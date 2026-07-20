# 小验证：集合 / Stream / Optional / 时间 API

> 覆盖：
- [异常](./07-exception.md)
- [集合框架](./08-collections.md)
- [Stream / Lambda](./09-stream-lambda.md)
- [Optional](./10-optional.md)
- [时间 API](./11-time-api.md)
>
> 预计：30～45 分钟 · 本地练习

## 背景

在集合与函数式 API 上完成一次「用户列表清洗与统计」，并正确处理空值与时间。

## 需求

本地项目（可接续 `06-*-java-basics` 的 `User`），完成：

1. 准备一份 `List<User>` 假数据（含 null 名字、重复 email、`createdAt` 为 `LocalDateTime`）。
2. 用 Stream：过滤无效用户 → 按 `createdAt` 倒序 → 收集 `Map<String, User>`（email → user，冲突时保留较早创建的）。
3. 用 `Optional` 封装“按 email 查找”，找不到返回空而不是 null。
4. 用 `java.time` 计算「近 7 天注册用户数」。
5. 故意触发一处业务异常路径（如非法 email 格式），用 try/catch 或 assertThrows 验证异常类型。

## 提示

- `Collectors.toMap` 记得写 merge function，避免 Duplicate key。
- `findByEmail` 不要返回 null。
- 近 7 天用 `LocalDateTime.now().minusDays(7)` 即可。

## 验收标准

- [ ] Stream 过滤 + 排序 + toMap 结果正确
- [ ] `findByEmail` 返回 `Optional`，无结果不抛 NPE
- [ ] 近 7 天统计与假数据一致
- [ ] 异常路径有可运行验证
- [ ] 无未处理的 raw type / 明显 NPE 风险

## 延伸（选做）

- 用 `YearMonth` 按月分组用户数。
- 对比 `ArrayList` 与 `LinkedHashMap` 在「保序」场景的取舍。
