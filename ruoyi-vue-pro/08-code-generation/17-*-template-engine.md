# 小验证：Velocity 模板与产物

> 覆盖：
- [Velocity](./12-velocity.md)
- [Java 模板](./13-java-template.md)
- [Vue 模板](./14-vue-template.md)
- [SQL 模板](./15-sql-template.md)
- [自定义模板](./16-custom-template.md)
>
> 预计：45～75 分钟 · 本地练习或改 ruoyi-vue-pro 仓库

## 背景

读懂 .vm 才能定制生成结果。

## 需求

1. 在仓库中定位 Java/Vue/SQL 的 `.vm` 文件。
2. 阅读 Controller/Service 模板，标出变量来自哪些元数据。
3. 小改模板：例如在生成的 Controller 类注释中增加作者占位或统一前缀（本地验证后可还原）。
4. 说明自定义模板的注册方式。

## 提示

- 改模板会影响全局生成，用 git checkout 还原。
- 注意 Velocity 静默失败时的空输出。

## 验收标准

- [ ] 三类模板路径列出
- [ ] 能解释 5 个以上模板变量来源
- [ ] 完成一次可控的模板小改并生成验证
- [ ] 自定义模板扩展方式说明
- [ ] 改动已还原或隔离

## 延伸（选做）

- 新增一个生成“导出 Excel”方法的模板片段。
- 对比 Vue3 与 Vben 模板差异。
