# 1.2.1 Maven 多模块项目结构

> 理解 Maven 多模块项目的核心思想，看懂 ruoyi-vue-pro 的父子模块拆分。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Maven 多模块的价值（复用、依赖管理、模块边界）
- 看懂 `<modules>` 配置与聚合 / 继承关系
- 区分 ruoyi 中的 `dependencies` / `framework` / `module-*` / `server` 模块
- 能动手搭建简单的多模块项目

## 📚 前置知识

- Maven 基础（`<dependency>`、`<scope>`）
- Java 基础工具链

## 1. 核心概念

### 1.1 为什么需要多模块？

单模块项目随着业务膨胀会遇到以下问题：
- 一个功能可能影响整个应用（编译慢、耦合严重）
- 团队成员间代码冲突频繁
- 工具类难以被多个业务复用

Maven 多模块通过"父子项目 + 模块拆分"解决：
- **编译隔离**：只编译改动的子模块
- **职责清晰**：`framework` 与 `business` 解耦
- **复用性**：`common` 工具类被多个业务模块共享

### 1.2 父子 POM 的两种关系

| 关系         | 描述                                               |
|------------|--------------------------------------------------|
| **聚合（aggregation）** | 父 POM 用 `<modules>` 聚合多个子模块，用于统一构建（一个 `mvn install` 编译所有子项目） |
| **继承（inheritance）** | 父 POM 通过 `<dependencyManagement>` 配置，子模块自动继承默认版本号（BOM 与版本统一详见 [12-maven-bom](./14-maven-bom.md)） |

二者经常组合——一个父 POM 既聚合又管理依赖。

### 1.3 ruoyi 的模块布局

```
yudao                                       (父 POM，纯管理)
├── yudao-dependencies                      (BOM：管依赖版本号)
├── yudao-framework                         (框架通用层：security/redisson/mybatis)
│   ├── yudao-common                        (POJO/Utils/Exception)
│   ├── yudao-spring-boot-starter-web
│   ├── yudao-spring-boot-starter-redis
│   ├── yudao-spring-boot-starter-security
│   ├── yudao-spring-boot-starter-mybatis
│   └── ... 20+ starter
├── yudao-module-system                     (业务模块：用户/角色/权限)
├── yudao-module-infra                      (基础设施：代码生成、文件存储)
├── yudao-module-crm / erp / pay / mall ...  (其他业务模块)
└── yudao-server                            (启动主程序：聚合所有 module)
```

## 2. 代码示例

### 2.1 一个最小化多模块项目结构

```
parent/
├── pom.xml                    (父 POM)
├── common/
│   ├── pom.xml
│   └── src/main/java/...
└── app/
    ├── pom.xml
    └── src/main/java/...
```

**父 POM** (`pom.xml`)：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>parent</artifactId>
    <version>1.0.0</version>
    <packaging>pom</packaging>

    <modules>
        <module>common</module>      <!-- 聚合 -->
        <module>app</module>
    </modules>

    <!-- 共享依赖版本：被所有子模块继承 -->
    <dependencyManagement>
        <dependencies>
            <dependency>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-dependencies</artifactId>
                <version>3.2.0</version>
                <type>pom</type>
                <scope>import</scope>
            </dependency>
        </dependencies>
    </dependencyManagement>
</project>
```

**子模块 POM** (`common/pom.xml`)：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>

    <!-- 继承父 POM -->
    <parent>
        <groupId>com.example</groupId>
        <artifactId>parent</artifactId>
        <version>1.0.0</version>
        <relativePath>../pom.xml</relativePath>
    </parent>

    <artifactId>common</artifactId>
    <dependencies>
        <!-- 这里不需要写版本号，父 POM 已统一管理 -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter</artifactId>
        </dependency>
    </dependencies>
</project>
```

## 3. 关键要点总结

- Maven 多模块通过父 POM 的 `<modules>` 聚合 + `<dependencyManagement>` 统一依赖版本
- ruoyi 4 级结构：根 → dependencies → framework → module-* → server
- 注释掉的 module 在大公司很常见——按业务需求决定是否启用

---

**文档版本**：v1.0
**最后更新**：2026-07-13
