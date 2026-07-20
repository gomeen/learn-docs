# Phase 0 — Docker 与运行时

← [索引](../LEARNING-PLAN.md) · [使用说明](./00-guide.md) · 下一阶段 → [Phase 1](./phase-1-python-map.md)

**量级：** 1–2 个有效周 · **入学：** 有 `dify` 仓库  
**源码根：** `/Users/xu/code/github/dify`（下文 `dify/`）

---

## 目标

稳定「compose 起来 → 能打开并登录控制台」，并理解**每个核心容器干什么**，而不是只会复制启动命令。

### 学完应能讲清（口述提纲）

1. 浏览器访问的是哪个端口、谁在听（通常是 nginx）  
2. 一次打开控制台的大致路径：浏览器 → nginx → web / api  
3. `api` 和 `worker` 分别干什么；停掉其中一个，页面会怎样  
4. 配置从哪来（`.env`），密钥为什么不进 git  
5. 出问题你先看 `ps` 还是 `logs`，怎么区分 502 和 API 自己 500  

---

## 必读（按序）

1. [`../../_common/09-containerization/01-concepts.md`](../../_common/09-containerization/01-concepts.md) — 镜像 vs 容器  
2. [`../../_common/09-containerization/04-compose.md`](../../_common/09-containerization/04-compose.md) — Compose  
3. [`../../_common/09-containerization/05-network-volume.md`](../../_common/09-containerization/05-network-volume.md) — 网络与卷  
4. [`../../_common/10-network-proxy/02-reverse-proxy.md`](../../_common/10-network-proxy/02-reverse-proxy.md) — 反代  
5. [`../../_common/17-config/02-env-vars.md`](../../_common/17-config/02-env-vars.md) — 环境变量  
6. [`../08-devops/01-dify-docker.md`](../08-devops/01-dify-docker.md) — Dify Docker（**与下文冲突时以 compose / 上游 README 为准**）  
7. 上游：`dify/docker/README.md`（部署步骤真源）

**卡壳再读：** [`02-dockerfile.md`](../../_common/09-containerization/02-dockerfile.md)  
**延后：** multi-stage 深挖、K8s、全套 CI、Certbot/HTTPS 生产加固  

---

## 上手操作（照着做）

> 在 `dify/docker` 目录下执行。若你已有在跑的栈，从 **步骤 3** 开始验收即可。

### 步骤 1 — 环境文件

```bash
cd /Users/xu/code/github/dify/docker
cp -n .env.example .env   # 已有 .env 则跳过，避免覆盖
# 用编辑器打开 .env：扫一眼 DB / REDIS / 端口相关变量，先不深改
```

可选高级配置在 `envs/*.env.example`；默认能起就先不动。

### 步骤 2 — 启动与状态

```bash
docker compose up -d
docker compose ps
```

关注：

- 状态是否 `running` / `healthy`（名称因版本而异）  
- 宿主端口：默认 nginx 常映射 **`${EXPOSE_NGINX_PORT:-80}` → 容器 80**（见 compose 里 `nginx` 的 `ports`）  

浏览器打开（端口以你 `.env` 为准）：

- 常见：`http://localhost` 或 `http://localhost:<EXPOSE_NGINX_PORT>`  
- 完成首次 setup / 登录控制台  

### 步骤 3 — 日志与进容器（必会）

```bash
# 只跟某一个服务（名字以 ps 输出为准）
docker compose logs -f api --tail=100
docker compose logs -f nginx --tail=50
docker compose logs -f worker --tail=50

# 进 api 容器看一眼进程/文件（镜像内路径因版本可能不同）
docker compose exec api sh -c "pwd; ls"
```

Ctrl+C 只停日志跟随，不停容器。

### 步骤 4 — 故意搞坏一次（毕业要求）

任选其一，**做完要恢复**：

**A. 停 API**

```bash
docker compose stop api
# 浏览器刷新控制台 / 调任意会打后端的操作
# 预期：页面在，但接口失败或 502/网关错误类现象
docker compose logs nginx --tail=30
docker compose start api
```

**B. 看端口占用（本机）**

