# 5.1 Terraform 入门

> 学会用 Terraform 声明式管理云资源（基础设施即代码），理解 IaC 核心思想。

> ⚠️ **dify 中暂未直接使用 Terraform**。本文档基于通用 Terraform 概念讲解。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Terraform 三大概念：provider / resource / state
- 编写 `.tf` 文件声明 AWS / 阿里云资源
- 理解 Terraform 与 Ansible 的差异

## 📚 前置知识

- `08-devops/04-docker-compose.md`
- 云服务基础（EC2 / RDS / VPC 等）

## 1. 核心概念

### 1.1 Terraform 是什么？

Terraform 是 HashiCorp 开发的**基础设施即代码（IaC）**工具。用声明式 HCL 语言定义云资源，自动管理云平台 API。

### 1.2 核心概念

- **Provider**：云服务插件（AWS / 阿里云 / GCP）
- **Resource**：声明一个云资源（VM、RDS、VPC）
- **State**：当前资源的状态（存储在本地或 S3）
- **Plan**：执行前预览变更
- **Apply**：实际执行变更
- **Module**：可复用的资源集合

### 1.3 三大工作流

```bash
terraform init     # 初始化（下载 provider）
terraform plan     # 预览（不实际执行）
terraform apply    # 应用变更
terraform destroy  # 销毁
```

### 1.4 Terraform vs Ansible

| 维度 | Terraform | Ansible |
|------|-----------|---------|
| 范式 | 声明式 | 命令式 |
| 关注 | 资源生命周期 | 配置管理 |
| 顺序 | 无序（并行） | 有序（playbook） |
| 状态 | 维护 state 文件 | 无状态 |
| 适用 | 云资源创建 | 软件部署/配置 |

## 2. 代码示例

### 2.1 第一个 Terraform 配置

```hcl
# 文件：main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"

  tags = {
    Name = "dify-web"
  }
}
```

```bash
terraform init
terraform plan
terraform apply
```

### 2.2 变量与输出

```hcl
# variables.tf
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "environment" {
  type    = string
  default = "dev"
}

# main.tf
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = var.instance_type
  tags = {
    Env = var.environment
  }
}

# outputs.tf
output "instance_ip" {
  value = aws_instance.web.public_ip
}
```

```bash
terraform apply -var="instance_type=t3.medium"
```

### 2.3 模块化

```hcl
# modules/dify/main.tf
resource "aws_instance" "api" { ... }
resource "aws_db_instance" "postgres" { ... }
resource "aws_s3_bucket" "storage" { ... }

# root main.tf
module "dify_prod" {
  source      = "./modules/dify"
  environment = "prod"
  instance_type = "t3.large"
}

module "dify_dev" {
  source      = "./modules/dify"
  environment = "dev"
  instance_type = "t3.micro"
}
```

### 2.4 常见错误：state 冲突

```bash
# ❌ 错误：两人同时 apply，state 冲突
# 解决：把 state 存到 S3 + DynamoDB 锁
terraform {
  backend "s3" {
    bucket         = "my-tf-state"
    key            = "dify/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "my-tf-lock"
    encrypt        = true
  }
}
```

## 3. dify 仓库源码解读

### 3.1 dify 主仓库的 Terraform 使用

**说明**：dify 主仓库**没有** `.tf` 文件（不直接管理云基础设施）。

但根据 dify 的部署模式，可用 Terraform 创建**部署 dify 的基础设施**：

### 3.2 假想的 dify 部署 Terraform

```hcl
# 假想：main.tf（部署 dify 的基础设施）
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC
resource "aws_vpc" "dify_vpc" {
  cidr_block = "10.0.0.0/16"
  tags = {
    Name = "dify-vpc"
  }
}

# EC2 用于运行 docker-compose
resource "aws_instance" "dify_host" {
  ami           = "ami-0c55b159cbfafe1f0"   # Ubuntu 22.04
  instance_type = "t3.large"
  vpc_security_group_ids = [aws_security_group.dify_sg.id]
  user_data = file("user-data.sh")             # 启动时安装 Docker

  tags = {
    Name = "dify-host"
  }
}

# RDS for PostgreSQL
resource "aws_db_instance" "dify_db" {
  engine                = "postgres"
  engine_version        = "15.4"
  instance_class        = "db.t3.micro"
  allocated_storage     = 20
  db_name               = "dify"
  username              = var.db_username
  password              = var.db_password
  skip_final_snapshot   = true

  tags = {
    Name = "dify-db"
  }
}

# S3 用于存储
resource "aws_s3_bucket" "dify_storage" {
  bucket = "dify-storage-${var.environment}"
}

# 安全组
resource "aws_security_group" "dify_sg" {
  name_prefix = "dify-"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

### 3.3 dify 的部署方式对照

**dify 部署的三种模式**：

| 模式 | 工具 | 适用 |
|------|------|------|
| **单机自托管** | docker-compose | 个人/小团队 |
| **企业自托管** | docker-compose + Ansible | 中等规模 |
| **云端 SaaS** | K8s + Terraform | 大规模 |

- **Terraform** 适合大规模云端部署（创建 VPC/EC2/RDS/S3 等基础设施）
- **Ansible** 适合在已有的服务器上部署软件（安装 Docker、配置 compose）
- **docker-compose** 适合单机自托管

### 3.4 dify 的 cloud 部署

dify 官方也提供 **Dify Cloud**（SaaS），用 Terraform 管理底层云资源（**这部分代码不开源**）。

## 4. 关键要点总结

- Terraform = **IaC 工具**，用 HCL 声明式定义云资源
- 三大命令：`init` / `plan` / `apply`
- **State** 是关键——必须妥善管理（推荐 S3 + DynamoDB）
- Terraform 适合**基础设施层**（VPC、EC2、RDS）
- Ansible 适合**配置管理层**（软件安装、配置）
- dify 主仓库暂未使用 Terraform，但企业版部署可结合使用

## 5. 练习题

### 练习 1：基础（必做）

用 Terraform 创建一个 AWS EC2 实例（t3.micro，Ubuntu 22.04），输出公网 IP，ssh 进去确认实例存在。

```bash
terraform init && terraform apply
ssh ubuntu@$(terraform output -raw instance_ip)
```

### 练习 2：进阶

把 dify 的部署抽象为 Terraform module：包含 EC2（运行 docker-compose）+ RDS（PostgreSQL）+ S3（存储），用变量控制环境（dev/prod）。

### 练习 3：挑战（选做）

为 dify 设计完整的云端部署：用 Terraform 创建基础设施（VPC/EC2/RDS/S3），用 Ansible 在 EC2 上安装 Docker 并启动 docker-compose，结合 `terraform apply` + `ansible-playbook` 一键部署。

## 6. 参考资料

- Terraform 官方文档：https://developer.hashicorp.com/terraform
- AWS Provider 文档：https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- dify 部署文档：https://docs.dify.ai/getting-started/install-self-hosted/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
