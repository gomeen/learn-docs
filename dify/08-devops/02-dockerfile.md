# 1.2 Dockerfile 编写最佳实践

> 学习编写高质量 Dockerfile，能读懂并修改 dify 的 `api/Dockerfile`。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 Dockerfile 的常用指令：`FROM`/`COPY`/`RUN`/`ENV`/`WORKDIR`/`USER`/`ENTRYPOINT`
- 写出可缓存、镜像小、安全性高的 Dockerfile
- 能读懂 dify 的 `api/Dockerfile` 中的多阶段构建与非 root 用户设置

## 📚 前置知识

- `08-devops/01-docker-concepts.md`

## 1. 核心概念

### 1.1 Dockerfile 是什么？

Dockerfile 是一个**构建镜像的脚本**，每条指令产生一个镜像层（Layer）。

### 1.2 常用指令

| 指令 | 作用 | 示例 |
|------|------|------|
| `FROM` | 基础镜像 | `FROM python:3.12-slim` |
| `WORKDIR` | 切换工作目录 | `WORKDIR /app` |
| `COPY` | 复制文件到镜像 | `COPY . .` |
| `ADD` | 复制文件（支持 URL/解压） | `ADD app.tar.gz /app` |
| `RUN` | 执行命令 | `RUN pip install flask` |
| `ENV` | 设置环境变量 | `ENV TZ=UTC` |
| `EXPOSE` | 声明端口 | `EXPOSE 5001` |
| `USER` | 切换用户 | `USER dify` |
| `ENTRYPOINT` | 入口点 | `ENTRYPOINT ["/entrypoint.sh"]` |
| `CMD` | 默认命令 | `CMD ["python", "app.py"]` |

### 1.3 关键原则

1. **顺序很重要**：把**不常变动的层**放前面（基础镜像、系统包），**常变的层**放后面（应用代码），最大化缓存命中。
2. **合并 RUN 指令**：每个 `RUN` 产生一层，多个命令合并可减少层数和最终镜像体积。
3. **使用 `.dockerignore`**：避免把 `node_modules`、`.git`、敏感配置等打入镜像。
4. **多阶段构建**：构建阶段用大镜像（含编译器），运行阶段只拷贝产物，镜像更小。
5. **非 root 用户**：默认以 root 运行有安全风险，应创建专用用户。

### 1.4 缓存机制

Docker 构建按**指令顺序**逐层执行，每层会与缓存比对：
- 指令相同 + 上层内容相同 → 命中缓存，跳过执行
- 任一指令变更 → 该层及其后所有层失效

**典型优化**：先 `COPY` 依赖清单 + `RUN pip install`，再 `COPY` 业务代码。这样只改代码时不必重装依赖。

## 2. 代码示例

### 2.1 反例：不规范的 Dockerfile

```dockerfile
# ❌ 反例：缓存利用差、镜像大、root 运行
FROM python:3.12

COPY . /app                      # 改一行代码也触发 pip 重新安装
WORKDIR /app
RUN pip install flask
RUN pip install requests
RUN pip install sqlalchemy

CMD python app.py                # root 权限运行
```

### 2.2 正例：优化后的 Dockerfile

```dockerfile
# ✅ 正例：缓存友好、镜像小、非 root
FROM python:3.12-slim            # 1. 用 slim 镜像（~150MB vs ~1GB）

WORKDIR /app

# 2. 先 COPY 依赖清单
COPY requirements.txt .

# 3. 安装依赖（合并为一条 RUN，清理 apt 缓存）
RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache

# 4. 最后 COPY 业务代码（缓存友好）
COPY . .

# 5. 创建非 root 用户
RUN useradd -m -u 1001 appuser
USER appuser

EXPOSE 5000
CMD ["python", "app.py"]
```

### 2.3 常见错误：`ADD` vs `COPY`

