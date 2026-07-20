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
- 外部化配置（详见 [外部配置](./05-external-config.md)）

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

## 3. 关键要点总结

- `spring.profiles.active` 决定加载哪个 `application-{profile}.yaml`
- ruoyi 默认提供 `local`（开发）和 `dev`（开发服务器）两套
- 建议补充 `prod` 环境用于生产部署
- profile 切换不影响 jar 包，只是切换配置加载源

---

**文档版本**：v1.0
**最后更新**：2026-07-13
