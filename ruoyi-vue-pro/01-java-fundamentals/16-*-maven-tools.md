# 小验证：Maven 多模块与生命周期

> 覆盖：
- [Maven 多模块](./13-maven-modules.md)
- [BOM 与 dependencyManagement](./14-maven-bom.md)
- [生命周期与插件](./15-maven-lifecycle.md)
>
> 预计：30～45 分钟 · 本地练习或对照 ruoyi-vue-pro 仓库

## 背景

读 ruoyi 源码前先摸清多模块与 BOM。本验证用最小多模块骨架走通依赖管理与打包。

## 需求

在本地完成（可用独立小项目，或对照 `/Users/xu/code/github/ruoyi-vue-pro`）：

1. 建两个模块：`demo-api`、`demo-service`，父 POM 统一 `groupId`/`version`。
2. 父 POM 用 `dependencyManagement` 管理至少 2 个依赖版本（如 junit、slf4j）；子模块不写 version。
3. `demo-service` 依赖 `demo-api`，写一个可编译的类互相引用。
4. 执行 `mvn -q -DskipTests package`，确认 reactor 顺序与产物 jar。
5. 对照 ruoyi：指出 `yudao-dependencies`（BOM）与业务模块的依赖关系（路径 + 一句话）。

## 提示

- 子模块不要各自乱定版本号。
- 可用 `mvn help:effective-pom -pl demo-service` 核对版本是否被管理。
- 插件生命周期：至少知道 `compile` / `test` / `package` 三阶段。

## 验收标准

- [ ] 多模块可 `mvn package` 成功
- [ ] 子模块依赖无显式 version（由父管理）
- [ ] 模块间依赖可编译
- [ ] 能口述 ruoyi 父 POM / BOM 与业务模块关系
- [ ] 说明一次 `package` 大致执行了哪些生命周期阶段

## 延伸（选做）

- 给父 POM 加 `maven-compiler-plugin` 统一 Java 版本。
- 试 `mvn dependency:tree -pl demo-service` 解读输出。
