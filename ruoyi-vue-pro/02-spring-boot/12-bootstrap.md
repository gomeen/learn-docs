# 12 Spring Boot 启动加载器

> 理解 Spring Boot 启动加载机制：`ApplicationContextInitializer`、`ApplicationRunner`、`CommandLineRunner`、监听 `ApplicationReadyEvent`。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Spring Boot 启动过程中的扩展点
- 掌握 `ApplicationContextInitializer`（上下文初始化前）
- 掌握 `ApplicationRunner` / `CommandLineRunner`（启动后）
- 掌握 `ApplicationListener<ApplicationReadyEvent>`（就绪后）
- 能在 ruoyi-vue-pro 中识别和使用这些扩展点

## 📚 前置知识

- 01-ioc.md
- 07-startup.md

## 1. 核心概念

### 1.1 启动扩展点的 5 个位置

```
1. SpringApplicationRunListener          ← 启动前（监听 run 生命周期）
2. ApplicationContextInitializer         ← 上下文初始化（refresh 前）
3. BeanFactoryPostProcessor             ← Bean 定义加载后，实例化前
4. BeanPostProcessor                    ← Bean 实例化前后
5. ApplicationRunner / CommandLineRunner ← 启动完成
```

### 1.2 5 个 Spring Boot 事件

| 事件 | 触发时机 |
|------|---------|
| `ApplicationStartingEvent` | 启动最开始（环境未准备） |
| `ApplicationEnvironmentPreparedEvent` | 环境准备完成 |
| `ApplicationContextInitializedEvent` | 上下文创建完成 |
| `ApplicationPreparedEvent` | Bean 定义加载完成 |
| `ApplicationStartedEvent` | 上下文刷新完成 |
| `ApplicationReadyEvent` | **应用就绪**（可接收请求） |
| `ApplicationFailedEvent` | 启动失败 |

### 1.3 `ApplicationRunner` vs `CommandLineRunner`

| 特性 | `ApplicationRunner` | `CommandLineRunner` |
|------|--------------------|--------------------|
| 参数 | `ApplicationArguments`（已解析） | `String[]`（原始） |
| 顺序 | `@Order(n)` | `@Order(n)` |
| 触发 | 上下文刷新后 | 上下文刷新后 |

## 2. 代码示例

### 2.1 ApplicationContextInitializer

```java
// 文件：MyContextInitializer.java
@Order(Ordered.HIGHEST_PRECEDENCE)
public class MyContextInitializer implements ApplicationContextInitializer<ConfigurableApplicationContext> {
    @Override
    public void initialize(ConfigurableApplicationContext context) {
        // 在 Bean 实例化前设置属性
        context.getEnvironment().setActiveProfiles("dev");
    }
}
```

注册方式（在 `META-INF/spring.factories`）：

```properties
org.springframework.context.ApplicationContextInitializer=\
cn.iocoder.yudao.framework.config.MyContextInitializer
```

### 2.2 ApplicationRunner

```java
// 文件：CacheWarmupRunner.java
@Component
@Order(1)  // 在 BannerRunner 之后执行
public class CacheWarmupRunner implements ApplicationRunner {
    @Override
    public void run(ApplicationArguments args) throws Exception {
        log.info("[CacheWarmupRunner] 预热用户缓存...");
        userService.preloadCache();
    }
}
```

### 2.3 CommandLineRunner

```java
@Component
@Order(2)
public class StartupRunner implements CommandLineRunner {
    @Override
    public void run(String... args) throws Exception {
        log.info("启动参数: {}", Arrays.toString(args));
    }
}
```

### 2.4 监听 ApplicationReadyEvent

```java
@Component
public class StartupListener {
    @EventListener(ApplicationReadyEvent.class)
    public void onReady() {
        log.info("应用已就绪，监听端口: 8080");
    }
}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 BannerApplicationRunner 启动后钩子

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/banner/core/BannerApplicationRunner.java`
**核心代码**（行 22-35）：

```java
@Slf4j
@Order(0)  // 越小越靠前
public class BannerApplicationRunner implements ApplicationRunner {

    private final String applicationName;

    public BannerApplicationRunner(@Value("${spring.application.name}") String applicationName) {
        this.applicationName = applicationName;
    }

    @Override
    public void run(ApplicationArguments args) throws Exception {
        log.info("""
                
                ----------------------------------------------------------
                \t项目启动成功！
                \t项目名称：{}
                \t启动时间：{}
                ----------------------------------------------------------
                """,
                applicationName, LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
    }
}
```

