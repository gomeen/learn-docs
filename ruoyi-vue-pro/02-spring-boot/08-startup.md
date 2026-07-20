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
- `Environment`：环境（配置 + Profile，详见 [06-profile](./06-profile.md)）

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

## 3. 关键要点总结

- **启动流程**：main() → SpringApplication.run() → 准备环境 → 创建 Context → 加载 Bean → 刷新 Context → 启动 Tomcat
- **`@SpringBootApplication` = `@Configuration` + `@EnableAutoConfiguration` + `@ComponentScan`**（自动配置详见 [08-auto-config](./09-auto-config.md)）
- **启动失败排查**：
  - 看启动日志（端口、Bean 错误）
  - 加 `--debug` 参数查看自动配置报告
  - 用 `BufferingApplicationStartup` 分析启动耗时
- ruoyi 启动流程：YudaoServerApplication → 扫描 server/module → 加载 starter → 启动 Tomcat → 输出 Banner
- `ApplicationRunner` 用于启动后钩子（Banner、缓存预热、定时任务初始化）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
