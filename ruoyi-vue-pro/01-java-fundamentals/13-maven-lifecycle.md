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
- 11-maven-modules.md

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

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 注解处理器（解决 Spring Boot + Lombok + MapStruct 兼容问题）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/pom.xml`
**核心代码**（行 76-100）：

```xml
<!-- maven-compiler-plugin 插件，解决 spring-boot-configuration-processor + Lombok + MapStruct 组合（Lombok 见 [14-lombok](./14-lombok.md)，MapStruct 见 [15-mapstruct](./15-mapstruct.md)） -->
<!-- https://stackoverflow.com/questions/33483697/re-run-spring-boot-configuration-processor-to-update-generated-metada -->
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-compiler-plugin</artifactId>
    <version>${maven-compiler-plugin.version}</version>
    <configuration>
        <annotationProcessorPaths>
            <path>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-configuration-processor</artifactId>
                <version>${spring.boot.version}</version>
            </path>
            <path>
                <groupId>org.projectlombok</groupId>
                <artifactId>lombok</artifactId>
                <version>${lombok.version}</version>
            </path>
            <path>
                <!-- 确保 Lombok 生成的 getter/setter 方法能被 MapStruct 正确识别，
                     避免出现 No property named “xxx" exists 的编译错误 -->
                <groupId>org.projectlombok</groupId>
                <artifactId>lombok-mapstruct-binding</artifactId>
                <version>0.2.0</version>
            </path>
```

**解读**：
- 第 3 行：注释里有 Stack Overflow 链接，说明这个组合坑很大
- 第 7-19 行：用 `<annotationProcessorPaths>` 而非 `<dependencies>`，这三个 jar 只在编译期使用，不会污染运行时
- 第 21 行：注释说明 `lombok-mapstruct-binding` 是关键——它让 MapStruct 在编译期能看到 Lombok 生成的 getter/setter

### 3.2 flatten-maven-plugin：解决子模块版本引用问题

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/pom.xml`
**核心代码**（类似第 76-100 行附近的 `flatten-maven-plugin` 配置，未直接展示）：
```
核心作用：在 install 阶段把 ${revision} 占位符替换为具体版本号（如 2026.06-jdk8-SNAPSHOT）。
```
- 用来解决 Maven 多模块的版本不一致问题
- 子模块的 pom.xml 在 install 后会变成具体的版本号

## 4. 关键要点总结

- Maven 三大生命周期：clean / default / site
- 每个阶段由特定插件目标实现，可自定义配置
- `install` 把产物装到本地仓库，`deploy` 上传远程仓库
- ruoyi 用 `maven-compiler-plugin` 的 `<annotationProcessorPaths>` 解决 Lombok + MapStruct 编译问题

## 5. 练习题

### 练习 1：基础（必做）

在自己电脑上创建一个简单项目，分别运行 `mvn package` 与 `mvn install`，对比 `target/xxx.jar` 与 `~/.m2/repository/xxx` 是否同时存在。

### 练习 2：进阶

阅读 `maven-compiler-plugin` 配置，解释为什么 Lombok 这种"运行时需要"的依赖要放在 `<annotationProcessorPaths>`（编译时）而不是 `<dependencies>`（运行时）。

### 练习 3：挑战（选做）

尝试运行 `mvn dependency:tree -pl yudao-server`，观察 Spring Boot 启动模块的依赖树，找出 MyBatis-Plus 真实的版本号。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/pom.xml`
- Maven 官方生命周期文档：https://maven.apache.org/guides/introduction/introduction-to-the-lifecycle.html
- 《Maven 实战》第 4 章：生命周期

---

**文档版本**：v1.0
**最后更新**：2026-07-13
