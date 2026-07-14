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
| **继承（inheritance）** | 父 POM 通过 `<dependencyManagement>` 配置，子模块自动继承默认版本号 |

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

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 父 POM 聚合多个模块

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/pom.xml`
**核心代码**（行 10-32）：

```xml
<modules>
    <module>yudao-dependencies</module>
    <module>yudao-framework</module>
    <!-- Server 主项目 -->
    <module>yudao-server</module>
    <!-- 各种 module 拓展 -->
    <module>yudao-module-system</module>
    <module>yudao-module-infra</module>
<!--        <module>yudao-module-member</module>-->
<!--        <module>yudao-module-bpm</module>-->
```

**解读**：
- 第 1-2 行：`yudao-dependencies` / `yudao-framework` 是基础设施，BOM 和 starter 集合
- 第 4 行：`yudao-server` 是 Spring Boot 启动程序，把所有业务 module 组合起来
- 第 7-9 行：注释掉的 module（如 `member`、`bpm`、`crm`）表明这是**按需启用**的模块——构建时用 `<maven -pl yudao-module-xxx -am>` 单独构建

### 3.2 各模块的 `pom` 元素

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/pom.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project>
    <parent>
        <artifactId>yudao-framework</artifactId>
        <groupId>cn.iocoder.boot</groupId>
        <version>${revision}</version>
    </parent>
    <modelVersion>4.0.0</modelVersion>
    <artifactId>yudao-common</artifactId>
    <packaging>jar</packaging>
    ...
```

**解读**：
- 第 1 行：`yudao-common` 继承自 `yudao-framework`（而非根 POM），形成了**多级继承**：
  ```
  root pom → yudao-framework → yudao-common
  ```
- 第 7 行：`packaging=jar` 表示这个模块最终打包成 jar（被其他模块依赖）
- 父级继承链中的 `<dependencyManagement>` 配置会自动传递下来

## 4. 关键要点总结

- Maven 多模块通过父 POM 的 `<modules>` 聚合 + `<dependencyManagement>` 统一依赖版本
- ruoyi 4 级结构：根 → dependencies → framework → module-* → server
- 注释掉的 module 在大公司很常见——按业务需求决定是否启用

## 5. 练习题

### 练习 1：基础（必做）

手写一个 3 模块项目：`parent / common / app`，`common` 提供一个工具类 `StringUtils.isEmpty`，`app` 依赖 `common` 并调用它。

### 练习 2：进阶

打开 `yudao-framework/pom.xml`，看一下它聚合了哪些 `starter`，并解释为什么 `redis` 和 `mybatis` 要拆成独立的 starter（而不是一个大依赖）。

### 练习 3：挑战（选做）

解释为什么 `yudao-server` 是 jar 模块而不是 war 模块（说明 Spring Boot 的 jar 包内嵌 Tomcat 的好处）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/pom.xml`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/pom.xml`
- Maven 官方文档：https://maven.apache.org/guides/mini/guide-multiple-modules.html
- 《Maven 实战》第 7 章：聚合与继承

---

**文档版本**：v1.0
**最后更新**：2026-07-13
