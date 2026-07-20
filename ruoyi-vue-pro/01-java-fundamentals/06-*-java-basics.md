# 小验证：Java 语言核心

> 覆盖：
- [Java 语法基础](./01-java-syntax.md)
- [面向对象](./02-oop.md)
- [泛型](./03-generics.md)
- [注解](./04-annotation.md)
- [反射](./05-reflection.md)
>
> 预计：30～45 分钟 · 本地练习

## 背景

用一个本地小模块把 Java 语言核心串起来：数据建模、自定义注解与反射校验。不依赖 Spring。

## 需求

新建本地 Maven/Gradle 小项目 `learn-java-core`（或单测类），完成：

1. 定义 `User` 类：`id`、`name`、`email`，用构造/Builder 均可；至少一个接口（如 `Identifiable`）与一个抽象基类或组合关系。
2. 自定义运行时注解 `@NotBlank`（可仅作标记），写一个 `SimpleValidator` 用反射检查 `String` 字段非空，失败抛出自定义 `ValidationException`（Checked 或 Unchecked 自选，说明理由）。
3. 给校验器加泛型方法 `validate(T target)`，并对 `User` 与另一个简单类（如 `Order`）复用。
4. 用 main 或 JUnit 5 覆盖：合法对象通过、空 name/email 被捕获。

## 提示

- 注解保留策略用 `RUNTIME`，否则反射读不到。
- 异常类型选择写 2～3 行理由即可。
- 单元测试可用 `assertThrows`。

## 验收标准

- [ ] `User` 与校验逻辑有可运行的 main 或单测
- [ ] 空 name/email 能被校验捕获
- [ ] 泛型校验方法至少用于 2 个类型
- [ ] 自定义注解可被反射读取
- [ ] 对 Checked vs Unchecked 选择有简短说明

## 延伸（选做）

- 给 `User` 加泛型仓库接口 `Repository<T, ID>` 与内存实现。
- 支持注解参数 `message`，异常信息带上字段名。