**解读**：
- 第 5 行：`@Order(0)` 让 Banner 第一个输出（其他 Runner 在它之后）
- 第 8-10 行：构造器注入 `applicationName`（来自 `application.yml` 的 `spring.application.name`）
- 第 14-23 行：使用 Java 17 文本块（`"""..."""`）输出格式化 Banner
- **执行时机**：所有 Bean 初始化完成 → `ContextRefreshedEvent` → 多个 `ApplicationRunner.run()` 按 `@Order` 执行
- **设计意图**：启动后立即输出 Banner，让运维一眼看到应用名（多实例部署时区分服务）

### 3.2 全局异常处理器的依赖注入（间接使用扩展点）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
**核心代码**（行 83-92）：

```java
@Bean
@SuppressWarnings("SpringJavaInjectionPointsAutowiringInspection")
public GlobalExceptionHandler globalExceptionHandler(ApiErrorLogCommonApi apiErrorLogApi) {
    return new GlobalExceptionHandler(applicationName, apiErrorLogApi);
}

@Bean
public GlobalResponseBodyHandler globalResponseBodyHandler() {
    return new GlobalResponseBodyHandler();
}
```

**解读**：
- 第 1-4 行：`globalExceptionHandler` 在 `YudaoWebAutoConfiguration` 中显式构造
- **为什么不在 `GlobalExceptionHandler` 加 `@Component`？** 因为 `applicationName` 需要从启动类所在模块注入，避免循环依赖
- **设计模式**：通过 `@Bean` 手动装配，把扩展点（`@Value` 注入）和 Bean 创建逻辑集中

### 3.3 Cache 自动配置（Redis 缓存启动加载）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
**核心代码**（行 27-40）：

```java
@AutoConfiguration
@EnableConfigurationProperties({CacheProperties.class, YudaoCacheProperties.class})
@EnableCaching
public class YudaoCacheAutoConfiguration {

    /**
     * RedisCacheConfiguration Bean
     * <p>
     * 参考 org.springframework.boot.autoconfigure.cache.RedisCacheConfiguration 的 createConfiguration 方法
     */
    @Bean
    @Primary
    public RedisCacheConfiguration redisCacheConfiguration(CacheProperties cacheProperties) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig();
```

**解读**：
- 第 3 行：`@EnableCaching` 是 Spring 缓存的"启动加载器"——开启 `@Cacheable` 注解支持
- 第 4 行：`@AutoConfiguration` 是 Spring Boot 3.x 推荐方式
- 第 10 行：`@Primary` 让多个 `RedisCacheConfiguration` Bean 时优先选这个
- **执行时机**：上下文刷新阶段 → `EnableCaching` 处理器扫描 `@Cacheable` 注解 → 注册缓存切面

## 4. 关键要点总结

- **5 个启动扩展点**：`ApplicationContextInitializer` → `BeanFactoryPostProcessor` → `BeanPostProcessor` → `Runner` → 事件监听
- **Runner 是最常用的扩展点**（启动后执行初始化逻辑）
- **`@Order` 控制 Runner 顺序**（数字越小越先）
- **ruoyi 中通过 `BannerApplicationRunner` 输出启动 Banner**
- **ruoyi 中通过 `@EnableCaching` 启用缓存注解**
- **ruoyi 中通过 `@AutoConfiguration` + `@Bean` 集中管理 Bean 注册**

## 5. 练习题

### 练习 1：基础（必做）

在 ruoyi-vue-pro 中实现一个 `StartupLogger` 实现 `ApplicationRunner`，在启动后输出"系统已就绪"日志。

### 练习 2：进阶

解释 `ApplicationRunner` 和 `CommandLineRunner` 的差异，并实现一个 `CommandLineRunner` 接收启动参数 `--clean-cache` 来清空 Redis 缓存。

### 练习 3：挑战（选做）

实现一个 `ApplicationContextInitializer`，在开发环境自动注入 Mock 用户到 Spring 上下文（用于单元测试），并通过 `META-INF/spring.factories` 注册。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/banner/core/BannerApplicationRunner.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
- Spring Boot 启动流程：https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.spring-application.application-availability
- 芋道 Spring Boot 启动：https://doc.iocoder.cn/spring-boot-starter/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
