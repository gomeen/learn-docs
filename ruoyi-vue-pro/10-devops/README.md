# 10 - DevOps 与部署

> ruoyi-vue-pro 的部署、容器化、CI/CD、监控。

## 🌐 公共部分

| 主题 | 公共文档 | 本项目特定内容 |
|------|---------|--------------|
| Docker 基础 / Dockerfile / Compose | [_common/09-containerization/](../../_common/09-containerization/) | 05-09 章节（Java Docker 实战） |
| Nginx 反向代理 / HTTPS | [_common/10-network-proxy/](../../_common/10-network-proxy/) | 10-12 章节（ruoyi 视角） |
| CI/CD / GitHub Actions / GitLab CI / Jenkins | [_common/11-cicd/](../../_common/11-cicd/) | 14-17 章节（ruoyi 实战） |
| 蓝绿 / 灰度部署 | [_common/12-deploy-strategies/](../../_common/12-deploy-strategies/) | 17-deploy-strategy.md |
| 监控 / Actuator / Prometheus | 暂用 dify 文档 | 18-23 章节（ruoyi 监控） |
| JVM 调优 | Java 专属（01-java-fundamentals/24） | 24-27 章节 |

## 模块 10.1 构建与打包

- [ ] [1.1 Maven 多模块构建](./01-maven-build.md)
- [ ] [1.2 Spring Boot 打包：jar / war](./02-spring-boot-jar.md)
- [ ] [1.3 配置文件外置](./03-external-config.md)
- [ ] [1.4 Profile 多环境构建](./04-profile-build.md)

## 模块 10.2 Docker 容器化

- [ ] [2.1 Java 应用的 Docker 镜像](./05-java-docker.md)
- [ ] [2.2 多阶段构建：减小镜像](./06-multi-stage.md)
- [ ] [2.3 Dockerfile 优化：JVM 镜像](./07-jvm-image.md)
- [ ] [2.4 docker-compose 部署](./08-docker-compose.md)
- [ ] [2.5 ruoyi 的部署脚本](./09-ruoyi-deploy.md)

## 模块 10.3 反向代理与网关

- [ ] [3.1 Nginx 反向代理](./10-nginx-proxy.md)
- [ ] [3.2 HTTPS 配置](./11-https.md)
- [ ] [3.3 负载均衡策略](./12-load-balance.md)
- [ ] [3.4 Spring Cloud Gateway（yudao-cloud）](./13-gateway.md)

## 模块 10.4 CI/CD

- [ ] [4.1 GitHub Actions 实战](./14-github-actions.md)
- [ ] [4.2 GitLab CI 实战](./15-gitlab-ci.md)
- [ ] [4.3 Jenkins 流水线](./16-jenkins.md)
- [ ] [4.4 蓝绿部署 / 灰度发布](./17-deploy-strategy.md)

## 模块 10.5 监控与告警

- [ ] [5.1 Spring Boot Actuator](./18-actuator.md)
- [ ] [5.2 Spring Boot Admin](./19-admin.md)
- [ ] [5.3 Prometheus + Grafana](./20-prometheus.md)
- [ ] [5.4 ELK 日志收集](./21-elk.md)
- [ ] [5.5 SkyWalking 链路追踪](./22-skywalking.md)
- [ ] [5.6 Sentry 错误监控](./23-sentry.md)

## 模块 10.6 性能调优

- [ ] [6.1 JVM 调优：GC 参数](./24-jvm-tuning.md)
- [ ] [6.2 Arthas 线上诊断](./25-arthas.md)
- [ ] [6.3 慢 SQL 分析](./26-slow-sql.md)
- [ ] [6.4 压测：JMeter / Gatling](./27-stress-test.md)

## 🎯 ruoyi-vue-pro 仓库对应位置

- 部署脚本：`/Users/xu/code/github/ruoyi-vue-pro/script/`
- Docker 镜像：搜索 `Dockerfile`
- CI 配置：`.github/workflows/`（如果有）
- 监控：参考 `yudao-framework/yudao-spring-boot-starter-monitor/`
