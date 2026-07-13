# 5.2 Ansible 入门

> 学会用 Ansible 自动化服务器配置，能在多台机器上批量部署 dify。

> ⚠️ **dify 中暂未直接使用 Ansible**。本文档基于通用 Ansible 概念讲解。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Ansible 核心概念：inventory / playbook / role / task
- 编写 playbook 自动化部署
- 理解 Ansible 与 Terraform 的差异

## 📚 前置知识

- `08-devops/24-terraform.md`（Terraform 入门）
- SSH 基础

## 1. 核心概念

### 1.1 Ansible 是什么？

Ansible 是 Red Hat 维护的**配置管理工具**，用 YAML 编写 playbook，通过 SSH 在远程主机上执行任务。

### 1.2 核心概念

- **Inventory**：主机清单（要管理哪些机器）
- **Playbook**：YAML 格式的任务脚本
- **Task**：单个任务（如安装包、复制文件）
- **Module**：可复用的功能单元（apt、copy、service）
- **Role**：模块化的任务集合
- **Handler**：仅在变更时触发的任务（重启服务）

### 1.3 工作原理

```
控制节点（Ansible）
  │
  │ SSH
  ├──→ 节点 1（被管理主机）
  ├──→ 节点 2（被管理主机）
  └──→ 节点 3（被管理主机）
```

- **无代理**（agentless）：通过 SSH 通信
- **幂等性**：可重复执行，结果一致
- **顺序执行**：playbook 按顺序执行 task

### 1.4 Ansible vs Terraform

| 维度 | Terraform | Ansible |
|------|-----------|---------|
| 关注 | 创建/销毁云资源 | 配置/部署软件 |
| 状态 | 有 state 文件 | 无状态 |
| 协议 | Cloud API | SSH |
| 语言 | HCL | YAML |
| 适用 | 基础设施层 | 应用层 |

## 2. 代码示例

### 2.1 Inventory

```ini
# 文件：inventory.ini
[dify]
web1 ansible_host=10.0.1.10
web2 ansible_host=10.0.1.11
worker1 ansible_host=10.0.1.20

[db]
postgres1 ansible_host=10.0.2.10

[all:vars]
ansible_user=ubuntu
ansible_ssh_private_key_file=~/.ssh/id_rsa
```

### 2.2 第一个 Playbook

```yaml
# 文件：playbook.yml
- name: Install Docker on all hosts
  hosts: all
  become: true                     # sudo
  tasks:
    - name: Update apt
      apt:
        update_cache: yes

    - name: Install Docker
      apt:
        name: docker.io
        state: present

    - name: Ensure Docker is running
      service:
        name: docker
        state: started
        enabled: yes
```

```bash
ansible-playbook -i inventory.ini playbook.yml
```

### 2.3 部署 dify

```yaml
# 文件：deploy-dify.yml
- name: Deploy dify with docker-compose
  hosts: dify
  become: true
  vars:
    dify_version: "1.16.0-rc1"
    dify_dir: "/opt/dify"

  tasks:
    - name: Ensure docker-compose is installed
      apt:
        name: docker-compose-plugin
        state: present

    - name: Clone dify repository
      git:
        repo: https://github.com/langgenius/dify.git
        dest: "{{ dify_dir }}"
        version: "{{ dify_version }}"

    - name: Copy .env file
      template:
        src: .env.j2
        dest: "{{ dify_dir }}/docker/.env"

    - name: Start dify
      community.docker.docker_compose_v2:
        project_src: "{{ dify_dir }}/docker"
        state: present
        profiles:
          - postgresql
      notify: Restart dify

  handlers:
    - name: Restart dify
      community.docker.docker_compose_v2:
        project_src: "{{ dify_dir }}/docker"
        state: restarted
        profiles:
          - postgresql
```

### 2.4 Role 模块化

```
roles/
└── dify/
    ├── tasks/main.yml
    ├── handlers/main.yml
    ├── templates/.env.j2
    ├── vars/main.yml
    └── defaults/main.yml
```

```yaml
# roles/dify/tasks/main.yml
- name: Install Docker
  apt:
    name: docker.io
    state: present

- name: Clone dify
  git:
    repo: https://github.com/langgenius/dify.git
    dest: /opt/dify
```

```yaml
# site.yml
- name: Deploy dify
  hosts: all
  roles:
    - common
    - dify
```

### 2.5 常见错误：忘记 `become: true`

