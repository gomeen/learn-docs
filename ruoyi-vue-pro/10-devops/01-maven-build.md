# 1.1 Maven 多模块构建

> 理解 ruoyi-vue-pro 的多模块 Maven 项目结构，掌握 `${revision}` 统一版本管理。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Maven 多模块项目的设计理念
- 掌握 parent / dependencyManagement / 子模块依赖的层级关系
- 看懂 `flatten-maven-plugin` 与 `${revision}` 统一版本号机制
- 能独立修改 ruoyi 的 `pom.xml` 添加新模块

## 📚 前置知识

- Maven 基础（pom.xml、依赖、坐标）
- Spring Boot 起步
- `02-spring-boot-jar.md`（推荐先看）

## 1. 核心概念

### 1.1 为什么需要多模块？

单模块项目随着业务扩张会面临：
- **编译慢**：改一行代码全量编译
- **复用差**：通用工具类无法被其他项目引用
- **边界模糊**：业务代码和技术组件混在一起

Maven 多模块通过 **父 POM 统一定义版本 + 子 POM 按需引入** 来解决这些问题。

### 1.2 ruoyi 的多模块结构

```
yudao (parent)
├── yudao-dependencies      # 统一管理第三方依赖版本（BOM）
├── yudao-framework         # 自研 starter（web/security/mybatis/redis...）
├── yudao-server            # 主项目（空壳），引入需要的 module-xxx
├── yudao-module-system     # 系统功能（用户/角色/菜单/部门）
├── yudao-module-infra      # 基础设施（代码生成/文件存储/定时任务）
├── yudao-module-bpm        # 工作流
├── yudao-module-mall       # 商城
└── ...                     # 其他业务模块
```

**关键思想**：
- `yudao-server` 是个 **空壳**，通过 `<dependency>` 引入需要的业务模块
- 业务模块之间互不依赖（解耦）
- 所有版本号用 `${revision}` 占位符统一管理

### 1.3 `${revision}` 统一版本

ruoyi 的根 `pom.xml` 中定义：

```xml
<properties>
    <revision>2026.06-jdk8-SNAPSHOT</revision>
</properties>
```

所有子模块的版本号都引用 `${revision}`：

```xml
<parent>
    <groupId>cn.iocoder.boot</groupId>
    <artifactId>yudao</artifactId>
    <version>${revision}</version>  <!-- 统一版本号 -->
</parent>
```

**优势**：升级版本只需改根 POM 的一个地方。

## 2. 代码示例

### 2.1 根 POM 的 modules 声明

```xml
<!-- 文件：/Users/xu/code/github/ruoyi-vue-pro/pom.xml -->
<project>
    <groupId>cn.iocoder.boot</groupId>
    <artifactId>yudao</artifactId>
    <version>${revision}</version>
    <packaging>pom</packaging>
    <modules>
        <module>yudao-dependencies</module>
        <module>yudao-framework</module>
        <module>yudao-server</module>
        <module>yudao-module-system</module>
        <module>yudao-module-infra</module>
    </modules>
</project>
```

**说明**：
- `<packaging>pom</packaging>`：父 POM 不打包
- `<modules>`：声明当前 POM 管理的子模块路径
- 注释掉的 module（如 `yudao-module-ai`）默认不参与编译，加快本地启动速度

### 2.2 子模块依赖父 POM

```xml
<!-- 文件：yudao-server/pom.xml -->
<parent>
    <groupId>cn.iocoder.boot</groupId>
    <artifactId>yudao</artifactId>
    <version>${revision}</version>
</parent>
<artifactId>yudao-server</artifactId>
<packaging>jar</packaging>
```

**说明**：
- 子 POM 通过 `<parent>` 继承父 POM 的 groupId、version、properties
- 子 POM 只需要声明自己的 `artifactId`

## 3. ruoyi 仓库源码解读

