# 小验证：业务模块结构与分层

> 覆盖：
- [模块划分](./01-module-structure.md)
- [MVC 分层](./02-mvc-layers.md)
- [DTO/VO/DO](./03-dto-vo-do.md)
- [MapStruct 实战](./04-mapstruct-practice.md)
- [CommonResult / PageResult](./05-common-result.md)
>
> 预计：45～75 分钟 · 本地练习或改 ruoyi-vue-pro 仓库

## 背景

先摸清 yudao-module-* 的标准骨架，再谈具体业务。

## 需求

在 `/Users/xu/code/github/ruoyi-vue-pro`：

1. 画出 `yudao-module-system` 的包结构：controller / service / dal / convert / enums。
2. 选一个完整功能（如字典类型），从 Controller → Service → Mapper → DO → Convert → VO 跟读一遍，记下类名。
3. 说明 `CommonResult` / `PageResult` 的字段含义。
4. **小改动**：给某个 RespVO 增加一个已有 DO 字段的映射（Convert 补 `@Mapping` 如需要），接口返回可见。

## 提示

- admin 与 app 包不要混用。
- VO 不要直接当 DO 返回。

## 验收标准

- [ ] 包结构图完成
- [ ] 一条调用链类名列表完整
- [ ] CommonResult/PageResult 说明正确
- [ ] VO 增字段并映射成功
- [ ] 接口响应可见新字段

## 延伸（选做）

- 对比 member 模块与 system 模块结构差异。
- 给 ReqVO 加分组校验。
