# 1.2.3 Maven 生命周期与插件

> 理解 Maven 三大生命周期与常用插件，能在 ruoyi-vue-pro 中执行 `mvn clean install` 完成构建。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Maven 三大生命周期（clean / default / site）
- 掌握常用插件（compiler、surefire、jar）和它们绑定的阶段
- 能在 ruoyi 项目中执行常见构建命令
- 区分 `mvn package` 与 `mvn install` 的差别

## 📚 前置知识

- Maven 多模块项目结构
- 13-maven-modules.md

## 1. 核心概念

### 1.1 三大生命周期

Maven 有三套独立的生命周期，每套内部又分若干**阶段（phase）**：

```
clean → clean
default → validate → compile → test → package → verify → install → deploy
site → site → site-deploy
```

- **clean**：清理工作目录
- **default（核心）**：从验证到部署
- **site**：生成文档网站（不常用）

每个阶段都**有序**：执行 `package` 时，前面所有阶段（`validate` / `compile` / `test`）都会执行。

### 1.2 常用阶段

| 阶段            | 作用                |
|---------------|-------------------|
| `validate`    | 验证项目信息是否正确        |
| `compile`     | 编译主源码             |
| `test`        | 运行单元测试            |
| `package`     | 打包（jar/war）       |
| `verify`      | 运行集成测试 / 检查       |
| `install`     | 装到本地仓库            |
| `deploy`      | 部署到远程仓库           |

### 1.3 插件与生命周期绑定

每个阶段由一个**插件目标（plugin goal）**实现：

| 阶段          | 默认插件                              |
|-------------|-----------------------------------|
| `compile`   | `maven-compiler-plugin:compile`   |
| `test`      | `maven-surefire-plugin:test`      |
| `package`   | `maven-jar-plugin:jar`            |

插件可以被自定义配置：

```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-compiler-plugin</artifactId>
    <version>3.14.0</version>
    <configuration>
        <source>1.8</source>
        <target>1.8</target>
    </configuration>
</plugin>
```

### 1.4 `package` vs `install` vs `deploy`

| 命令              | 产物位置                |
|-----------------|-----------------------|
| `mvn package`   | `target/xxx.jar`      |
| `mvn install`   | `~/.m2/repository/...` |
| `mvn deploy`    | 上传到远程仓库              |

`install` 的产物能被本机的其他 Maven 项目引用；`deploy` 是发布到团队共享仓库。

## 2. 代码示例

### 2.1 常用 Maven 命令

```bash
# 清理 + 编译 + 测试 + 打包
mvn clean package

# 编译并安装到本地仓库（这样其他模块可依赖）
mvn clean install

# 跳过测试
mvn clean install -DskipTests

# 单模块构建（-pl 指定模块，-am 同时构建依赖的模块）
mvn -pl yudao-server -am clean install

# 只运行测试
mvn test

# 直接运行 Spring Boot 应用（需要 spring-boot-maven-plugin）
mvn spring-boot:run

# 打包时不跑测试
mvn package -Dmaven.test.skip=true
```

### 2.2 常见错误：父模块 install 失败导致子模块找不到依赖

```bash
# ❌ 子模块找不到依赖
$ mvn -pl yudao-server compile
[ERROR] Could not find artifact cn.iocoder.boot:yudao-common:jar:2026.06-SNAPSHOT

# ✅ 先 install 所有依赖的模块
$ mvn clean install
...
# 或者只 install 必要的依赖模块
$ mvn -pl yudao-common -am install
```

## 3. 关键要点总结

- Maven 三大生命周期：clean / default / site
- 每个阶段由特定插件目标实现，可自定义配置
- `install` 把产物装到本地仓库，`deploy` 上传远程仓库
- ruoyi 用 `maven-compiler-plugin` 的 `<annotationProcessorPaths>` 解决 Lombok + MapStruct 编译问题

---

**文档版本**：v1.0
**最后更新**：2026-07-13
