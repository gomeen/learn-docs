# 2.1 Java 应用的 Docker 镜像

> 理解如何为 Spring Boot 应用编写 Dockerfile，掌握 ruoyi 的基础镜像与启动命令。

## 🎯 学习目标

完成本文档后，你将能够：
- 编写 Java 应用的 Dockerfile
- 理解基础镜像选择（JDK vs JRE）
- 掌握容器时区与 JVM 参数配置
- 能独立打包 ruoyi 后端镜像

## 📚 前置知识

- Docker 基础（image / container / build）
- `02-spring-boot-jar.md`

## 1. 核心概念

### 1.1 基础镜像选择

| 镜像 | 大小 | 用途 |
|------|------|------|
| `openjdk:8-jdk` | ~600MB | 编译 |
| `eclipse-temurin:8-jre` | ~250MB | **运行 JRE（推荐）** |
| `openjdk:8-jre-slim` | ~200MB | 更精简 |
| `alpine` + JDK | ~150MB | 极简（可能踩 glibc 坑） |

ruoyi 使用 **`eclipse-temurin:8-jre`**（AdoptOpenJDK 停止后由 Eclipse 接管）。

### 1.2 Dockerfile 核心指令

| 指令 | 作用 |
|------|------|
| `FROM` | 指定基础镜像 |
| `WORKDIR` | 设置工作目录（后续命令的执行路径） |
| `COPY` | 复制文件到镜像 |
| `ENV` | 设置环境变量 |
| `EXPOSE` | 声明容器监听的端口（**不真正发布端口**） |
| `CMD` | 容器启动命令（可被 `docker run` 覆盖） |

### 1.3 Docker 镜像分层

Dockerfile 每一行都会生成一个**镜像层**（Layer）。优化原则：
- 不变的层放前面
- 频繁变化的层放后面（利用缓存）
- 多阶段构建减少最终镜像大小

## 2. 代码示例

### 2.1 最简 Java 应用 Dockerfile

```dockerfile
# 文件：Dockerfile
FROM eclipse-temurin:8-jre

WORKDIR /app
COPY target/my-app.jar app.jar

ENV TZ=Asia/Shanghai
ENV JAVA_OPTS="-Xms512m -Xmx512m"

EXPOSE 8080
CMD java ${JAVA_OPTS} -jar app.jar
```

**说明**：
- `FROM eclipse-temurin:8-jre`：使用 Eclipse 维护的 JRE 8
- `WORKDIR /app`：设置工作目录
- `COPY target/my-app.jar app.jar`：把 jar 复制进镜像并重命名
- `ENV JAVA_OPTS`：JVM 参数可通过 `docker run -e "JAVA_OPTS=..."` 覆盖
- `EXPOSE 8080`：声明端口（实际映射靠 `-p`）
- `CMD java ...`：容器启动命令

### 2.2 运行时覆盖环境变量

```bash
# 启动时覆盖 JVM 参数
docker run -e "JAVA_OPTS=-Xms1g -Xmx2g" -p 8080:8080 my-app

# 启动时覆盖应用参数
docker run -e "ARGS=--spring.profiles.active=prod" my-app
```

## 3. ruoyi 仓库源码解读

### 3.1 yudao-server Dockerfile

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/Dockerfile`
**核心代码**（行 1-24）：

```dockerfile
## AdoptOpenJDK 停止发布 OpenJDK 二进制，而 Eclipse Temurin 是它的延伸，提供更好的稳定性
## 感谢复旦核博士的建议！灰子哥，牛皮！
FROM eclipse-temurin:8-jre

## 创建目录，并使用它作为工作目录
RUN mkdir -p /yudao-server
WORKDIR /yudao-server
## 将后端项目的 Jar 文件，复制到镜像中
COPY ./target/yudao-server.jar app.jar

## 设置 TZ 时区
ENV TZ=Asia/Shanghai
## 设置 JAVA_OPTS 环境变量，可通过 docker run -e "JAVA_OPTS=" 进行覆盖
ENV JAVA_OPTS="-Xms512m -Xmx512m -Djava.security.egd=file:/dev/./urandom"

## 应用参数
ENV ARGS=""

## 暴露后端项目的 48080 端口
EXPOSE 48080

