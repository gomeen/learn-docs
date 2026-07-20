# 小验证：Lombok / MapStruct / Hutool / 日志

> 覆盖：
- [Lombok](./17-lombok.md)
- [MapStruct](./18-mapstruct.md)
- [Hutool](./19-hutool.md)
- [SLF4J + Logback](./20-logging.md)
>
> 预计：30～45 分钟 · 本地练习或改 ruoyi-vue-pro 仓库

## 背景

工程化注解与工具是读 ruoyi 的“倍增器”：DO→VO 映射、空安全、结构化日志。

## 需求

本地小项目（可复用 `16-*-maven-tools` 多模块）：

1. `UserDO` → `UserRespVO`：MapStruct 接口 + `@Mapper`，字段名有一处刻意不一致（如 `userName` ↔ `nickname`），用 `@Mapping` 处理。
2. DO 用 Lombok `@Data` / `@Builder`。
3. Service 里用 Hutool `StrUtil` / `CollUtil` 做空安全处理。
4. 用 SLF4J 打出：入参、映射后 VO、耗时（`System.nanoTime` 即可）；占位符用 `{}`。
5. `mvn -q -DskipTests package` 确认注解处理生成 MapStruct 实现类。

## 提示

- MapStruct 需要 `annotationProcessorPaths` 同时配置 lombok + mapstruct。
- 对照 ruoyi：`yudao-module-system` 下 `*Convert` 接口。
- 日志不要用 `System.out`。

## 验收标准

- [ ] target/generated-sources 中存在 MapStruct 实现
- [ ] 字段重命名映射结果正确（单测或 main 打印）
- [ ] Lombok 生成 getter/builder 可正常使用
- [ ] 日志输出含关键步骤且使用 `{}`
- [ ] Hutool 空安全处理至少一处有实际效果

## 延伸（选做）

- 给 Convert 增加 `List<UserDO> → List<UserRespVO>`。
- 在 logback.xml 里加独立 appender 输出到 `logs/demo.log`。
