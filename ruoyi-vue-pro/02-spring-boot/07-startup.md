# 07 Spring Boot 启动流程

> 理解 Spring Boot 从 `main()` 方法到监听 8080 端口的完整启动流程，能在 ruoyi-vue-pro 中快速定位启动失败问题。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `SpringApplication.run()` 内部的 7 个核心步骤
- 掌握 ApplicationContext 生命周期：加载 → 刷新 → 启动 → 关闭
- 能在启动失败时看懂堆栈信息（`Unable to start web server` 等）
- 能使用 `spring-boot-starter-actuator` 的 `/actuator/startup` 端点分析启动时间

## 📚 前置知识

- 01-ioc.md
- 02-bean-lifecycle.md

## 1. 核心概念

### 1.1 Spring Boot 启动流程

```
1. 准备环境（Environment）
   ↓
2. 打印 Banner
   ↓
3. 创建 ApplicationContext
   ↓
4. 加载 Bean 定义（@ComponentScan、@Configuration）
   ↓
5. 刷新上下文（refresh() —— 核心）
   ↓
6. 执行 Runner（ApplicationRunner、CommandLineRunner）
   ↓
7. 启动 Web 服务器（Tomcat）
```

### 1.2 关键类

- `SpringApplication`：启动器
- `ApplicationContext`：IoC 容器接口
- `BeanFactory`：Bean 工厂（最底层接口）
- `Environment`：环境（配置 + Profile）

### 1.3 启动失败常见原因

| 异常 | 原因 |
|------|------|
| `Port already in use` | 端口被占用 |
| `No qualifying bean of type` | 缺少 Bean |
| `BeanDefinitionStoreException` | 配置错误（@ComponentScan 路径错） |
| `ClassNotFoundException` | 缺少依赖 |
| `Failed to bind on [0.0.0.0:port]` | 端口权限不足（1024 以下） |

## 2. 代码示例

### 2.1 启动类 + 自定义 Banner

```java
// 文件：MyApplication.java
@SpringBootApplication
public class MyApplication {
    public static void main(String[] args) {
        SpringApplication app = new SpringApplication(MyApplication.class);
        // 设置 Banner 模式（OFF 关闭）
        app.setBannerMode(Banner.Mode.OFF);
        // 设置环境（默认从 application.yml 加载）
        app.setLogStartupInfo(true);
        // 启动
        app.run(args);
    }
}
```

### 2.2 自定义 Banner

```text
// 文件：src/main/resources/banner.txt
  __  __   ____    ____
 |  \/  | / __ \  / __ \
 | \  / || |  | || |  | |
 | |\/| || |  | || |  | |
 | |  | || |__| || |__| |
 |_|  |_| \____/  \____/
 :: yudao-server :: ${spring-boot.formatted-version}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 YudaoServerApplication 启动入口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/java/cn/iocoder/yudao/server/YudaoServerApplication.java`
**核心代码**（行 1-34）：

```java
package cn.iocoder.yudao.server;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 项目的启动类
 *
 * 如果你碰到启动的问题，请认真阅读 https://doc.iocoder.cn/quick-start/ 文章
 *
 * @author 芋道源码
 */
@SuppressWarnings("SpringComponentScan") // 忽略 IDEA 无法识别 ${yudao.info.base-package}
@SpringBootApplication(scanBasePackages = {"${yudao.info.base-package}.server", "${yudao.info.base-package}.module"})
public class YudaoServerApplication {

    public static void main(String[] args) {
        SpringApplication.run(YudaoServerApplication.class, args);
//        new SpringApplicationBuilder(YudaoServerApplication.class)
//                .applicationStartup(new BufferingApplicationStartup(20480))
//                .run(args);
    }
}
```

**解读**：
- 第 16 行：`@SpringBootApplication` 是 `@Configuration` + `@EnableAutoConfiguration` + `@ComponentScan` 的组合
- 第 16 行：`scanBasePackages` 指定扫描 `cn.iocoder.yudao.server` 和 `cn.iocoder.yudao.module` 两个根包
- 第 24 行：`SpringApplication.run()` 一行完成所有启动流程
- 第 25-27 行：注释掉的 `BufferingApplicationStartup(20480)` 用于启动时间分析（20KB 缓冲区），可在排查慢启动时启用

### 3.2 BannerApplicationRunner 在启动后执行

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
- 第 5 行：`@Order(0)` 让 Banner 第一个输出（在其他 Runner 之前）
- 第 8-10 行：通过 `@Value` 注入应用名
- 第 14-23 行：使用 Java 15+ 的文本块（`"""..."""`）输出美化的启动 Banner
- **启动阶段**：所有 Bean 初始化完成 → ContextRefreshedEvent → ApplicationRunner#run

## 4. 关键要点总结

- **启动流程**：main() → SpringApplication.run() → 准备环境 → 创建 Context → 加载 Bean → 刷新 Context → 启动 Tomcat
- **`@SpringBootApplication` = `@Configuration` + `@EnableAutoConfiguration` + `@ComponentScan`**
- **启动失败排查**：
  - 看启动日志（端口、Bean 错误）
  - 加 `--debug` 参数查看自动配置报告
  - 用 `BufferingApplicationStartup` 分析启动耗时
- ruoyi 启动流程：YudaoServerApplication → 扫描 server/module → 加载 starter → 启动 Tomcat → 输出 Banner
- `ApplicationRunner` 用于启动后钩子（Banner、缓存预热、定时任务初始化）

## 5. 练习题

### 练习 1：基础（必做）

在 ruoyi-vue-pro 启动类中加一个 `CommandLineRunner`，在项目启动后输出"系统就绪"。

### 练习 2：进阶

启动 ruoyi-vue-pro 时加 `--debug` 参数，观察控制台输出的 `CONDITIONS EVALUATION REPORT`，列出 3 个 `negative match` 的自动配置类。

### 练习 3：挑战（选做）

启用 `BufferingApplicationStartup(20480)`，访问 `actuator/startup` 端点，找出启动最慢的 Bean 并分析原因。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/java/cn/iocoder/yudao/server/YudaoServerApplication.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/banner/core/BannerApplicationRunner.java`
- Spring Boot 启动流程：https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.spring-application
- 芋道 Spring Boot 启动：https://doc.iocoder.cn/spring-boot-starter/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