```bash
# macOS 示例：看谁占用 80（或你的 EXPOSE 端口）
lsof -nP -iTCP:80 -sTCP:LISTEN
```

### 步骤 5 — 拓扑笔记（必须落盘）

用文本或图画一版，至少包含：

```text
浏览器
  → nginx (:80 或你的端口)
      → web（静态前端，本阶段不读源码）
      → api（HTTP API）
      → api_websocket（若启用）
  api / worker
      → db（postgres 等）
      → redis
      → 向量库（仅你启用的一个）
  worker_beat → 定时触发 → worker
```

保存到你自己的笔记；路径可记在 [`progress.md`](./progress.md) 备注里。

---

## 源码 / 配置入口

| 用途 | 路径 |
|------|------|
| 主编排 | `dify/docker/docker-compose.yaml` |
| 本地配置 | `dify/docker/.env`（由 `.env.example` 复制） |
| 可选分组 env | `dify/docker/envs/` |
| nginx 模板 | `dify/docker/nginx/` |
| API 镜像 | `dify/api/Dockerfile` |
| API 进程入口 | `dify/api/app.py`、`app_factory.py` |
| Worker 入口 | `dify/api/celery_entrypoint.py` |

**本阶段读源码的深度：** 只确认「入口文件存在、compose 里 command/image 指向谁」；不跟业务逻辑。

---

## 服务职责表（优先搞懂）

以你实际 `docker compose ps` 为准：

| 服务 | 一句话 | 挂了时你可能看到 |
|------|--------|------------------|
| `nginx` | 入口反代，对外端口 | 整站打不开 |
| `web` | 前端静态资源 | 白屏/静态 404；API 可能仍通 |
| `api` | 后端 HTTP | 登录/接口失败；nginx 可能 502 |
| `api_websocket` | WS 相关 | 实时能力异常 |
| `worker` | Celery 异步任务 | 同步接口或可，索引/后台任务积压 |
| `worker_beat` | 定时调度 | 周期任务不跑 |
| `db_*` | 主库 | API 疯狂报 DB 连接错误 |
| `redis` | 缓存/队列等 | 登录限流、队列、部分缓存异常 |
| 向量库（一个） | 检索存储 | 知识库相关失败（Phase 4 再深挖） |
| `sandbox` / `ssrf_proxy` / `plugin_daemon` | 安全执行 / 出站 / 插件 | 先记名字，细节后置 |

---

## 常见卡点

| 现象 | 先查 | 常见原因 |
|------|------|----------|
| `compose up` 端口被占用 | `lsof` / 改 `.env` 的 `EXPOSE_NGINX_PORT` | 本机 80 已被占用 |
| 页面 502 Bad Gateway | `logs nginx` + `ps api` | api 未就绪或已退出 |
| 页面开了但登录一直转圈/失败 | `logs api` | DB/redis 未好、迁移中、账号/setup 未完成 |
| `ps` 里服务反复重启 | 该服务 `logs` | env 配错、依赖服务未起、健康检查失败 |
| 改了 `.env` 不生效 | 是否重建/重启对应服务 | 仅改文件未 `up -d` 或需 recreate |
| 不知道请求有没有进后端 | 浏览器 Network + `logs api -f` | 请求是否打到 nginx 同一 host |

---

## 本周目标模板

- [ ] 完成「上手操作」步骤 1–5  
- [ ] `compose ps`：每个 **Up** 服务能说一句职责  
- [ ] 会用 `logs -f`、`exec`  
- [ ] 完成一次「故意搞坏 + 恢复」并写下现象  
- [ ] 拓扑图已保存  
- [ ] 知道密钥在 `.env`，不把含密钥的 `.env` 提交 git  

---

## 毕业验收（全勾 → Phase 1）

- [ ] 闭卷口述：nginx / api / worker / db / redis / web  
- [ ] 能判断：nginx 通但 api 未就绪（结合你做过的故障演练）  
- [ ] 控制台可打开并登录（或完成等价 setup）  
- [ ] 笔记里有拓扑图 + 你本机实际端口  

进度总表：[`progress.md`](./progress.md)
