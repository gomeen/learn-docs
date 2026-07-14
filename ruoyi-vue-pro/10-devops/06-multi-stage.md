# 2.2 多阶段构建：减小镜像

> 理解 Docker 多阶段构建（Multi-Stage Build）的原理，掌握把构建产物从大镜像提取到小镜像的方法。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解多阶段构建的工作原理
- 掌握 `FROM ... AS` 与 `COPY --from` 语法
- 能为 Java 应用编写多阶段 Dockerfile
- 了解镜像大小对生产环境的影响

## 📚 前置知识

- Docker 基础
- Maven 打包（`02-spring-boot-jar.md`）
- `05-java-docker.md`

## 1. 核心概念

### 1.1 为什么需要多阶段？

**单阶段构建的问题**：
- 包含 Maven、Node.js 等构建工具，镜像 **>1GB**
- 构建工具也是攻击面（不必要的依赖）
- 拉取慢、占用更多存储

**多阶段构建**的核心思想：
- **第一阶段**：用完整 JDK + Maven 编译出 jar（包含构建工具）
- **第二阶段**：只把 jar 复制到精简的 JRE 镜像（不含构建工具）
- 最终镜像**只有运行时必要的部分**

### 1.2 镜像大小对比

| 阶段 | 镜像 | 大小 |
|------|------|------|
| 单阶段（JDK） | `openjdk:8-jdk` | ~600MB |
| 单阶段（JRE） | `eclipse-temurin:8-jre` | ~250MB |
| 多阶段（最终） | `eclipse-temurin:8-jre-jammy` | **~280MB** |
| 多阶段（alpine） | `eclipse-temurin:8-jre-alpine` | **~180MB** |

多阶段镜像**通常比单阶段 JRE 镜像略大**（因为 RUN 层的依赖），但**比单阶段 JDK 镜像小 50%+**。

### 1.3 多阶段语法

```dockerfile
# 阶段 1：构建
FROM maven:3.8-openjdk-8 AS builder
WORKDIR /build
COPY pom.xml .
RUN mvn dependency:go-offline
COPY src ./src
RUN mvn package -DskipTests

# 阶段 2：运行
FROM eclipse-temurin:8-jre
WORKDIR /app
COPY --from=builder /build/target/*.jar app.jar
CMD java -jar app.jar
```

`COPY --from=builder` 表示**从 builder 阶段**的文件系统复制。

## 2. 代码示例

### 2.1 完整的多阶段构建

```dockerfile
# 文件：Dockerfile

# ===== 阶段 1：使用 Maven 镜像编译项目 =====
FROM maven:3.8-openjdk-8 AS builder

WORKDIR /build
# 先复制 pom.xml 并下载依赖（利用 Docker 缓存）
COPY pom.xml .
RUN mvn dependency:go-offline -B

# 复制源码并编译
COPY src ./src
RUN mvn clean package -DskipTests -B

# ===== 阶段 2：只保留运行时需要的 jar =====
FROM eclipse-temurin:8-jre

WORKDIR /app
COPY --from=builder /build/target/*.jar app.jar

ENV TZ=Asia/Shanghai
EXPOSE 8080
CMD ["java", "-jar", "app.jar"]
```

**说明**：
- 阶段 1 命名为 `builder`，方便阶段 2 引用
- 阶段 1 的所有层都**不会**进入最终镜像
- 阶段 2 的 `COPY --from=builder` 只复制构建产物

### 2.2 多阶段构建的最佳实践

```dockerfile
# 1. 缓存依赖层：先复制 pom.xml 下载依赖
COPY pom.xml .
RUN mvn dependency:go-offline

# 2. 后复制源码：源码变化时不需要重下依赖
COPY src ./src
RUN mvn package -DskipTests
```

**说明**：
- Docker 按层缓存：`pom.xml` 没变就不会重下依赖
- 源码改动**只重编 jar**，不重下几百 MB 的 Maven 依赖

## 3. ruoyi 仓库源码解读

**注**：ruoyi 当前 Dockerfile 是**单阶段**的（直接复制宿主机构建好的 jar）。

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/Dockerfile`
**核心代码**（行 1-10）：

```dockerfile
## AdoptOpenJDK 停止发布 OpenJDK 二进制，而 Eclipse Temurin 是它的延伸，提供更好的稳定性
FROM eclipse-temurin:8-jre

## 创建目录，并使用它作为工作目录
RUN mkdir -p /yudao-server
WORKDIR /yudao-server
## 将后端项目的 Jar 文件，复制到镜像中
COPY ./target/yudao-server.jar app.jar
```

**当前实现**：
- 第 4 行：单阶段，使用 JRE 镜像
- 第 9 行：`COPY ./target/yudao-server.jar` — 复制**宿主机**已经构建好的 jar
- 镜像大小约 250MB

**改进方向（多阶段版本）**：

```dockerfile
# 建议改造为多阶段（参考）
FROM maven:3.8-openjdk-8 AS builder
WORKDIR /build
COPY . .
RUN mvn clean package -pl yudao-server -am -DskipTests

FROM eclipse-temurin:8-jre
WORKDIR /yudao-server
COPY --from=builder /build/yudao-server/target/yudao-server.jar app.jar
ENV TZ=Asia/Shanghai
ENV JAVA_OPTS="-Xms512m -Xmx512m"
EXPOSE 48080
CMD java ${JAVA_OPTS} -jar app.jar
```

**对比**：
- 当前实现：依赖宿主机构建（CI 必须先 `mvn package`）
- 多阶段：Docker 内部完成构建，CI 只需 `docker build`
- 多阶段优势：避免 "在我机器上能跑" 问题

## 4. 关键要点总结

- 多阶段构建通过 `FROM ... AS <name>` + `COPY --from=<name>` 复用前阶段的产物
- 最终镜像**不包含**构建工具，体积小、攻击面小
- **缓存优化**：先复制 `pom.xml` 缓存依赖层，源码变化不影响依赖下载
- ruoyi 当前是单阶段（依赖宿主机构建），可改造为多阶段
- 多阶段 vs 单阶段：JRE 镜像约 250MB，多阶段 + JRE 约 280MB（多了 RUN 层），但**比单阶段 JDK 600MB 小 50%+**

## 5. 练习题

### 练习 1：基础（必做）

把 `yudao-server/Dockerfile` 改造成多阶段：使用 `maven:3.8-openjdk-8 AS builder`，在 Docker 内执行 `mvn clean package`，第二阶段只复制 jar。比较改造前后 `docker images` 的大小。

### 练习 2：进阶

在多阶段构建中添加 `.dockerignore`（忽略 `target/`、`*.iml`、`.git/`），观察 `docker build` 的速度提升。

### 练习 3：挑战（选做）

尝试将最终镜像替换为 `eclipse-temurin:8-jre-alpine`，观察 Spring Boot 启动时是否出现 musl/glibc 兼容性问题（如 Netty 的 `DnsNameResolver`）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/Dockerfile`
- [Docker 官方文档 - 多阶段构建](https://docs.docker.com/build/building/multi-stage/)
- [Spring Boot Docker 官方指南](https://spring.io/guides/topicals/spring-boot-docker)

---

**文档版本**：v1.0
**最后更新**：2026-07-13
