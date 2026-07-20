# 1.2.2 Maven 依赖管理：BOM 与 dependencyManagement

> 理解 Maven `dependencyManagement`（BOM）与 `dependencies` 的差异，看懂 ruoyi-vue-pro 统一管理 100+ 依赖版本的方法。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 `<dependencies>` 与 `<dependencyManagement>` 的本质差别
- 理解 BOM（Bill of Materials）的概念
- 解释 ruoyi 中"父 POM 只管理版本号，子 POM 不写版本号"的模式
- 能够动手编写自定义 BOM 模块

## 📚 前置知识

- Maven 多模块项目结构（详见 [11-maven-modules](./13-maven-modules.md)）
- 13-maven-modules.md

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

## 3. 关键要点总结

- `<dependencies>` 引入依赖，`<dependencyManagement>` 只锁定版本
- BOM 是一个 `packaging=pom` 的特殊模块，用 `<scope>import</scope>` 引入
- ruoyi 通过 `yudao-dependencies` 集中管理 100+ 依赖版本
- 子模块不写版本号，所有版本由 BOM 决定

---

**文档版本**：v1.0
**最后更新**：2026-07-13
