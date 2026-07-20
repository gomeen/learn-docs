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
- Spring Boot 起步（详见 [IoC](../02-spring-boot/01-ioc.md)）
- 可执行 JAR（详见 [Spring Boot JAR](./04-spring-boot-jar.md)）
- 业务多模块划分（详见 [模块结构](../07-business-modules/01-module-structure.md)）

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

## 3. 关键要点总结

- 根 POM 用 `<packaging>pom</packaging>` + `<modules>` 管理子模块
- 所有子模块通过 `<parent>` 继承根 POM，共享 `${revision}` 版本号
- `yudao-server` 是个空壳，通过 `<dependency>` 引入需要的业务模块
- 注释掉不需要的 module 可以加快本地编译速度
- 升级项目版本：修改根 POM 的 `<revision>` 一处即可

---

**文档版本**：v1.0
**最后更新**：2026-07-13
