# 1.2 Spring Boot 打包：jar / war

> 理解 Spring Boot 应用的两种打包方式，掌握 ruoyi 的 `spring-boot-maven-plugin` 实战配置。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 Spring Boot 的 jar 包和 war 包
- 理解 `spring-boot-maven-plugin` 的 `repackage` 机制
- 能独立打包 ruoyi 后端服务
- 知道如何通过 `finalName` 控制产物名称

## 📚 前置知识

- Maven 基础（`pom.xml`、`<build>` 配置，详见 [Maven 多模块](./01-maven-build.md)）
- Spring Boot 启动与打包（详见 [启动流程](../02-spring-boot/07-startup.md)）

## 1. 核心概念

### 1.1 Spring Boot 的两种打包方式

| 特性 | jar（可执行） | war（外部容器） |
|------|--------------|----------------|
| 启动方式 | `java -jar xxx.jar` | 部署到 Tomcat |
| 内嵌容器 | Tomcat/Jetty | 外部 Tomcat |
| 部署单位 | 单文件 | war 文件 + Tomcat |
| 适合场景 | 微服务、容器化 | 传统企业应用 |

ruoyi 使用 **jar 方式**（便于 Docker 部署）。

### 1.2 spring-boot-maven-plugin 的 repackage 目标

普通的 `mvn package` 生成的 jar **不可执行**（缺少依赖和 main class 入口）。

`repackage` 目标会做两件事：
1. 把所有依赖（`<scope>compile</scope>`）打进同一个 jar
2. 把 `main class` 写入 jar 的 `MANIFEST.MF`

最终产物是一个 **Fat Jar**（包含所有依赖的可执行 jar）。

### 1.3 Fat Jar 的目录结构

```
yudao-server.jar
├── BOOT-INF/
│   ├── classes/        # 项目自己的 .class
│   └── lib/            # 所有第三方依赖 .jar
├── META-INF/
│   └── MANIFEST.MF     # 包含 Main-Class: cn.iocoder.yudao.YudaoServerApplication
└── org/springframework/boot/loader/  # Spring Boot 的 ClassLoader
```

## 2. 代码示例

### 2.1 spring-boot-maven-plugin 基础配置

```xml
<build>
    <plugins>
        <plugin>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-maven-plugin</artifactId>
            <version>2.7.18</version>
            <executions>
                <execution>
                    <goals>
                        <goal>repackage</goal>
                    </goals>
                </execution>
            </executions>
        </plugin>
    </plugins>
</build>
```

**说明**：
- `<goal>repackage</goal>`：打包时执行 repackage，把依赖打进 jar
- 如果不写这个 goal，生成的 jar **不能直接运行**

### 2.2 通过 finalName 控制产物名

```xml
<build>
    <finalName>${project.artifactId}</finalName>
    <plugins>
        <plugin>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-maven-plugin</artifactId>
        </plugin>
    </plugins>
</build>
```

**说明**：
- 默认产物名是 `${artifactId}-${version}.jar`（如 `yudao-server-2026.06-jdk8-SNAPSHOT.jar`）
- 设置 `<finalName>` 后变成 `yudao-server.jar`（部署脚本约定的名字）

## 3. ruoyi 仓库源码解读

### 3.1 yudao-server 的打包配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/pom.xml`
**核心代码**（行 153-172）：

```xml
<build>
    <!-- 设置构建的 jar 包名 -->
    <finalName>${project.artifactId}</finalName>
    <plugins>
        <!-- 打包 -->
        <plugin>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-maven-plugin</artifactId>
            <version>${spring.boot.version}</version>
            <executions>
                <execution>
                    <goals>
                        <goal>repackage</goal> <!-- 将引入的 jar 打入其中 -->
                    </goals>
                </execution>
            </executions>
        </plugin>
    </plugins>
</build>
```

**解读**：
- 第 156 行：`<finalName>${project.artifactId}</finalName>` — 强制产物名为 `yudao-server.jar`（不含版本号）
- 第 158 行：`<version>${spring.boot.version}</version>` — 引用根 POM 的 Spring Boot 版本（2.7.18）
- 第 159-170 行：`<execution>` 绑定到默认 phase（`package`），执行 `repackage` 目标
- 第 166 行注释："将引入的 jar 打入其中" — 这就是 Fat Jar 的核心作用

### 3.2 Dockerfile 引用 jar 包

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/Dockerfile`
**核心代码**（行 6-9）：

```dockerfile
## 创建目录，并使用它作为工作目录
RUN mkdir -p /yudao-server
WORKDIR /yudao-server
## 将后端项目的 Jar 文件，复制到镜像中
COPY ./target/yudao-server.jar app.jar
```

**解读**：
- 第 9 行：`COPY ./target/yudao-server.jar app.jar` — 引用 `finalName` 配置的产物名
- Docker 镜像中 jar 被重命名为 `app.jar`（容器内的命名约定）

### 3.3 部署脚本启动 jar

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
**核心代码**（行 102）：

```bash
# 开始启动
BUILD_ID=dontKillMe nohup java -server $JAVA_OPS $JAVA_AGENT -jar $BASE_PATH/$SERVER_NAME.jar --spring.profiles.active=$PROFILES_ACTIVE &
echo "[start] 启动 $BASE_PATH/$SERVER_NAME 完成"
```

**解读**：
- `BUILD_ID=dontKillMe` — 防止 Jenkins 在 build 完成后杀掉衍生进程
- `nohup ... &` — 后台启动
- `java -jar yudao-server.jar` — 直接执行可执行 jar（不需要 `java -cp`）
- `--spring.profiles.active=$PROFILES_ACTIVE` — 启动时切换 profile

## 4. 关键要点总结

- Spring Boot 用 `spring-boot-maven-plugin` 的 `repackage` 目标生成 Fat Jar
- ruoyi 用 `<finalName>${project.artifactId}</finalName>` 固定产物名，便于脚本和 Dockerfile 引用
- Fat Jar 包含所有依赖，**单文件即可运行**：`java -jar yudao-server.jar`
- Docker 部署时，jar 在容器内通常重命名为 `app.jar`

## 5. 练习题

### 练习 1：基础（必做）

执行 `mvn clean package -pl yudao-server -am -DskipTests`，在 `yudao-server/target/` 下找到 `yudao-server.jar`，运行 `java -jar yudao-server.jar` 验证能否启动。

### 练习 2：进阶

解压 `yudao-server.jar`（`jar tf yudao-server.jar | head -50` 或 `unzip -l`），观察 `BOOT-INF/lib/` 下的依赖列表，找出 `mybatis-plus`、`dynamic-datasource` 等关键依赖。

### 练习 3：挑战（选做）

修改 `pom.xml` 添加 `<configuration><mainClass>...</mainClass></configuration>` 显式指定 main class，理解 repackage 后的 `MANIFEST.MF` 是怎么写入 main class 的。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/pom.xml`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/Dockerfile`
- `/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
- [Spring Boot 官方文档 - 构建工具](https://docs.spring.io/spring-boot/docs/2.7.x/reference/html/getting-started.html#getting-started.first-application.executable-jar)

---

**文档版本**：v1.0
**最后更新**：2026-07-13
