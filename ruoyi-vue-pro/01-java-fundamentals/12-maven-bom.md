# 1.2.2 Maven 依赖管理：BOM 与 dependencyManagement

> 理解 Maven `dependencyManagement`（BOM）与 `dependencies` 的差异，看懂 ruoyi-vue-pro 统一管理 100+ 依赖版本的方法。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 `<dependencies>` 与 `<dependencyManagement>` 的本质差别
- 理解 BOM（Bill of Materials）的概念
- 解释 ruoyi 中"父 POM 只管理版本号，子 POM 不写版本号"的模式
- 能够动手编写自定义 BOM 模块

## 📚 前置知识

- Maven 多模块项目结构
- 11-maven-modules.md

## 1. 核心概念

### 1.1 `<dependencies>` vs `<dependencyManagement>`

| 标签                                | 作用                          | 是否引入依赖        |
|-----------------------------------|-----------------------------|---------------|
| `<dependencies>`                   | **声明**依赖（每个子模块都能看到）        | **是**         |
| `<dependencyManagement>`           | **管理**依赖版本（默认引入，由子模块决定） | **否**（仅锁定版本） |

**关键差别**：`<dependencies>` 会真的引入 jar；`<dependencyManagement>` 只是一个"版本号仓库"，子模块要主动用 `<dependencies>` 声明才会被引入。

### 1.2 BOM（Bill of Materials）

BOM 是一个特殊的 POM 文件，专门用于**集中管理依赖版本**。一般模式是：

```xml
<dependencyManagement>
    <dependencies>
        <dependency>...</dependency>   <!-- 100+ 依赖版本 -->
    </dependencies>
</dependencyManagement>
```

子模块只需要 `<scope>import</scope>` 引入 BOM：

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>com.example</groupId>
            <artifactId>my-bom</artifactId>
            <version>1.0</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

### 1.3 ruoyi 的 100+ 依赖版本管理

ruoyi-vue-pro 把所有第三方依赖版本号集中在 `yudao-dependencies/pom.xml` 中，其他模块通过 `<scope>import</scope>` 引入它。

这样做的好处：
- **版本号一站式管理**：升级 Spring Boot 只改一处
- **避免冲突**：依赖冲突（传递依赖）一目了然
- **简化子模块**：子 POM 不写版本号，可读性更好

## 2. 代码示例

### 2.1 自定义 BOM 模块

**`my-dependencies/pom.xml`**：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project>
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>my-dependencies</artifactId>
    <version>1.0.0</version>
    <packaging>pom</packaging>

    <!-- BOM 模块本身只负责管版本，不应引入实际依赖 -->
    <dependencyManagement>
        <dependencies>
            <!-- 第三方依赖：只声明版本号 -->
            <dependency>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-dependencies</artifactId>
                <version>3.2.0</version>
                <type>pom</type>
                <scope>import</scope>
            </dependency>
            <dependency>
                <groupId>com.baomidou</groupId>
                <artifactId>mybatis-plus</artifactId>
                <version>3.5.7</version>
            </dependency>
        </dependencies>
    </dependencyManagement>
</project>
```

**`my-app/pom.xml`**：

```xml
<project>
    <parent>
        <groupId>com.example</groupId>
        <artifactId>my-parent</artifactId>
        <version>1.0.0</version>
    </parent>

    <dependencyManagement>
        <dependencies>
            <!-- 引入 BOM -->
            <dependency>
                <groupId>com.example</groupId>
                <artifactId>my-dependencies</artifactId>
                <version>1.0.0</version>
                <type>pom</type>
                <scope>import</scope>
            </dependency>
        </dependencies>
    </dependencyManagement>

    <dependencies>
        <!-- 实际引入依赖：不需要写版本号 -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>com.baomidou</groupId>
            <artifactId>mybatis-plus</artifactId>
        </dependency>
    </dependencies>
</project>
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 父 POM 引入 BOM

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/pom.xml`
**核心代码**（行 54-64）：

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>cn.iocoder.boot</groupId>
            <artifactId>yudao-dependencies</artifactId>
            <version>${revision}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

**解读**：
- 第 6 行：`${revision}` 是 `flatten-maven-plugin` 提供的变量，能在多模块间共享版本号
- 第 7 行：`type=pom` + `scope=import` 是 BOM 引入的标准写法

### 3.2 关键依赖版本统一管理

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/pom.xml`（同上文）
**核心代码**（行 38-52）：

```xml
<properties>
    <revision>2026.06-jdk8-SNAPSHOT</revision>
    <!-- Maven 相关 -->
    <java.version>1.8</java.version>
    <maven-surefire-plugin.version>3.5.3</maven-surefire-plugin.version>
    <maven-compiler-plugin.version>3.14.0</maven-compiler-plugin.version>
    <flatten-maven-plugin.version>1.7.2</flatten-maven-plugin.version>
    <!-- maven-surefire-plugin 暂时无法通过 bom 的依赖读取（兼容老版本 IDEA 2024 及以前版本） -->
    <lombok.version>1.18.42</lombok.version>
    <spring.boot.version>2.7.18</spring.boot.version>
    <mapstruct.version>1.6.3</mapstruct.version>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
</properties>
```

**解读**：
- 第 2 行：`<revision>` 是整个项目的版本号，配合 `flatten-maven-plugin` 让 `yudao-server` 打包时把所有 transitive 依赖版本号变成具体值
- 第 4-5 行：JDK 8 + Spring Boot 2.7.x（ruoyi 当前主要兼容老版本）
- 第 7 行：注释说明为什么 `maven-surefire-plugin` 不能用 BOM 管理（旧版 IDEA 不支持）

## 4. 关键要点总结

- `<dependencies>` 引入依赖，`<dependencyManagement>` 只锁定版本
- BOM 是一个 `packaging=pom` 的特殊模块，用 `<scope>import</scope>` 引入
- ruoyi 通过 `yudao-dependencies` 集中管理 100+ 依赖版本
- 子模块不写版本号，所有版本由 BOM 决定

## 5. 练习题

### 练习 1：基础（必做）

在自己的电脑上创建一个 2 模块项目：`my-bom`（BOM 模块）+ `my-app`（应用模块），验证 "子模块不写版本号也能正常构建"。

### 练习 2：进阶

查看 `yudao-dependencies/pom.xml`，列出它管理的 5 个常见依赖及其版本号。

### 练习 3：挑战（选做）

阅读 `pom.xml` 第 78-100 行的 `maven-compiler-plugin` 配置，解释为什么配置 `spring-boot-configuration-processor` + Lombok + `lombok-mapstruct-binding` 这 3 个注解处理器才能让 `@ConfigurationProperties` 和 MapStruct 一起正常工作。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/pom.xml`
- Maven 官方 BOM 文档：https://maven.apache.org/guides/introduction/introduction-to-dependency-mechanism.html
- 《Maven 实战》第 6 章：依赖

---

**文档版本**：v1.0
**最后更新**：2026-07-13
