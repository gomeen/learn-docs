# 08 - DevOps 与部署

> 后端系统必须能稳定部署运行。本分类涵盖容器化、编排、CI/CD。

## 🌐 公共部分

| 主题 | 公共文档 | 本项目特定内容 |
|------|---------|--------------|
| Docker 基础 / Dockerfile / Compose | [_common/09-containerization/](../../_common/09-containerization/) | 07-dify-docker.md（dify 全家桶） |
| K8s 核心 | [_common/09-containerization/](../../_common/09-containerization/) | 08-13 章节（K8s 完整） |
| Nginx 反向代理 / HTTPS | [_common/10-network-proxy/](../../_common/10-network-proxy/) | 14-17 章节（dify 实战） |
| CI/CD 概念 / GitHub Actions / GitLab CI | [_common/11-cicd/](../../_common/11-cicd/) | 18-21 章节（dify 实战） |
| 蓝绿 / 灰度部署 | [_common/12-deploy-strategies/](../../_common/12-deploy-strategies/) | 22-deployment-strategies.md |
| Terraform / Ansible | [_common/11-cicd/](../../_common/11-cicd/) | 24-25 章节（IaC） |

## 前置依赖

- `01-fundamentals` 中的 Linux/Shell 基础

## 模块 8.1 Docker 容器化

- [ ] [1.1 Docker 核心概念：镜像、容器、层](./01-docker-concepts.md)
- [ ] [1.2 Dockerfile 编写最佳实践](./02-dockerfile.md)
- [ ] [1.3 多阶段构建：减小镜像体积](./03-multi-stage-build.md)
- [ ] [1.4 Docker Compose：本地多容器编排](./04-docker-compose.md)
- [ ] [1.5 Docker 网络：bridge / host / overlay](./05-docker-network.md)
- [ ] [1.6 Docker 卷与数据持久化](./06-docker-volume.md)
- [ ] [1.7 dify 的 Docker Compose 全家桶分析](./07-dify-docker.md)

## 模块 8.2 Kubernetes 编排

- [ ] [2.1 K8s 核心概念：Pod / Deployment / Service](./08-k8s-concepts.md)
- [ ] [2.2 K8s 工作负载：Deployment / StatefulSet / DaemonSet](./09-k8s-workloads.md)
- [ ] [2.3 K8s 网络：Service / Ingress / NetworkPolicy](./10-k8s-network.md)
- [ ] [2.4 ConfigMap 与 Secret](./11-k8s-configmap.md)
- [ ] [2.5 K8s 持久化存储：PV / PVC](./12-k8s-storage.md)
- [ ] [2.6 Helm Chart 入门](./13-helm.md)

## 模块 8.3 反向代理与负载均衡

- [ ] [3.1 Nginx 基础：配置文件与虚拟主机](./14-nginx-basics.md)
- [ ] [3.2 Nginx 反向代理与负载均衡](./15-nginx-proxy.md)
- [ ] [3.3 HTTPS 配置：TLS 证书与 Let's Encrypt](./16-nginx-https.md)
- [ ] [3.4 Nginx 限流与缓存](./17-nginx-limit-cache.md)

## 模块 8.4 CI/CD 持续集成与部署

- [ ] [4.1 CI/CD 概念与流水线设计](./18-cicd-concepts.md)
- [ ] [4.2 GitHub Actions 实战](./19-github-actions.md)
- [ ] [4.3 GitLab CI 入门](./20-gitlab-ci.md)
- [ ] [4.4 自动化测试与构建流水线](./21-ci-pipeline.md)
- [ ] [4.5 蓝绿部署 / 灰度发布 / 金丝雀](./22-deployment-strategies.md)
- [ ] [4.6 dify 的 CI/CD 配置分析（`.github/workflows/`）](./23-cicd-in-dify.md)

## 模块 8.5 基础设施即代码

- [ ] [5.1 Terraform 入门](./24-terraform.md)
- [ ] [5.2 Ansible 入门](./25-ansible.md)

## 🎯 dify 仓库对应位置

- Docker 配置：`/Users/xu/code/github/dify/docker/`
- docker-compose：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
- Dockerfile：`/Users/xu/code/github/dify/docker/api/Dockerfile`
- CI 工作流：`/Users/xu/code/github/dify/.github/workflows/`
- 部署文档：`/Users/xu/code/github/dify/deploy/`
