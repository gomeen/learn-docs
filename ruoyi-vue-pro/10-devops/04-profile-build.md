# 1.4 Profile 多环境构建

> 理解 Spring Profile 机制，掌握 ruoyi 通过 profile 区分 local / dev / prod 环境的最佳实践。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Spring Profile 的工作原理
- 掌握 `spring.profiles.active` 的多种设置方式
- 知道 ruoyi 的 `local` / `dev` / `prod` 三套环境差异
- 能独立设计一套多环境配置方案

## 📚 前置知识

- Spring Profile（详见 [Profile](../02-spring-boot/06-profile.md)）
- 外部化配置（详见 [外部配置](./03-external-config.md)）

## 1. 核心概念

### 1.1 什么是 Profile？

Profile 是 Spring 提供的"环境隔离"机制：
- 不同环境（开发/测试/生产）使用不同配置
- 同一套代码，根据激活的 profile 加载不同的 Bean / 配置

### 1.2 Profile 的三种激活方式

```bash
# 方式 1：配置文件（application.yaml）
spring.profiles.active: local

# 方式 2：命令行参数（最高优先级）
java -jar app.jar --spring.profiles.active=prod

# 方式 3：环境变量
SPRING_PROFILES_ACTIVE=prod java -jar app.jar
```

### 1.3 ruoyi 的环境划分

| Profile | 用途 | 主要差异 |
|---------|------|---------|
| `local` | 本地开发 | 端口 48080，关闭验证码，启用 druid 监控 |
| `dev` | 开发服务器 | 连接开发数据库，开启部分日志 |
| `prod` | 生产环境（建议） | 严格的安全配置、关闭调试 |

## 2. 代码示例

### 2.1 application-{profile}.yaml 命名规范

```
src/main/resources/
├── application.yaml            # 公共配置
├── application-local.yaml      # 本地
├── application-dev.yaml        # 开发服务器
├── application-test.yaml       # 测试环境
└── application-prod.yaml       # 生产环境
```

**说明**：Spring Boot 会根据 `spring.profiles.active` 自动加载对应的 yaml。

### 2.2 在代码中使用 `@Profile`

```java
@Configuration
public class DataSourceConfig {

    @Bean
    @Profile("local")
    public DataSource localDataSource() {
        // 本地 H2 内存数据库
        return new H2DataSource();
    }

    @Bean
    @Profile("prod")
    public DataSource prodDataSource() {
        // 生产 MySQL
        return new MySQLDataSource();
    }
}
```

**说明**：Spring 只创建与当前 profile 匹配的 Bean。

## 3. ruoyi 仓库源码解读

### 3.1 根 application.yaml：默认激活 local

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application.yaml`
**核心代码**（行 1-10）：

```yaml
spring:
  application:
    name: yudao-server

  profiles:
    active: local

  main:
    allow-circular-references: true
```

**解读**：
- 第 5-6 行：`profiles.active: local` — 默认激活 `local` profile
- 这意味着直接 `java -jar yudao-server.jar` 启动时，会加载 `application-local.yaml`
- 切换环境：`java -jar yudao-server.jar --spring.profiles.active=prod`

### 3.2 local 环境：开发友好配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
**核心代码**（行 235-285）：

```yaml
# 芋道配置项，设置当前项目所有自定义的配置
yudao:
  captcha:
    enable: false # 本地环境，暂时关闭图片验证码，方便登录等接口的测试；
  security:
    mock-enable: true
  pay:
    order-notify-url: https://yutou.mynatapp.cc/admin-api/pay/notify/order
  access-log: # 访问日志的配置项
    enable: false
  demo: false # 关闭演示模式

justauth:
  enabled: true
```

**解读**：
- 第 3 行：`captcha.enable: false` — 本地不显示图片验证码，调试更快
- 第 5 行：`security.mock-enable: true` — 本地可以走 mock 登录
- 第 11 行：`access-log.enable: false` — 本地不记录访问日志，减少磁盘 IO
- **设计意图**：local 环境是给开发者用的，要尽量"宽松"

### 3.3 dev 环境：模拟生产配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-dev.yaml`
**核心代码**（行 1-20）：

```yaml
--- #################### 数据库相关配置 ####################
spring:
  autoconfigure:
    # noinspection SpringBootApplicationYaml
    exclude:
      - com.alibaba.druid.spring.boot.autoconfigure.DruidDataSourceAutoConfigure
      - org.springframework.boot.autoconfigure.quartz.QuartzAutoConfiguration
  # 数据源配置项
  datasource:
    dynamic:
      primary: master
      datasource:
        master:
          url: jdbc:mysql://127.0.0.1:3306/ruoyi-vue-pro-jdk8?...
          username: root
          password: 123456
```

**解读**：
- dev 环境的数据库连接地址和 local 类似，但通常指向**开发服务器**的数据库
- 实际上 ruoyi 默认只提供了 `local` 和 `dev` 两套，需要生产环境时**建议自己创建 `application-prod.yaml`**

### 3.4 部署脚本指定 profile

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
**核心代码**（行 12-19）：

```bash
# 环境
PROFILES_ACTIVE=development
# 健康检查 URL
HEALTH_CHECK_URL=http://127.0.0.1:48080/actuator/health/

# heapError 存放路径
HEAP_ERROR_PATH=$BASE_PATH/heapError
# JVM 参数
JAVA_OPS="-Xms512m -Xmx512m -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=$HEAP_ERROR_PATH"
```

**解读**：
- 第 3 行：`PROFILES_ACTIVE=development` — Jenkins 部署时使用 `development` profile
- 第 5 行：部署后通过 `actuator/health` 健康检查
- 注意：`development` 对应 `application-development.yaml`（如果存在），未定义时回退到 `application.yaml`

## 4. 关键要点总结

- `spring.profiles.active` 决定加载哪个 `application-{profile}.yaml`
- ruoyi 默认提供 `local`（开发）和 `dev`（开发服务器）两套
- 建议补充 `prod` 环境用于生产部署
- profile 切换不影响 jar 包，只是切换配置加载源

## 5. 练习题

### 练习 1：基础（必做）

复制 `application-local.yaml` 为 `application-test.yaml`，修改端口为 48081，激活测试：`java -jar yudao-server.jar --spring.profiles.active=test`，访问 48081 验证。

### 练习 2：进阶

在 `application-prod.yaml` 中配置 MySQL 主从 + Redis 密码 + 关闭 actuator 的 `env` 端点，理解生产环境的安全配置。

### 练习 3：挑战（选做）

使用 `@Profile` 注解封装一个 `SmsChannel` Bean：local 环境使用 mock，prod 环境使用阿里云。实现并验证切换 profile 时 Bean 自动切换。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application.yaml`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-dev.yaml`
- `/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
- [Spring Profile 官方文档](https://docs.spring.io/spring-framework/reference/core/beans/environment.html#beans-definition-profiles)

---

**文档版本**：v1.0
**最后更新**：2026-07-13