### 3.1 根 POM：定义模块 + 统一版本

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/pom.xml`
**核心代码**（行 1-50）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>cn.iocoder.boot</groupId>
    <artifactId>yudao</artifactId>
    <version>${revision}</version>
    <packaging>pom</packaging>
    <modules>
        <module>yudao-dependencies</module>
        <module>yudao-framework</module>
        <!-- Server 主项目 -->
        <module>yudao-server</module>
        <!-- 各种 module 拓展 -->
        <module>yudao-module-system</module>
        <module>yudao-module-infra</module>
    </modules>

    <properties>
        <revision>2026.06-jdk8-SNAPSHOT</revision>
        <java.version>1.8</java.version>
        <maven.compiler.source>${java.version}</maven.compiler.source>
        <maven.compiler.target>${java.version}</maven.compiler.target>
        <lombok.version>1.18.42</lombok.version>
        <spring.boot.version>2.7.18</spring.boot.version>
    </properties>
```

**解读**：
- 第 7-9 行：`${revision}` 占位符 + `<packaging>pom</packaging>` 定义多模块根项目
- 第 18-23 行：`<modules>` 列出所有子模块。注释的 module 不参与编译
- 第 25-30 行：`<properties>` 定义版本号。修改 `<revision>` 即可升级整个项目版本

### 3.2 子模块 yudao-server：空壳 + 按需引入

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/pom.xml`
**核心代码**（行 1-60）：

```xml
<parent>
    <groupId>cn.iocoder.boot</groupId>
    <artifactId>yudao</artifactId>
    <version>${revision}</version>
</parent>

<artifactId>yudao-server</artifactId>
<packaging>jar</packaging>

<dependencies>
    <dependency>
        <groupId>cn.iocoder.boot</groupId>
        <artifactId>yudao-module-system</artifactId>
        <version>${revision}</version>  <!-- 引用同一版本 -->
    </dependency>
    <dependency>
        <groupId>cn.iocoder.boot</groupId>
        <artifactId>yudao-module-infra</artifactId>
        <version>${revision}</version>
    </dependency>
</dependencies>
```

**解读**：
- 第 1-6 行：`<parent>` 继承根 POM，子模块自动获得 `${revision}` 等属性
- 第 10 行：`<packaging>jar</packaging>` 表明这是一个可执行 jar
- 第 13-29 行：按需引入业务模块。注释的 module（如 `yudao-module-bpm`）默认不引入
- **设计意图**：`yudao-server` 只做"组装"，业务代码在 `yudao-module-xxx` 中维护

## 4. 关键要点总结

- 根 POM 用 `<packaging>pom</packaging>` + `<modules>` 管理子模块
- 所有子模块通过 `<parent>` 继承根 POM，共享 `${revision}` 版本号
- `yudao-server` 是个空壳，通过 `<dependency>` 引入需要的业务模块
- 注释掉不需要的 module 可以加快本地编译速度
- 升级项目版本：修改根 POM 的 `<revision>` 一处即可

## 5. 练习题

### 练习 1：基础（必做）

手动修改 `pom.xml` 的 `<revision>` 从 `2026.06-jdk8-SNAPSHOT` 改为 `2026.07-jdk8-SNAPSHOT`，运行 `mvn clean package -pl yudao-server -am`，观察是否所有子模块都使用新版本。

### 练习 2：进阶

阅读 `yudao-server/pom.xml`，列出当前默认引入的所有业务模块，并画出依赖树。

### 练习 3：挑战（选做）

尝试启用 `yudao-module-bpm`（工作流模块）：取消注释 `<module>yudao-module-bpm</module>` 和对应的 `<dependency>`，执行 `mvn clean package -DskipTests` 验证是否能编译通过。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/pom.xml`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/pom.xml`
- [Maven 多模块项目官方文档](https://maven.apache.org/guides/mini/guide-multiple-modules.html)
- ruoyi 官方文档：https://doc.iocoder.cn/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