```yaml
# ❌ 错误：apt 安装需要 root 权限
- name: Install Docker
  apt:
    name: docker.io
# 报错：Permission denied

# ✅ 正确：提升权限
- name: Install Docker
  apt:
    name: docker.io
  become: true
```

## 3. dify 仓库源码解读

### 3.1 dify 主仓库的 Ansible 使用

**说明**：dify 主仓库**没有** Ansible playbook。

但 Ansible 是 dify 自托管部署的**推荐工具**之一：

### 3.2 假想的 dify Ansible Role

```yaml
# roles/dify/tasks/main.yml
---
- name: Install required packages
  apt:
    name:
      - docker.io
      - docker-compose-plugin
      - git
      - curl
    state: present
    update_cache: yes

- name: Create dify directory
  file:
    path: /opt/dify
    state: directory
    owner: ubuntu
    group: ubuntu

- name: Clone dify repository
  git:
    repo: https://github.com/langgenius/dify.git
    dest: /opt/dify
    version: "1.16.0-rc1"
    force: no

- name: Copy .env from template
  template:
    src: .env.j2
    dest: /opt/dify/docker/.env
    owner: ubuntu
    group: ubuntu
    mode: '0600'                  # 敏感文件仅所有者可读

- name: Pull docker images
  community.docker.docker_compose_v2:
    project_src: /opt/dify/docker
    pull: always
    profiles:
      - postgresql

- name: Start dify
  community.docker.docker_compose_v2:
    project_src: /opt/dify/docker
    state: present
    profiles:
      - postgresql

- name: Wait for dify to be ready
  uri:
    url: http://localhost/install
    status_code: 200
  register: result
  until: result.status == 200
  retries: 30
  delay: 10
```

### 3.3 假想的 Inventory

```ini
# inventory/production
[dify_workers]
dify-web-1 ansible_host=10.0.1.10
dify-web-2 ansible_host=10.0.1.11

[db_servers]
dify-db-1 ansible_host=10.0.2.10

[vector_db]
dify-weaviate-1 ansible_host=10.0.3.10

[all:vars]
ansible_user=ubuntu
ansible_ssh_private_key_file=~/.ssh/dify-prod.pem
ansible_python_interpreter=/usr/bin/python3
```

### 3.4 部署策略对照

**dify 部署的三种自动化模式**：

| 模式 | 工具组合 | 适用 |
|------|----------|------|
| **单机** | docker-compose | 1 台机器，最简单 |
| **多机** | Ansible + docker-compose | 3-5 台机器，中等规模 |
| **大规模** | Terraform + Ansible + K8s | 10+ 台机器，企业级 |

**典型组合**：
- Terraform：创建 EC2/VPC/RDS（基础设施）
- Ansible：在 EC2 上安装 Docker、配置（应用层）
- docker-compose：启动 dify 容器（应用运行时）
- K8s：大规模编排（可选）

### 3.5 实际参考：dify 的官方部署建议

参考 dify 官方文档（不在主仓库）：

> - 单机：`docker compose up -d` 一行命令
> - 集群：用 Kubernetes（参考社区 Helm Chart）
> - 自动化：用 Ansible/Terraform 自定义

## 4. 关键要点总结

- Ansible = **配置管理工具**，用 YAML 编写 playbook
- **无代理**（agentless），通过 SSH 通信
- **幂等性**：重复执行结果一致
- Inventory / Playbook / Role / Module 四大概念
- Ansible 适合**应用层配置**（安装、配置、启动）
- Terraform 适合**基础设施层**（创建云资源）
- dify 主仓库暂未使用 Ansible，但**企业部署常用**

## 5. 练习题

### 练习 1：基础（必做）

用 Ansible 在本地（localhost）安装 Docker，运行 `ansible -m setup localhost` 验证连接，`ansible-playbook` 安装 nginx。

### 练习 2：进阶

编写一个 Ansible playbook：用 `community.docker.docker_compose_v2` 模块在 3 台机器上部署 dify（--profile postgresql），验证健康检查通过。

### 练习 3：挑战（选做）

为 dify 设计完整的 Ansible role：包含 install（装 Docker）、configure（配置 .env）、deploy（启动 compose）、verify（健康检查）四个 task，封装为可复用 role，支持多环境（dev/staging/prod）。

## 6. 参考资料

- Ansible 官方文档：https://docs.ansible.com/
- Ansible docker_compose_v2 模块：https://docs.ansible.com/ansible/latest/collections/community/docker/docker_compose_v2_module.html
- dify 官方部署文档：https://docs.dify.ai/getting-started/install-self-hosted/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
