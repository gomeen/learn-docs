# 1.3 配置文件外置

> 理解 Spring Boot 配置文件的加载顺序，掌握 ruoyi 的多环境配置与外部化配置方案。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Spring Boot 配置文件优先级
- 掌握 `application.yaml` 与 profile-specific 配置文件的关系
- 知道 ruoyi 如何通过环境变量覆盖配置
- 能独立配置生产环境的数据库连接

## 📚 前置知识

- Spring Boot 基础（详见 [配置](../02-spring-boot/11-config.md)）
- YAML 语法
- Maven 构建（详见 [Maven 多模块](./03-maven-build.md)）
- Profile（详见 [Profile](../02-spring-boot/06-profile.md)、[Profile 构建](./06-profile-build.md)）

## 1. 核心概念

### 1.1 Spring Boot 配置加载顺序

Spring Boot 按以下**优先级从高到低**加载配置：

1. **命令行参数**：`--spring.datasource.url=...`
2. **环境变量**：`SPRING_DATASOURCE_URL=...`
3. **外部 `application-{profile}.yaml`**：放在 jar 包外
4. **jar 包内 `application-{profile}.yaml`**：`classpath:config/`
5. **jar 包内 `application.yaml`**：默认配置

**核心原则**：高优先级覆盖低优先级。

### 1.2 ruoyi 的三套环境

```
yudao-server/src/main/resources/
├── application.yaml       # 公共配置（所有环境共享）
├── application-local.yaml  # 本地开发环境（dev）
└── application-dev.yaml   # 开发服务器环境（dev）
```

通过 `spring.profiles.active=local` 激活对应环境。

### 1.3 12-Factor App：配置与代码分离

生产环境的数据库密码、Redis 地址、第三方 API Key **不应该**硬编码在 yaml 中。ruoyi 的做法：

- **开发环境**：直接写在 yaml（方便）
- **生产环境**：通过环境变量注入（`--spring.datasource.dynamic.datasource.master.url=${...}`）
- **Docker**：通过 `docker-compose.yml` 的 `environment` 注入

## 2. 代码示例

### 2.1 占位符引用环境变量

```yaml
# 文件：application-local.yaml
spring:
  datasource:
    dynamic:
      datasource:
        master:
          url: jdbc:mysql://${MYSQL_HOST:127.0.0.1}:${MYSQL_PORT:3306}/${DB_NAME:ruoyi-vue-pro}
          username: ${MYSQL_USER:root}
          password: ${MYSQL_PWD:123456}
```

**说明**：
- `${MYSQL_HOST:127.0.0.1}`：读取环境变量 `MYSQL_HOST`，未设置则用默认值 `127.0.0.1`
- 启动时可通过 `MYSQL_HOST=192.168.1.10 java -jar app.jar` 覆盖

### 2.2 命令行参数覆盖

```bash
java -jar yudao-server.jar \
  --spring.profiles.active=prod \
  --spring.datasource.dynamic.datasource.master.url=jdbc:mysql://prod-db:3306/ruoyi \
  --spring.datasource.dynamic.datasource.master.password=prod-secret
```

**说明**：命令行参数优先级最高，可临时调试。

## 3. 关键要点总结

- ruoyi 用 `application.yaml`（公共） + `application-{profile}.yaml`（环境）分层管理
- 配置优先级：命令行 > 环境变量 > 外部 yaml > 内部 yaml
- Docker 部署时通过 `docker-compose.yml` 的 `environment` 注入生产配置
- `${VAR:-default}` 语法同时支持 shell 和 Spring 占位符

---

**文档版本**：v1.0
**最后更新**：2026-07-13
