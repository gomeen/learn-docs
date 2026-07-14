# 9.3 多阶段构建：减小镜像体积

> 通过多阶段构建，把"构建工具"留在 builder 阶段，只把"运行时产物"带到最终镜像。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解多阶段构建的"只搬运最终产物"思想
- 用 `COPY --from=` 跨阶段搬运文件
- 解释为何 dify 的 Python API 需要多阶段（把 venv 装入运行时）
- 了解 ruoyi JVM 应用的"单 jar"是否真的需要多阶段

## 📚 前置知识

- 9.2 Dockerfile 编写最佳实践
- 编译型语言 vs 解释型语言的区别
- /Users/xu/code/gomeen/learn-docs/_common/09-containerization/02-dockerfile.md

## 1. 核心概念

### 1.1 什么是多阶段构建？

在 **同一个 Dockerfile** 中定义**多个 `FROM`**，每个阶段用一个别名标记。最终镜像只来自最后一个阶段，但可以通过 `COPY --from=<stage>` 引用前面阶段的产物。

```
  Stage 1: builder                 Stage 2: runtime
 ┌──────────────────────┐          ┌──────────────────────┐
 │ FROM golang:1.22     │          │ FROM alpine:3.19     │
 │ COPY . .             │  ─────►  │ COPY --from=builder  │
 │ RUN go build -o app  │  binary  │      /app/bin /app/  │
 │ (300 MB 的 Go 工具链) │          │                      │
 └──────────────────────┘          │ (镜像只含 5MB binary) │
                                   └──────────────────────┘
```

**核心收益**：编译工具、源码、中间产物都不会出现在最终镜像中。

### 1.2 为什么 Python 应用也要多阶段？

**直觉**：Python 是解释型语言，似乎不需要编译。实际上：
- 构建依赖（`uv`、`pip`）通常需要 `gcc`、`libpq-dev` 等编译工具
- 这些工具**运行时并不需要**

**dify 的做法**：把 `uv sync` 放在 `packages` 阶段，把生成的 `.venv` 通过 `COPY --from=packages` 搬到 `production` 阶段。

### 1.3 为何 JVM 应用"单 jar 就够"？

JVM 应用"编译产物 = jar/war"已经是一个独立的可运行单元，**不再需要 JVM 编译工具**。

因此 ruoyi 的 `yudao-server/Dockerfile` 用单阶段即可：
```dockerfile
FROM eclipse-temurin:8-jre      # 运行时镜像
COPY target/*.jar app.jar        # 直接复制 jar
```

但 ruoyi 真正的"瘦身"在更深的层面——比如**多模块拆分**：在生产环境把 `yudao-module-system` jar 抽出来独立部署，节约容器内存。

## 2. 代码示例

### 2.1 Go 多阶段构建（教科书示范）

```dockerfile
# 文件：Dockerfile.multistage-go

# ============== Stage 1: builder ==============
FROM golang:1.22-alpine AS builder

WORKDIR /src
# 缓存层：依赖文件
COPY go.mod go.sum ./
RUN go mod download

# 源码
COPY . .

# 静态编译（CGO=0），单文件 ~10MB
RUN CGO_ENABLED=0 GOOS=linux go build -o /out/app .

# ============== Stage 2: runtime ==============
FROM alpine:3.19

RUN apk --no-cache add ca-certificates tzdata && \
    cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

WORKDIR /app
COPY --from=builder /out/app /app/app

# 非 root
RUN adduser -D -u 1001 appuser
USER appuser

EXPOSE 8080
ENTRYPOINT ["/app/app"]
```

**对比效果**：
- 单阶段：`golang:1.22-alpine` 基础 + 工具链 + 源码 + binary = **~500MB**
- 多阶段：仅 `alpine:3.19` + 10MB binary = **~15MB**

### 2.2 Node 多阶段（分离 devDependencies）

```dockerfile
# Stage 1: deps（含 dev deps，用于构建）
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Stage 2: builder
FROM deps AS builder
COPY . .
RUN npm run build      # 产出 dist/

# Stage 3: runtime（不含 dev deps）
FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY package.json package-lock.json ./
RUN npm ci --omit=dev   # 关键：省略 dev 依赖
COPY --from=builder /app/dist ./dist

CMD ["node", "dist/main.js"]
```

### 2.3 常见错误：忘记 `--from=` 阶段名

```dockerfile
# ❌ 错误：拼写错误找不到 stage
COPY --from=buidler /out/app /app   # typo

# ✅ 正确：与 AS 后的别名完全一致
COPY --from=builder /out/app /app
```

## 3. dify 与 ruoyi 源码解读

### 3.1 dify：用多阶段搬运 Python 虚拟环境

**文件位置**：`/Users/xu/code/github/dify/api/Dockerfile`
**核心代码**（行 1-30，97-100）：

```dockerfile
# base image
FROM python:3.12-slim-bookworm AS base

WORKDIR /app/api

# Install uv
ENV UV_VERSION=0.8.9

RUN pip install --no-cache-dir uv==${UV_VERSION}


FROM base AS packages

# if you located in China, you can use aliyun mirror to speed up
# RUN sed -i 's@deb.debian.org@mirrors.aliyun.com@g' /etc/apt/sources.list.d/debian.sources

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
          # basic environment
          git g++ \
          # for building gmpy2
          libmpfr-dev libmpc-dev

# Install Python dependencies (workspace members under providers/vdb/)
COPY api/pyproject.toml api/uv.lock ./
COPY api/providers ./providers
COPY dify-agent/pyproject.toml dify-agent/README.md /app/dify-agent/
COPY dify-agent/src /app/dify-agent/src
# Trust the checked-in lock during image builds; local path sources are copied from the repository context.
RUN uv sync --frozen --no-dev --no-editable
```