## 启动后端项目
CMD java ${JAVA_OPTS} -jar app.jar $ARGS
```

**解读**：
- 第 1-3 行：注释解释为什么选 `eclipse-temurin:8-jre`（AdoptOpenJDK 已 EOL）
- 第 4 行：`FROM eclipse-temurin:8-jre` — 使用 Eclipse Temurin JRE 8 基础镜像
- 第 6-7 行：`RUN mkdir -p` + `WORKDIR` — 创建工作目录
- 第 9 行：`COPY ./target/yudao-server.jar app.jar` — 复制 jar，重命名为 `app.jar`
- 第 12 行：`ENV TZ=Asia/Shanghai` — 设置时区（中国用户）
- 第 14 行：`ENV JAVA_OPTS="-Xms512m -Xmx512m ..."` — 默认 JVM 参数
  - `-Djava.security.egd=file:/dev/./urandom` — 解决 Tomcat 启动慢的 bug（使用 `/dev/urandom` 而非 `/dev/random`）
- 第 17 行：`ENV ARGS=""` — 占位，运行时注入应用参数
- 第 20 行：`EXPOSE 48080` — 声明端口
- 第 23 行：`CMD java ${JAVA_OPTS} -jar app.jar $ARGS` — 启动命令，组合 JVM 参数和应用参数

### 3.2 docker-compose 中构建镜像

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`
**核心代码**（行 29-37）：

```yaml
  server:
    container_name: yudao-server
    build:
      context: ./yudao-server/
    image: yudao-server
    restart: unless-stopped
    ports:
      - "48080:48080"
```

**解读**：
- 第 32-33 行：`build.context: ./yudao-server/` — 相对 docker-compose.yml 的路径，找到 `yudao-server/Dockerfile`
- 第 35 行：`ports: "48080:48080"` — 主机端口:容器端口映射
- 第 34 行：`image: yudao-server` — 构建后的镜像名

### 3.3 docker-compose 注入应用参数

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`
**核心代码**（行 37-53）：

```yaml
    environment:
      SPRING_PROFILES_ACTIVE: local
      JAVA_OPTS:
        ${JAVA_OPTS:-
          -Xms512m
          -Xmx512m
          -Djava.security.egd=file:/dev/./urandom
        }
      ARGS:
        --spring.datasource.dynamic.datasource.master.url=${MASTER_DATASOURCE_URL:-jdbc:mysql://yudao-mysql:3306/ruoyi-vue-pro?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true&nullCatalogMeansCurrent=true}
        --spring.datasource.dynamic.datasource.master.username=${MASTER_DATASOURCE_USERNAME:-root}
        --spring.datasource.dynamic.datasource.master.password=${MASTER_DATASOURCE_PASSWORD:-123456}
        --spring.redis.host=${REDIS_HOST:-yudao-redis}
```

**解读**：
- `environment` 块会设置容器的环境变量
- `SPRING_PROFILES_ACTIVE: local` — 激活 Spring profile
- `JAVA_OPTS`：多行写法，最终会合并成单行字符串
- `ARGS`：作为 `CMD` 末尾的追加参数
- `${VAR:-default}`：docker-compose 的变量插值，未定义时用 default

## 4. 关键要点总结

- 选 **JRE 镜像**（非 JDK）减小体积
- 必须设置时区 `TZ=Asia/Shanghai`，否则日志时间是 UTC
- JVM 添加 `-Djava.security.egd=file:/dev/./urandom` 解决启动慢
- `EXPOSE` 只是声明端口，**实际映射**靠 `docker run -p` 或 `docker-compose ports`
- `ENV` 定义的变量可被 `docker run -e` 或 `docker-compose environment` 覆盖

## 5. 练习题

### 练习 1：基础（必做）

执行 `mvn clean package -pl yudao-server -am -DskipTests`，在 `yudao-server/` 下 `docker build -t yudao-test .` 构建镜像，`docker run -p 48080:48080 yudao-test` 启动验证。

### 练习 2：进阶

修改 `Dockerfile` 把 `EXPOSE 48080` 改成 `EXPOSE 8080`，观察 `docker run -p 48080:48080` 是否能正常工作，理解 EXPOSE 的真正含义。

### 练习 3：挑战（选做）

在 `CMD` 中加 `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dump.hprof`，启动后通过 `docker exec` 模拟 OOM，观察堆转储是否生成。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/Dockerfile`
- `/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`
- [Eclipse Temurin 镜像](https://hub.docker.com/_/eclipse-temurin)
- [Dockerfile 最佳实践](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)

---

**文档版本**：v1.0
**最后更新**：2026-07-13
