# 小验证：构建打包与部署脚本

> 覆盖：
- [Maven 多模块构建](./03-maven-build.md)
- [Spring Boot 打包](./04-spring-boot-jar.md)
- [配置外置](./05-external-config.md)
- [Profile 构建](./06-profile-build.md)
- [ruoyi 部署脚本](./01-ruoyi-deploy.md)
>
> 预计：45～75 分钟 · 本地练习或改 ruoyi-vue-pro 仓库

## 背景

能本地打出可运行 jar，并理解配置外置与脚本部署方式。

## 需求

在 `/Users/xu/code/github/ruoyi-vue-pro`：

1. 使用 Maven 打包 `yudao-server`（可 `-DskipTests`），定位产物 jar。
2. 用 `java -jar` 启动，并通过 `--spring.profiles.active` 或外置 `application-local.yaml` 覆盖一个配置项。
3. 阅读 `script/` 或文档中的部署脚本/Dockerfile 片段，说明生产如何挂载配置与日志目录。
4. 记录多模块构建顺序与 `finalName` 策略。

## 提示

- 打包前确认 JDK 版本与项目要求一致。
- 端口冲突先改配置。
- 不要把含密码的配置提交仓库。

## 验收标准

- [ ] jar 打包成功
- [ ] 外置/Profile 配置覆盖生效
- [ ] 部署脚本或 Docker 关键步骤说明
- [ ] finalName/产物路径记录
- [ ] 启动日志无致命错误（依赖中间件可允许连接失败但要识别）

## 延伸（选做）

- 多阶段 Docker 构建出镜像并 run。
- 比较 thin jar 与 fat jar。