**解读**：
- 第 12 行：`FROM base AS packages`——这是第二个 stage，从 `base` 派生
- 第 17-22 行：在 `packages` 阶段安装 `git g++` 和 `libmpfr-dev libmpc-dev`——**只为编译 gmpy2**（Python 包），运行时不需要
- 第 30 行：`uv sync --frozen --no-dev --no-editable`——生成 `.venv` 到 `/app/api/.venv`

**后续阶段引用（行 97-100）**：

```dockerfile
# Copy Python environment and packages
ENV VIRTUAL_ENV=/app/api/.venv
COPY --from=packages --chown=dify:dify ${VIRTUAL_ENV} ${VIRTUAL_ENV}
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
```

- 第 99 行：`COPY --from=packages`——从 packages 阶段**只复制 .venv 目录**，不带 `gcc`、`libmpfr-dev` 等编译工具
- 第 100 行：把 venv 的 `bin` 加入 `PATH`，后续 `python` 命令直接走 venv 解释器

**体积对比**：若不用多阶段，最终镜像需包含 `python:3.12-slim` + `gcc` + `g++` + `uv` = **~600MB**；用了多阶段，只需 `python:3.12-slim` + `.venv` = **~400MB**，省约 **30-40%** 体积。

### 3.2 ruoyi 单阶段 + .dockerignore

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/Dockerfile`
**核心代码**（行 1-23）：

```dockerfile
FROM eclipse-temurin:8-jre

## 创建目录，并使用它作为工作目录
RUN mkdir -p /yudao-server
WORKDIR /yudao-server
## 将后端项目的 Jar 文件，复制到镜像中
COPY ./target/yudao-server.jar app.jar

## 设置 TZ 时区
ENV TZ=Asia/Shanghai

## 暴露后端项目的 48080 端口
EXPOSE 48080

## 启动后端项目
CMD java ${JAVA_OPTS} -jar app.jar $ARGS
```

**解读**：
- 第 3 行：`eclipse-temurin:8-jre`——JRE 镜像，不含 JDK 工具链（单阶段就已经很瘦）
- 第 9 行：`COPY ./target/yudao-server.jar app.jar`——只搬运编译产物，没有源码、`node_modules`、`.idea/` 等

**配合 .dockerignore**（节省构建上下文大小）：

```gitignore
# 一般 ruoyi 项目都有 .dockerignore 排除：
target/
*.iml
.idea/
.vscode/
.git/
.gitignore
README.md
```

**典型体积对比**：
- 单阶段：`temurin-8-jre`（~180MB）+ `yudao-server.jar`（~150MB） ≈ **330MB**
- 若还想进一步瘦身，可用 `eclipse-temurin:8-jre-alpine`（~120MB）≈ **270MB**

**是否值得多阶段？** ruoyi 把 Maven 构建留在外部（Jenkins / GitHub Actions），镜像内只跑 jar。**多阶段**可避免外部编译依赖，但需要额外写一个 `build` stage 用 `maven:3.9-eclipse-temurin-8` 编译——增加构建时间，未必能省很多体积。**这是工程上的取舍**。

## 4. 关键要点总结

- **多阶段 = 多个 `FROM` + 最后阶段 + `COPY --from=`**
- **跨阶段搬运**：只把最终可运行物带到 runtime 阶段
- **Python 多阶段**：分离 `uv` / `gcc` 等构建工具
- **JVM 多阶段**：Maven 与运行时分离，可选
- **构建缓存关键**：放在前一个阶段的稳定文件（依赖清单）
- **size vs speed 权衡**：多阶段减少 size，但 builder 阶段需要更长时间

## 5. 练习题

### 练习 1：基础（必做）

判断以下说法对错：
1. 多阶段构建必须用 3 个 stage（`base` + `builder` + `runtime`）。 ❌
2. `COPY --from=builder` 可以从前一个 stage 复制文件。 ✅
3. 多阶段构建一定会让构建变慢。 ❌（builder 阶段通常被缓存复用）

**参考答案**：见 `solutions/01-multi-stage.md`

### 练习 2：进阶

阅读 dify 的 `/api/Dockerfile`，假设现在要求**减少 50% 镜像体积**，请列出 5 个具体的改造方案（结合多阶段、其他底层镜像、清理缓存等）。

### 练习 3：挑战（选做）

为 `ruoyi-vue-pro/yudao-server/Dockerfile` 加入多阶段：
- Stage 1 (build)：`FROM maven:3.9-eclipse-temurin-8`，`mvn package`
- Stage 2 (runtime)：`FROM eclipse-temurin:8-jre-alpine`，`COPY --from=build target/*.jar`

估算能减少多少体积，是否值得？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/Dockerfile`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/Dockerfile`
- 多阶段构建官方文档：https://docs.docker.com/build/building/multi-stage/
- Docker BuildKit 缓存：https://docs.docker.com/build/cache/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
