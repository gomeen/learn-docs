# 3.3 负载均衡策略

> 理解负载均衡的核心策略，掌握 Nginx 的 upstream 配置与 Spring Cloud Gateway 的负载均衡。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 4 层 vs 7 层负载均衡
- 掌握轮询、加权轮询、IP Hash 等策略
- 能在 Nginx 配置多实例负载均衡
- 知道 Spring Cloud Gateway 的负载均衡机制

## 📚 前置知识

- `10-nginx-proxy.md`
- 微服务基本概念

## 1. 核心概念

### 1.1 4 层 vs 7 层负载均衡

| 层级 | 工作位置 | 代表 | 性能 | 灵活性 |
|------|---------|------|------|-------|
| **L4** | 传输层（TCP/UDP） | LVS / HAProxy | 高 | 低（按 IP/端口） |
| **L7** | 应用层（HTTP） | Nginx / Gateway | 中 | 高（按 URL/Header） |

### 1.2 常见负载均衡策略

| 策略 | 原理 | 适用 |
|------|------|------|
| **轮询**（round-robin） | 按顺序分发 | 服务器配置相同 |
| **加权轮询** | 按 weight 比例 | 服务器配置不同 |
| **IP Hash** | `hash(ip) % N` | 需要会话保持 |
| **最少连接** | 谁连接少给谁 | 长连接 |
| **URL Hash** | `hash(url)` | 缓存集群 |
| **random** | 随机 | 大规模集群 |

### 1.3 健康检查

负载均衡器会定期探测后端：
- 失败：自动剔除
- 恢复：自动加入

## 2. 代码示例

### 2.1 Nginx upstream 多策略

```nginx
upstream backend {
    # 1. 轮询（默认）
    server 192.168.1.10:8080;
    server 192.168.1.11:8080;

    # 2. 加权轮询（80% 流量去 1.10）
    server 192.168.1.20:8080 weight=8;
    server 192.168.1.21:8080 weight=2;

    # 3. 备份节点
    server 192.168.1.30:8080 backup;

    # 4. 不可用时踢出
    server 192.168.1.40:8080 down;
}

server {
    listen 80;
    location / {
        # 5. IP Hash（会话保持）
        # ip_hash;  # 取消注释启用

        # 6. 最少连接
        # least_conn;  # 取消注释启用

        proxy_pass http://backend;
    }
}
```

**说明**：
- `weight=N` — 权重越高分到的请求越多
- `backup` — 主节点全挂时启用
- `down` — 永久标记为不可用（用于维护）
- `ip_hash` / `least_conn` — 启用高级策略只需取消注释

### 2.2 Nginx 健康检查（主动）

```nginx
upstream backend {
    server 192.168.1.10:8080;
    server 192.168.1.11:8080;

    # 健康检查（需要 nginx-plus 或开源模块）
    health_check interval=5s fails=3 passes=2 uri=/actuator/health;
}
```

**注**：开源 Nginx 主动健康检查需要 `ngx_http_upstream_check_module`。

## 3. ruoyi 仓库源码解读

**注**：ruoyi 单机部署没有内置负载均衡配置。

### 3.1 yudao-cloud 的微服务架构

ruoyi 的微服务版（yudao-cloud）使用 **Spring Cloud LoadBalancer** + **Spring Cloud Gateway**：

```yaml
# Spring Cloud Gateway 配置示例
spring:
  cloud:
    gateway:
      discovery:
        locator:
          enabled: true    # 开启服务发现
      routes:
        - id: yudao-system
          uri: lb://yudao-system  # lb:// 表示负载均衡
          predicates:
            - Path=/admin-api/system/**
```

**`lb://yudao-system`** 中的 `lb` 是 **LoadBalancer** 缩写，Spring Cloud Gateway 会从 Nacos 注册中心拉取 `yudao-system` 服务实例列表并负载均衡。

### 3.2 推荐的多实例部署（单机伪集群）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`（修改建议）

```yaml
version: "3.4"
name: yudao-cluster

services:
  server-1:
    build: ./yudao-server
    container_name: yudao-server-1
    ports:
      - "48081:48080"
    environment:
      SERVER_PORT: 48080
      SPRING_PROFILES_ACTIVE: local

  server-2:
    build: ./yudao-server
    container_name: yudao-server-2
    ports:
      - "48082:48080"
    environment:
      SERVER_PORT: 48080
      SPRING_PROFILES_ACTIVE: local

  nginx:
    image: nginx:alpine
    container_name: yudao-nginx
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "48080:80"
    depends_on:
      - server-1
      - server-2
```

**配套 nginx.conf**：

```nginx
upstream yudao-cluster {
    server yudao-server-1:48080 weight=1;
    server yudao-server-2:48080 weight=1;
}

server {
    listen 80;
    location / {
        proxy_pass http://yudao-cluster;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**设计意图**：
- 用 Docker 把 2 个 yudao-server 实例跑在同一台机器
- 用 Nginx 负载均衡到两个实例
- 验证集群模式可行性（生产环境用 K8s）

## 4. 关键要点总结

- 4 层负载（LVS）：按 IP/端口，性能高
- 7 层负载（Nginx）：按 URL/Header，功能强
- 常用策略：轮询、加权轮询、IP Hash、最少连接
- ruoyi 单机版用 Nginx 即可实现负载均衡
- ruoyi 微服务版（yudao-cloud）用 Spring Cloud Gateway + LoadBalancer
- 健康检查是负载均衡器的标配

## 5. 练习题

### 练习 1：基础（必做）

本地启动 2 个 yudao-server（端口 48080、48081），配置 Nginx `upstream` 用轮询策略，访问 `http://localhost/admin-api/system/user/get` 观察日志中两个实例轮流响应。

### 练习 2：进阶

修改 Nginx 用 `ip_hash` 策略，连续发 10 个请求，观察是否都路由到同一个后端实例。

### 练习 3：挑战（选做）

把其中一个实例停掉（`docker stop`），配置 Nginx 的 `health_check`，观察 Nginx 是否自动剔除故障实例。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`
- [Nginx upstream 文档](http://nginx.org/en/docs/http/ngx_http_upstream_module.html)
- [Spring Cloud Gateway 文档](https://docs.spring.io/spring-cloud-gateway/docs/current/reference/html/)
- ruoyi 微服务文档：https://doc.iocoder.cn/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
