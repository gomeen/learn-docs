# 06 Spring Profile 多环境配置

> 掌握 Spring Profile 的使用，能在 ruoyi-vue-pro 中正确切换 dev / test / prod 环境。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Profile 的作用：同一套代码在不同环境使用不同配置
- 掌握 `@Profile`、`spring.profiles.active`、多配置文件（`application-{profile}.yml`）的使用
- 能在 ruoyi-vue-pro 中根据环境启用/禁用 Bean（如 DemoFilter）
- 了解 Nacos 配置中心如何与 Profile 结合

## 📚 前置知识

- Spring 基础配置
- Maven 多模块项目

## 1. 核心概念

### 1.1 什么是 Profile？

Profile 是 Spring 提供的**环境隔离机制**，让你能：
- `application-dev.yml`：开发环境（本地数据库、调试日志）
- `application-test.yml`：测试环境（测试数据库）
- `application-prod.yml`：生产环境（生产数据库、关闭调试）

激活方式：
1. `application.yml` 中：`spring.profiles.active: dev`
2. 启动参数：`--spring.profiles.active=prod`
3. 环境变量：`SPRING_PROFILES_ACTIVE=prod`
4. JVM 系统属性：`-Dspring.profiles.active=prod`

### 1.2 Profile 与 Bean 条件注册

```java
@Component
@Profile("dev")  // 只在 dev 环境注册
public class DevDataInitializer { ... }

@Component
@Profile("!prod")  // 非生产环境注册
public class DebugFilter { ... }
```

### 1.3 配置文件拆分

```yaml
# application.yml —— 公共配置
spring:
  application:
    name: yudao-server
  profiles:
    active: dev  # 默认激活 dev

---
# application-dev.yml —— 开发环境
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/yudao_dev

---
# application-prod.yml —— 生产环境
spring:
  datasource:
    url: jdbc:mysql://prod-db:3306/yudao_prod
```

## 2. 代码示例

### 2.1 启动类激活 Profile

```java
// 文件：YudaoServerApplication.java
@SpringBootApplication
public class YudaoServerApplication {
    public static void main(String[] args) {
        // 方式 1：环境变量激活
        SpringApplication.run(YudaoServerApplication.class, args);

        // 方式 2：代码硬编码（不推荐）
        // System.setProperty("spring.profiles.active", "dev");
    }
}
```

### 2.2 条件注册 DemoFilter

```java
// 文件：YudaoWebAutoConfiguration.java
@Bean
@ConditionalOnProperty(value = "yudao.demo", havingValue = "true")
public FilterRegistrationBean<DemoFilter> demoFilter() {
    return createFilterBean(new DemoFilter(), WebFilterOrderEnum.DEMO_FILTER);
}
```

**说明**：
- `@ConditionalOnProperty` 比 `@Profile` 更细粒度（基于配置项值）
- `yudao.demo=true` 在 dev 环境配置，prod 不配置则不启用演示模式

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 启动类的多包扫描

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/java/cn/iocoder/yudao/server/YudaoServerApplication.java`
**核心代码**（行 14-24）：

```java
@SuppressWarnings("SpringComponentScan") // 忽略 IDEA 无法识别 ${yudao.info.base-package}
@SpringBootApplication(scanBasePackages = {"${yudao.info.base-package}.server", "${yudao.info.base-package}.module"})
public class YudaoServerApplication {

    public static void main(String[] args) {
        // 如果你碰到启动的问题，请认真阅读 https://doc.iocoder.cn/quick-start/ 文章
        SpringApplication.run(YudaoServerApplication.class, args);
    }
}
```

**解读**：
- 第 3 行：`scanBasePackages` 用占位符 `${yudao.info.base-package}` 动态指定扫描路径
- 占位符在 `pom.xml` 的 `<properties>` 中定义（如 `yudao.info.base-package=cn.iocoder.yudao`）
- **Profile 关联**：在 dev/prod 环境下可以覆盖这个属性（如 `cn.iocoder.yudao.cn` vs `cn.iocoder.yudao.com`），实现"同一份代码部署到不同租户"

### 3.2 Web 配置中的条件 Bean

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
**核心代码**（行 132-136）：

```java
@Bean
@ConditionalOnProperty(value = "yudao.demo", havingValue = "true")
public FilterRegistrationBean<DemoFilter> demoFilter() {
    return createFilterBean(new DemoFilter(), WebFilterOrderEnum.DEMO_FILTER);
}
```

**解读**：
- 第 2 行：`@ConditionalOnProperty` 让 `DemoFilter` 只在 `yudao.demo=true` 时注册
- **典型应用**：
  - `application-dev.yml`：`yudao.demo: true`（演示模式，所有写操作返回假成功）
  - `application-prod.yml`：不配置此属性（生产环境严格校验）
- **设计意图**：防止开发环境的"演示模式"误带到生产环境，避免数据被误删

### 3.3 Profile 隔离的目录

ruoyi-vue-pro 在 `yudao-server/src/main/resources/` 下提供：
- `application.yml`（公共）
- `application-dev.yaml`（开发）
- `application-prod.yaml`（生产）
- `application-local.yaml`（本地）

**激活方式**：在 IDEA 的 `Run/Debug Configurations` 中设置 `Active profiles = dev`。

## 4. 关键要点总结

- **Profile = 环境隔离**，dev / test / prod 各自一套配置
- **3 种激活方式**：配置文件、启动参数、环境变量
- **细粒度控制用 `@ConditionalOnProperty`**（按配置项值判断）
- **粗粒度控制用 `@Profile`**（按环境名判断）
- ruoyi-vue-pro 用 `application-{profile}.yml` 分离环境配置
- ruoyi 的 `DemoFilter` 是 `@ConditionalOnProperty` 的典型应用

## 5. 练习题

### 练习 1：基础（必做）

创建 `application-dev.yml` 和 `application-prod.yml`，分别配置不同的 MySQL 数据源 URL。激活 dev 后启动项目，验证生效。

### 练习 2：进阶

在 `YudaoServerApplication` 中增加 `@Profile("dev")` 标注的 `CommandLineRunner`，在 dev 环境启动时输出"开发环境已激活"。

### 练习 3：挑战（选做）

在 ruoyi-vue-pro 中搜索 `application-{profile}.yml`，列出所有环境的配置文件，并分析每个环境的特殊配置（如日志级别、监控端点）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/java/cn/iocoder/yudao/server/YudaoServerApplication.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
- Spring Profile 官方文档：https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.profiles
- 芋道多环境配置：https://doc.iocoder.cn/spring-boot-profile/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
