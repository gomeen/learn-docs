# 10 配置文件：application.yml 多环境

> 掌握 Spring Boot 配置文件的语法、加载顺序、多环境分离，能正确管理 ruoyi-vue-pro 的配置。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `application.yml` 的语法（层级、数组、占位符）
- 掌握配置加载顺序：命令行 > 环境变量 > application-{profile}.yml > application.yml
- 掌握 `@ConfigurationProperties` 和 `@Value` 的差异
- 能在 ruoyi-vue-pro 中定位配置问题

## 📚 前置知识

- 06-profile.md
- 10-custom-starter.md

## 1. 核心概念

### 1.1 application.yml 语法

```yaml
# 字符串
yudao:
  name: "yudao-server"
  # 多行字符串
  description: |
    line 1
    line 2

# 数组
yudao:
  regions:
    - beijing
    - shanghai
    - shenzhen

# Map
yudao:
  databases:
    master: jdbc:mysql://localhost:3306/master
    slave: jdbc:mysql://localhost:3306/slave

# 占位符
yudao:
  name: "yudao-server"
  full-name: "${yudao.name}-v1"  # → yudao-server-v1

# 默认值
yudao:
  timeout: "${TIMEOUT:3000}"  # 优先用环境变量 TIMEOUT，默认 3000
```

### 1.2 加载顺序（优先级从高到低）

1. 命令行参数：`--server.port=8081`
2. `SPRING_APPLICATION_JSON` 内嵌 JSON
3. JNDI 属性
4. ServletContext 初始化参数
5. ServletConfig 初始化参数
6. 系统属性（`-D` 参数）
7. **操作系统环境变量**
8. **RandomValuePropertySource**（random.*）
9. **Jar 包外的 `application-{profile}.yml`**
10. **Jar 包内的 `application-{profile}.yml`**
11. **Jar 包外的 `application.yml`**
12. **Jar 包内的 `application.yml`**
13. `@PropertySource` 注解
14. 默认属性（SpringApplication.setDefaultProperties）

### 1.3 `@Value` vs `@ConfigurationProperties`

| 特性 | `@Value` | `@ConfigurationProperties` |
|------|---------|--------------------------|
| 注入单个值 | ✅ 擅长 | ✅ 支持 |
| 注入复杂对象（Map/List） | ❌ 麻烦 | ✅ 擅长 |
| 校验（`@Valid`） | ❌ | ✅ |
| IDE 元数据提示 | ❌ | ✅ |
| 松散绑定（`kebab-case`） | ❌ | ✅ |
| 推荐场景 | 简单值（端口、路径） | 业务配置类 |

## 2. 代码示例

### 2.1 简单配置 + @Value

```java
@Value("${server.port}")
private Integer port;

@Value("${yudao.name:yudao}")  // 默认值 yudao
private String name;
```

### 2.2 复杂配置 + @ConfigurationProperties

```java
// 文件：MyProperties.java
@Data
@ConfigurationProperties(prefix = "yudao.email")
@Validated
public class EmailProperties {
    @NotBlank
    private String host;
    @Min(1) @Max(65535)
    private Integer port = 465;
    private String username;
    private String password;
    private Duration timeout = Duration.ofSeconds(10);
}
```

```yaml
# application.yml
yudao:
  email:
    host: smtp.example.com
    port: 465
    username: noreply@example.com
    password: ${EMAIL_PASSWORD}  # 来自环境变量
    timeout: 30s
```

### 2.3 激活 Profile

> 📌 **Sighting**：多环境 Profile 完整用法见 [06-profile](./06-profile.md)。

```yaml
# application.yml
spring:
  profiles:
    active: dev  # 激活 application-dev.yml
```

## 3. 关键要点总结

- **`application.yml` 优先级低于命令行参数和环境变量**
- **多环境配置**：`application-{profile}.yml` + `spring.profiles.active`
- **`@ConfigurationProperties` 适合复杂配置类**，`@Value` 适合简单值
- **ruoyi 配置约定**：`yudao.{module}.{key}` 命名空间
- **`@Validated`** 让配置类启动时校验，配置错误立即失败
- **常见错误**：配置项没生效 → 检查 Profile、yaml 缩进、占位符语法

---

**文档版本**：v1.0
**最后更新**：2026-07-13
