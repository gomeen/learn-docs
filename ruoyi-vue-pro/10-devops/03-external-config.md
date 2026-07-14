# 1.3 配置文件外置

> 理解 Spring Boot 配置文件的加载顺序，掌握 ruoyi 的多环境配置与外部化配置方案。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Spring Boot 配置文件优先级
- 掌握 `application.yaml` 与 profile-specific 配置文件的关系
- 知道 ruoyi 如何通过环境变量覆盖配置
- 能独立配置生产环境的数据库连接

## 📚 前置知识

- Spring Boot 基础（`@SpringBootApplication`）
- YAML 语法
- `01-maven-build.md`

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

## 3. ruoyi 仓库源码解读

### 3.1 根 application.yaml：公共配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application.yaml`
**核心代码**（行 1-10）：

```yaml
spring:
  application:
    name: yudao-server

  profiles:
    active: local   # 默认激活 local 环境

  main:
    allow-circular-references: true # 允许循环依赖，因为项目是三层架构，无法避免这个情况。
```

**解读**：
- 第 5 行：`profiles.active: local` — 决定加载 `application-local.yaml`
- 第 9 行：允许循环依赖（项目采用三层架构，存在 Controller → Service → Service 的循环）
- **关键点**：公共配置只放"所有环境都一样的"（cache、jackson、文档配置）

### 3.2 application-local.yaml：本地开发配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
**核心代码**（行 1-15）：

```yaml
server:
  port: 48080

--- #################### 数据库相关配置 ####################
spring:
  autoconfigure:
    exclude:
      - com.alibaba.druid.spring.boot.autoconfigure.DruidDataSourceAutoConfigure
      - org.springframework.boot.autoconfigure.quartz.QuartzAutoConfiguration
  # 数据源配置项
  datasource:
    druid:
      web-stat-filter:
        enabled: true
      stat-view-servlet:
        enabled: true
```

**解读**：
- 第 1-2 行：服务器端口 48080
- 第 8-9 行：排除 Druid / Quartz 自动配置（ruoyi 用 dynamic-datasource 替代）
- 第 14-19 行：启用 Druid 监控过滤器（访问 `/druid/*` 查看 SQL 监控）

### 3.3 docker-compose 注入环境变量

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`
**核心代码**（行 36-56）：

```yaml
  server:
    container_name: yudao-server
    build:
      context: ./yudao-server/
    image: yudao-server
    restart: unless-stopped
    ports:
      - "48080:48080"
    environment:
      SPRING_PROFILES_ACTIVE: local
      JAVA_OPTS: ${JAVA_OPTS:-...}
      ARGS:
        --spring.datasource.dynamic.datasource.master.url=${MASTER_DATASOURCE_URL:-jdbc:mysql://yudao-mysql:3306/ruoyi-vue-pro?...}
        --spring.datasource.dynamic.datasource.master.username=${MASTER_DATASOURCE_USERNAME:-root}
        --spring.datasource.dynamic.datasource.master.password=${MASTER_DATASOURCE_PASSWORD:-123456}
        --spring.redis.host=${REDIS_HOST:-yudao-redis}
```

**解读**：
- 第 41 行：`SPRING_PROFILES_ACTIVE: local` — 激活 local profile
- 第 47-53 行：`ARGS` 数组形式的命令行参数，会被追加到 `java -jar` 命令后
- `${VAR:-default}`：docker-compose 语法，VAR 未设置则用 default
- **设计意图**：通过 `docker.env` 文件提供变量，`docker-compose.yml` 引用变量，实现配置外置

## 4. 关键要点总结

- ruoyi 用 `application.yaml`（公共） + `application-{profile}.yaml`（环境）分层管理
- 配置优先级：命令行 > 环境变量 > 外部 yaml > 内部 yaml
- Docker 部署时通过 `docker-compose.yml` 的 `environment` 注入生产配置
- `${VAR:-default}` 语法同时支持 shell 和 Spring 占位符

## 5. 练习题

### 练习 1：基础（必做）

启动 yudao-server 时通过命令行覆盖端口：`java -jar yudao-server.jar --server.port=9999`，验证端口是否变化。

### 练习 2：进阶

修改 `docker-compose.yml` 注入自定义数据库地址，重启 yudao-server 容器，验证数据库连接是否切换。

### 练习 3：挑战（选做）

封装一个 `application-prod.yaml`（生产环境专用），通过 `SPRING_PROFILES_ACTIVE=prod` 激活，包含 MySQL 主从 + Redis 集群 + 严格的 Actuator 端点控制。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application.yaml`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
- `/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`
- [Spring Boot 外部化配置文档](https://docs.spring.io/spring-boot/docs/2.7.x/reference/html/features.html#features.external-config)
- [12-Factor App 配置原则](https://12factor.net/zh_cn/config)

---

**文档版本**：v1.0
**最后更新**：2026-07-13
