# 1.5 自研 Starter 实战：完整案例

> 通过完整案例掌握自研 Starter 的开发流程，能独立发布 Starter 到 Maven 私服。

## 🎯 学习目标

完成本文档后，你将能够：
- 独立开发一个完整 Starter（含 autoconfigure 模块）
- 编写 `AutoConfiguration.imports`、`spring.factories`
- 使用 `@ConfigurationProperties` 接收配置
- 编写单元测试验证 Starter
- 能发布 Starter 到公司 Maven 私服

## 📚 前置知识

- [01-starter-mechanism.md](./01-starter-mechanism.md)
- [02-auto-configuration.md](./02-auto-configuration.md)
- [03-spi.md](./03-spi.md)
- [04-conditional.md](./04-conditional.md)
- Maven 多模块项目

## 1. 核心概念

### 1.1 Starter 的开发流程

```
1. 需求分析 → 定义接口
2. 创建 autoconfigure 模块 → 写 @AutoConfiguration
3. 创建 starter 模块 → 引入 autoconfigure + 依赖
4. 编写 AutoConfiguration.imports
5. 编写单元测试
6. 发布到 Maven 仓库
```

### 1.2 ruoyi 的典型 Starter 结构

每个 ruoyi Starter 都有相似的目录结构：

```
yudao-spring-boot-starter-xxx/
├── pom.xml                                  # 依赖 spring-boot-starter
└── src/main/
    ├── java/cn/iocoder/yudao/framework/xxx/
    │   ├── config/YudaoXxxAutoConfiguration.java
    │   ├── core/                             # 核心类
    │   └── package-info.java
    └── resources/
        └── META-INF/spring/
            └── org.springframework.boot.autoconfigure.AutoConfiguration.imports
```

## 2. 代码示例

### 2.1 autoconfigure 模块的 pom

```xml
<!-- 文件：my-starter-spring-boot-autoconfigure/pom.xml -->
<project>
    <groupId>com.example</groupId>
    <artifactId>my-starter-spring-boot-autoconfigure</artifactId>
    <version>1.0.0</version>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-configuration-processor</artifactId>
            <optional>true</optional>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>
```

### 2.2 starter 模块的 pom

```xml
<!-- 文件：my-starter-spring-boot-starter/pom.xml -->
<project>
    <groupId>com.example</groupId>
    <artifactId>my-starter-spring-boot-starter</artifactId>
    <version>1.0.0</version>

    <dependencies>
        <dependency>
            <groupId>com.example</groupId>
            <artifactId>my-starter-spring-boot-autoconfigure</artifactId>
        </dependency>
    </dependencies>
</project>
```

### 2.3 Properties 类

```java
// 文件：MyProperties.java
package com.example.starter;

import org.springframework.boot.context.properties.ConfigurationProperties;

@Data
@ConfigurationProperties(prefix = "mystarter")
public class MyProperties {
    /** 是否启用 */
    private Boolean enable = true;
    /** 名称 */
    private String name = "default";
    /** 超时时间（秒） */
    private Integer timeout = 30;
}
```

### 2.4 Service 类

```java
// 文件：MyService.java
package com.example.starter;

public class MyService {
    private final MyProperties properties;

    public MyService(MyProperties properties) {
        this.properties = properties;
    }

    public String greet() {
        return "Hello, " + properties.getName();
    }
}
```

### 2.5 AutoConfiguration 类

```java
// 文件：MyAutoConfiguration.java
package com.example.starter;

import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@AutoConfiguration
@EnableConfigurationProperties(MyProperties.class)
public class MyAutoConfiguration {

    @Bean
    public MyService myService(MyProperties properties) {
        return new MyService(properties);
    }
}
```

### 2.6 单元测试

```java
// 文件：MyAutoConfigurationTest.java
package com.example.starter;

import org.junit.jupiter.api.Test;
import org.springframework.boot.autoconfigure.AutoConfigurations;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;

import static org.assertj.core.api.Assertions.assertThat;

class MyAutoConfigurationTest {

    private final ApplicationContextRunner runner = new ApplicationContextRunner()
            .withConfiguration(AutoConfigurations.of(MyAutoConfiguration.class));

    @Test
    void testMyServiceExists() {
        runner.run(context -> {
            assertThat(context).hasSingleBean(MyService.class);
            assertThat(context.getBean(MyService.class).greet()).isEqualTo("Hello, default");
        });
    }
}
```

## 3. 关键要点总结

- **Starter 开发的最小集**：AutoConfiguration 类 + Properties 类 + `AutoConfiguration.imports` 文件
- **maven 依赖规范**：autoconfigure 依赖 `spring-boot-starter`，starter 依赖 autoconfigure
- **`spring-boot-configuration-processor`** 提供 `application.yml` 的自动补全
- **测试方式**：用 `ApplicationContextRunner` 加载上下文，断言 Bean
- **发布**用 `mvn deploy` 到 Nexus 等私服

---

**文档版本**：v1.0
**最后更新**：2026-07-13
