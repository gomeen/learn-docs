# 1.2.7 日志框架：SLF4J + Logback

> 掌握 Java 日志规范 SLF4J 与主流实现 Logback，理解 `@Slf4j` 注解与日志级别配置。

## 🎯 学习目标

完成本文档后，你能够：
- 解释 SLF4J 的"门面模式"思想
- 使用 `@Slf4j` 注解快速生成日志对象
- 配置 Logback（`logback-spring.xml`）的输出格式、级别、滚动策略
- 在 ruoyi 中定位日志输出

## 📚 前置知识

- Lombok 注解（详见 [14-lombok](./17-lombok.md)）
- Spring Boot 基础
- [17-lombok.md](./17-lombok.md)

## 1. 核心概念

### 1.1 日志门面与日志实现

Java 日志生态复杂，存在多种日志库：
- `java.util.logging`（JDK 自带）
- `Log4j 1.x`（Apache）
- `Log4j 2`（Apache，2.x）
- `Logback`（与 SLF4J 同作者，性能更好）
- `Commons-Logging`（Apache）

为避免每个项目被绑死在某个日志库上，行业选择了**门面 + 实现** 模式（门面模式详见 [门面](../../_fundamentals/06-design-patterns/09-facade.md)）：
- **SLF4J**（Simple Logging Facade for Java）：纯粹的日志接口
- **Logback / Log4j2**：具体日志实现

```
应用代码 -> SLF4J API -> [Logback / Log4j2] -> 输出到控制台/文件
```

这样切换日志库无需修改业务代码。

### 1.2 日志级别

| 级别         | 用途           | 输出什么                  |
|------------|--------------|-----------------------|
| `ERROR`    | 错误（必须处理）     | 异常信息                   |
| `WARN`     | 警告（可能出错）     | 潜在问题                  |
| `INFO`     | 一般信息（重要事件）   | 用户登录、订单创建             |
| `DEBUG`    | 调试（开发期开启）    | SQL 语句                  |
| `TRACE`    | 详细跟踪（一般关闭）   | 每个方法的入参出参              |

生产环境一般只输出 `INFO` 以上。

### 1.3 为什么用 `@Slf4j`？

传统写法：

```java
public class UserService {
    private static final Logger log = LoggerFactory.getLogger(UserService.class);
}
```

Lombok 提供 `@Slf4j`：

```java
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class UserService {
    public void save() {
        log.info("保存用户");
    }
}
```

### 1.4 Logback 配置

`src/main/resources/logback-spring.xml`：

```xml
<configuration>
    <appender name="STDOUT" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <pattern>%d{HH:mm:ss} %-5level %logger{36} - %msg%n</pattern>
        </encoder>
    </appender>

    <root level="info">
        <appender-ref ref="STDOUT" />
    </root>
</configuration>
```

## 2. 代码示例

### 2.1 SLF4J 完整写法

```java
// 文件：UserService.java
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Slf4j
@Service
public class UserService {

    public void save(String username) {
        log.info("开始保存用户: {}", username);

        try {
            if (username == null) {
                throw new IllegalArgumentException("username 不能为空");
            }
            log.debug("参数校验通过");
            // ... 业务逻辑
        } catch (IllegalArgumentException e) {
            log.warn("业务校验失败: {}", e.getMessage());
        } catch (Exception e) {
            log.error("系统异常", e);
        }
    }
}
```

### 2.2 占位符 vs 字符串拼接

```java
// 文件：LogStyle.java
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class LogStyle {

    // ❌ 不好：每次都会做字符串拼接，即使日志级别不够
    public void bad() {
        String detail = "user_id=1, username=Tom, score=" + compute();
        log.info("用户登录: " + detail);    // 即使 INFO 被禁用，也做了拼接
    }

    // ✅ 好：SLF4J 占位符只在真正输出时才拼接
    public void good() {
        log.info("用户登录: user_id={}, username={}, score={}", 1, "Tom", compute());
    }

    private int compute() { return 100; }
}
```

### 2.3 异常日志记录

```java
// 文件：ErrorLog.java
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class ErrorLog {

    // ❌ 只记录异常消息（丢失堆栈）
    public void bad() {
        try {
            doSomething();
        } catch (Exception e) {
            log.error("发生错误: " + e.getMessage());   // 没有堆栈
        }
    }

    // ✅ 异常作为最后一个参数，会自动打堆栈
    public void good() {
        try {
            doSomething();
        } catch (Exception e) {
            log.error("发生错误", e);                 // 自动输出完整堆栈
        }
    }

    private void doSomething() { /* ... */ }
}
```

## 3. 关键要点总结

- SLF4J 是 Java 日志**门面**，Logback 是**实现**之一
- 日志级别：`ERROR > WARN > INFO > DEBUG > TRACE`
- Lombok `@Slf4j` 自动注入 `log` 静态字段
- 占位符 `{}` 比字符串拼接性能更好
- 异常作为最后一个参数会被自动打印堆栈

---

**文档版本**：v1.0
**最后更新**：2026-07-13
