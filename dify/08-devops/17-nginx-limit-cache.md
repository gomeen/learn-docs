# 3.4 Nginx 限流与缓存

> 学习用 Nginx 实现限流（rate limiting）和缓存（proxy cache），提升服务稳定性。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 `limit_req` / `limit_conn` 实现限流
- 用 `proxy_cache` 配置反向代理缓存
- 理解限流在 dify 这种 LLM 应用中的重要性

## 📚 前置知识

- `08-devops/14-nginx-basics.md`
- `08-devops/15-nginx-proxy.md`

## 1. 核心概念

### 1.1 限流（Rate Limiting）

限流保护后端服务不被突发流量打垮。两种维度：
- **limit_req**：限制**请求速率**（QPS）
- **limit_conn**：限制**并发连接数**

**算法**：Nginx 用**漏桶（Leaky Bucket）**算法，平滑突发流量。

### 1.2 缓存（Proxy Cache）

Nginx 可缓存后端响应，减少后端压力。典型场景：
- 静态资源（CSS / JS / 图片）
- 频繁查询的 API 响应（GET 请求）

### 1.3 缓存在 LLM 应用中的取舍

LLM 应用的响应是**动态、个性化**的（每次 prompt 不同），不适合全量缓存。但可以：
- 缓存**静态前端资源**（`/_next/static/`）
- 缓存**公共数据**（市场列表、用户公开信息）
- 缓存**限流响应**（同一 IP 的同类请求）

## 2. 代码示例

### 2.1 请求限流

```nginx
# 定义限流区域：10MB 状态，每秒 10 个请求
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

server {
    listen 80;
    server_name api.example.com;

    location /api/ {
        # 应用限流：每秒 10 个，突发 20 个
        limit_req zone=api_limit burst=20 nodelay;
        limit_req_status 429;            # 限流时返回 429

        proxy_pass http://backend;
    }
}
```

**关键参数**：
- `rate=10r/s`：每秒 10 个请求
- `burst=20`：允许突发 20 个（队列缓冲）
- `nodelay`：超出 burst 立即拒绝（不排队等待）
- `limit_req_status 429`：标准 HTTP 状态码

### 2.2 并发连接限流

```nginx
# 限制每个 IP 最多 5 个并发连接
limit_conn_zone $binary_remote_addr zone=conn_per_ip:10m;

server {
    limit_conn conn_per_ip 5;
}
```

### 2.3 反向代理缓存

```nginx
# 定义缓存：10MB key 存储，100MB 缓存，1 天过期
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m
                 max_size=100m inactive=24h use_temp_path=off;

server {
    location /api/public {
        proxy_cache api_cache;
        proxy_cache_valid 200 5m;           # 200 响应缓存 5 分钟
        proxy_cache_valid 404 1m;            # 404 缓存 1 分钟
        proxy_cache_key "$scheme$request_uri";
        add_header X-Cache-Status $upstream_cache_status;

        proxy_pass http://backend;
    }
}
```

**`$upstream_cache_status`**：
- `HIT`：命中缓存
- `MISS`：未命中，走了后端
- `BYPASS`：跳过缓存
- `EXPIRED`：缓存已过期
- `STALE`：返回过期内容（后端不可用时）

### 2.4 常见错误：缓存了动态内容

```nginx
# ❌ 错误：缓存 POST 请求（导致数据不一致）
location /api {
    proxy_cache api_cache;
    proxy_pass http://backend;
}

# ✅ 正确：只缓存 GET
location /api {
    proxy_cache api_cache;
    proxy_cache_methods GET HEAD;          # 只缓存 GET/HEAD
    proxy_pass http://backend;
}
```

## 3. dify 仓库源码解读

### 3.1 dify 的 proxy 配置（无内置限流）

**文件位置**：`/Users/xu/code/github/dify/docker/nginx/proxy.conf.template`（参考）

**核心内容**：

```nginx
proxy_http_version 1.1;
proxy_set_header   Host              $http_host;
proxy_set_header   X-Real-IP         $remote_addr;
proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
proxy_set_header   X-Forwarded-Proto $scheme;
proxy_redirect     off;
proxy_buffering    off;
proxy_read_timeout ${NGINX_PROXY_READ_TIMEOUT};
proxy_send_timeout ${NGINX_PROXY_SEND_TIMEOUT};
```

**解读**：
- **dify 默认不启用限流**（生产部署建议根据实际情况加）
- `proxy_buffering off`：**关键**——dify 是流式响应（SSE），关闭缓冲才能实时推送给客户端
- 限流需要在 dify 的 Nginx 配置中**自行添加**

### 3.2 dify 的 LLM 长时间代理超时

**核心代码片段**：

```nginx
proxy_read_timeout ${NGINX_PROXY_READ_TIMEOUT};     # 默认 3600s
proxy_send_timeout ${NGINX_PROXY_SEND_TIMEOUT};     # 默认 3600s
```

**解读**：
- 默认 60s 的 `proxy_read_timeout` 对 LLM 远远不够
- dify 设置为 1 小时，覆盖大多数 LLM 推理场景
- **这是 LLM 应用必须的配置**：Claude / GPT-4 长文本生成可能持续数分钟

### 3.3 dify 的客户端体限制

**文件位置**：`/Users/xu/code/github/dify/docker/nginx/nginx.conf.template`

**核心代码**（行 31）：

```nginx
client_max_body_size ${NGINX_CLIENT_MAX_BODY_SIZE};
```

**解读**：
- 默认 100M，允许上传大型文档（PDF / 视频 / 大数据集）
- `client_max_body_size` 控制请求体大小
- 超过限制返回 413（Request Entity Too Large）
- 调整时也要同步调整 uvicorn/gunicorn 的 `--limit-request-line` 等参数

## 4. 关键要点总结

- **limit_req** 限请求速率，**limit_conn** 限并发连接
- 限流用漏桶算法，平滑突发流量
- **proxy_cache** 用 `proxy_cache_valid` 设置不同状态码的 TTL
- dify 不默认启用限流，需自行配置
- LLM 应用必须设置**长超时**（`proxy_read_timeout 3600s`）
- **不能缓存**流式响应（SSE），`proxy_buffering off` 是关键
- `client_max_body_size` 控制上传体积，配合后端框架调整

## 5. 练习题

### 练习 1：基础（必做）

在本地启动一个 Nginx，对 `/api/` 配置限流 `rate=5r/s burst=10`，用 `ab`（Apache Bench）压测观察 429 响应。

```bash
docker run -d --name nginx -p 8080:80 nginx:1.27
# 配置限流
ab -n 100 -c 10 http://localhost:8080/api/
```

### 练习 2：进阶

阅读 dify `proxy.conf.template`，分析哪些设置对 LLM 流式输出至关重要。如果 `proxy_buffering on` 会发生什么？

### 练习 3：挑战（选做）

为 dify 写一个 `rate-limit.conf`，对 `/v1/chat-messages` 路径限流：每 IP 每分钟最多 60 次（防滥用），超出返回 429 并带 JSON 错误体。

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/nginx/proxy.conf.template`
- `/Users/xu/code/github/dify/docker/nginx/nginx.conf.template`
- `/Users/xu/code/github/dify/docker/docker-compose.yaml`
- Nginx 限流官方文档：http://nginx.org/en/docs/http/ngx_http_limit_req_module.html
- Nginx 缓存官方文档：http://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_cache

---

**文档版本**：v1.0
**最后更新**：2026-07-13