```dockerfile
# ❌ 错误：用 ADD 下载远程文件（无校验、缓存差）
ADD https://example.com/big.tar.gz /tmp/

# ✅ 正确：用 RUN + curl，或本地 ADD
RUN curl -fsSL https://example.com/big.tar.gz -o /tmp/big.tar.gz \
    && sha256sum /tmp/big.tar.gz | grep "expected_hash" \
    && tar -xzf /tmp/big.tar.gz -C /opt/
```

## 3. dify 仓库源码解读

### 3.1 dify API 的多阶段构建

**文件位置**：`/Users/xu/code/github/dify/api/Dockerfile`
**核心代码**（行 1-32）：

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
- 第 2 行：`AS base` 命名阶段，`slim-bookworm` 比完整 Debian 镜像小 70%+
- 第 6 行：先安装 `uv`（现代 Python 包管理器），后续 `uv sync` 速度比 `pip install` 快 10-100 倍
- 第 13 行：`FROM base AS packages` 第二个阶段专门用于**编译/安装 Python 依赖**
- 第 22 行：合并多条 `apt-get install` 为一条 RUN，并用 `--no-install-recommends` 减少无关包
- 第 25-30 行：分阶段 COPY，先只复制 `pyproject.toml` + `uv.lock`（变更少），最大化缓存命中
- 第 31 行：`uv sync --frozen --no-dev` 用 lock 文件精确安装，不装开发依赖，镜像更小

### 3.2 生产阶段的非 root 用户与入口点

**文件位置**：`/Users/xu/code/github/dify/api/Dockerfile`
**核心代码**（行 33-65）：

```dockerfile
# production stage
FROM base AS production

ENV FLASK_APP=app.py
ENV EDITION=SELF_HOSTED
ENV DEPLOY_ENV=PRODUCTION

EXPOSE 5001

# set timezone
ENV TZ=UTC

# Create non-root user
ARG dify_uid=1001
ARG NODE_MAJOR=22
RUN groupadd -r -g ${dify_uid} dify && \
    useradd -r -u ${dify_uid} -g ${dify_uid} -s /bin/bash dify && \
    chown -R dify:dify /app
```

**解读**：
- 第 2 行：`FROM base AS production` 第三个阶段，复用 base 但不继承 `packages` 阶段的大依赖
- 第 4-7 行：用 `ENV` 设置运行时常量，**构建期和运行期都能用**
- 第 14 行：`ARG dify_uid=1001` 用 ARG 声明构建参数（默认值 1001），可在 `docker build --build-arg dify_uid=2000 .` 覆盖
- 第 17-19 行：创建 `dify` 用户和组（`groupadd` + `useradd`），后续 `USER dify` 切换

## 4. 关键要点总结

- 指令顺序决定缓存效率，**依赖在前、代码在后**
- 合并 `RUN` 指令并清理缓存，减小镜像体积
- 用 `slim` / `alpine` 基础镜像，多阶段构建
- 用 `USER` 切换非 root 用户提升安全性
- dify 用 `uv` 而非 `pip`，构建速度快
- dify 三个构建阶段：`base`（共用基础）→ `packages`（装依赖）→ `production`（运行镜像）

## 5. 练习题

### 练习 1：基础（必做）

写一个简单的 Python Flask 应用的 Dockerfile，要求：
- 用 `python:3.12-slim` 基础镜像
- 先 COPY `requirements.txt` 再 `pip install`
- 创建非 root 用户
- 暴露 5000 端口

### 练习 2：进阶

阅读 dify `api/Dockerfile`，解释为什么 `packages` 阶段和 `production` 阶段要分开？直接把 `uv sync` 放在 production 阶段会有什么问题？

### 练习 3：挑战（选做）

为 dify 的 Web 应用写一个多阶段 Dockerfile，参考 `web/Dockerfile` 但加上 `.dockerignore`，比较前后 `docker build` 输出镜像大小。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/Dockerfile`
- `/Users/xu/code/github/dify/web/Dockerfile`
- Docker 官方最佳实践：https://docs.docker.com/develop/develop-images/dockerfile_best-practices/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
