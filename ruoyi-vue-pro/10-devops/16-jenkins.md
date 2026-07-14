# 4.3 Jenkins 流水线

> 深入理解 Jenkins Pipeline，掌握 ruoyi 仓库内置的 Jenkinsfile 实战配置。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Jenkins Pipeline 的两种语法（声明式 / 脚本式）
- 掌握 Jenkinsfile 的编写
- 能独立搭建 ruoyi 的 CI/CD 流水线
- 知道凭证管理与多环境部署技巧

## 📚 前置知识

- Jenkins 基础（安装、插件）
- Maven 命令
- `09-ruoyi-deploy.md`

## 1. 核心概念

### 1.1 Jenkins Pipeline 是什么？

Jenkins Pipeline 是一套**把构建/测试/部署流程写成代码**的插件：
- 配置文件：`Jenkinsfile`（与代码同仓库）
- 优势：版本管理、可视化、参数化

### 1.2 两种语法

| 特性 | 声明式（Declarative） | 脚本式（Scripted） |
|------|---------------------|------------------|
| 语法 | `pipeline { stages { ... } }` | `node { stage { ... } }` |
| 易读性 | 高 | 低 |
| 灵活性 | 中 | 高 |
| 推荐 | **是** | 复杂场景 |

ruoyi 用**脚本式**（`#!groovy` 开头）。

### 1.3 核心概念

| 概念 | 作用 |
|------|------|
| `agent` | 指定执行节点 |
| `stages` | 阶段集合 |
| `stage` | 一个阶段 |
| `steps` | 阶段内的步骤 |
| `environment` | 环境变量 |
| `parameters` | 流水线参数 |
| `post` | 流水线结束后操作 |

## 2. 代码示例

### 2.1 声明式 Pipeline

```groovy
pipeline {
    agent any

    options {
        timestamps()  // 显示时间戳
        timeout(time: 30, unit: 'MINUTES')  // 超时
    }

    stages {
        stage('检出') {
            steps {
                git url: 'https://gitee.com/yudao/yudao-server.git', branch: 'main'
            }
        }

        stage('编译') {
            steps {
                sh 'mvn clean package -DskipTests'
            }
        }

        stage('部署') {
            steps {
                sh 'bash deploy.sh'
            }
        }
    }

    post {
        success {
            echo '部署成功'
        }
        failure {
            echo '部署失败'
        }
    }
}
```

### 2.2 参数化构建

```groovy
pipeline {
    agent any

    parameters {
        choice(name: 'ENV', choices: ['dev', 'prod'], description: '部署环境')
        string(name: 'TAG', defaultValue: '', description: '镜像标签')
    }

    stages {
        stage('部署') {
            steps {
                echo "部署到 ${params.ENV}，标签 ${params.TAG}"
                sh "bash deploy-${params.ENV}.sh ${params.TAG}"
            }
        }
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的 Jenkinsfile

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/jenkins/Jenkinsfile`
**完整代码**：

```groovy
#!groovy
pipeline {

    agent any

    parameters {
        string(name: 'TAG_NAME', defaultValue: '', description: '')
    }

    environment {
        // DockerHub 凭证 ID(登录您的 DockerHub)
        DOCKER_CREDENTIAL_ID = 'dockerhub-id'
        //  GitHub 凭证 ID (推送 tag 到 GitHub 仓库)
        GITHUB_CREDENTIAL_ID = 'github-id'
        // kubeconfig 凭证 ID (访问接入正在运行的 Kubernetes 集群)
        KUBECONFIG_CREDENTIAL_ID = 'demo-kubeconfig'
        // 镜像的推送
        REGISTRY = 'docker.io'
        //  DockerHub 账号名
        DOCKERHUB_NAMESPACE = 'docker_username'
        // GitHub 账号名
        GITHUB_ACCOUNT = 'https://gitee.com/zhijiantianya/ruoyi-vue-pro'
        // 应用名称
        APP_NAME = 'yudao-server'
        // 应用部署路径
        APP_DEPLOY_BASE_DIR = '/media/pi/KINGTON/data/work/projects/'
    }

    stages {
        stage('检出') {
            steps {
                git url: "https://gitee.com/will-we/ruoyi-vue-pro.git",
                        branch: "devops"
            }
        }

        stage('构建') {
            steps {
                // TODO 解决多环境链接、密码不同配置临时方案
                sh 'if [ ! -d "' + "${env.HOME}" + '/resources" ];then\n' +
                        '  echo "配置文件不存在无需修改"\n' +
                        'else\n' +
                        '  cp  -rf  ' + "${env.HOME}" + '/resources/*.yaml " + "${env.APP_NAME}" + '/src/main/resources\n' +
                        '  echo "配置文件替换"\n' +
                        'fi'
                sh 'mvn clean package -Dmaven.test.skip=true'
            }
        }

        stage('部署') {
            steps {
                sh 'cp -f ' + ' bin/deploy.sh ' + "${env.APP_DEPLOY_BASE_DIR}" + "${env.APP_NAME}"
                sh 'cp -f ' + "${env.APP_NAME}" + '/target/*.jar ' + "${env.APP_DEPLOY_BASE_DIR}" + "${env.APP_NAME}" +'/build/'
                archiveArtifacts "${env.APP_NAME}" + '/target/*.jar'
                sh 'chmod +x ' + "${env.APP_DEPLOY_BASE_DIR}" + "${env.APP_NAME}" + '/deploy.sh'
                sh 'bash ' + "${env.APP_DEPLOY_BASE_DIR}" + "${env.APP_NAME}" + '/deploy.sh'
            }
        }
    }
}
```

### 3.2 参数与全局变量

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/jenkins/Jenkinsfile`
**核心代码**（行 5-27）：

```groovy
    parameters {
        string(name: 'TAG_NAME', defaultValue: '', description: '')
    }

    environment {
        DOCKER_CREDENTIAL_ID = 'dockerhub-id'
        GITHUB_CREDENTIAL_ID = 'github-id'
        KUBECONFIG_CREDENTIAL_ID = 'demo-kubeconfig'
        REGISTRY = 'docker.io'
        DOCKERHUB_NAMESPACE = 'docker_username'
        GITHUB_ACCOUNT = 'https://gitee.com/zhijiantianya/ruoyi-vue-pro'
        APP_NAME = 'yudao-server'
        APP_DEPLOY_BASE_DIR = '/media/pi/KINGTON/data/work/projects/'
    }
```

**解读**：
- 第 5-7 行：参数 `TAG_NAME`（用于标识构建版本）
- 第 10-13 行：**关键** — 凭证 ID（需要在 Jenkins 凭据管理中预先配置）
  - `DOCKER_CREDENTIAL_ID` — 用于 docker login
  - `GITHUB_CREDENTIAL_ID` — 用于 git push tag
  - `KUBECONFIG_CREDENTIAL_ID` — 用于 kubectl 操作 k8s 集群
- 第 14-15 行：镜像仓库地址
- 第 22-23 行：应用名 + 部署路径（**实际部署服务器的目录**）

### 3.3 检出阶段

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/jenkins/Jenkinsfile`
**核心代码**（行 30-35）：

```groovy
        stage('检出') {
            steps {
                git url: "https://gitee.com/will-we/ruoyi-vue-pro.git",
                        branch: "devops"
            }
        }
```

**解读**：
- 从 gitee 的 devops 分支拉取代码
- 需要在 Jenkins 配置 `GITHUB_CREDENTIAL_ID` 凭证（私人令牌或 SSH key）

### 3.4 构建阶段（配置覆盖）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/jenkins/Jenkinsfile`
**核心代码**（行 37-48）：

```groovy
        stage('构建') {
            steps {
                // TODO 解决多环境链接、密码不同配置临时方案
                sh 'if [ ! -d "' + "${env.HOME}" + '/resources" ];then\n' +
                        '  echo "配置文件不存在无需修改"\n' +
                        'else\n' +
                        '  cp  -rf  ' + "${env.HOME}" + '/resources/*.yaml " + "${env.APP_NAME}" + '/src/main/resources\n' +
                        '  echo "配置文件替换"\n' +
                        'fi'
                sh 'mvn clean package -Dmaven.test.skip=true'
            }
        }
```

**解读**：
- 第 39-46 行：**关键技巧** — 允许管理员在 Jenkins 服务器的 `$HOME/resources/` 放置覆盖配置文件
  - 每次构建都从服务器拉取最新的 yaml（避免把生产密码提交到代码库）
  - 这就是"配置外置"的实践
- 第 47 行：跳过测试编译

### 3.5 部署阶段

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/jenkins/Jenkinsfile`
**核心代码**（行 50-58）：

```groovy
        stage('部署') {
            steps {
                sh 'cp -f ' + ' bin/deploy.sh ' + "${env.APP_DEPLOY_BASE_DIR}" + "${env.APP_NAME}"
                sh 'cp -f ' + "${env.APP_NAME}" + '/target/*.jar ' + "${env.APP_DEPLOY_BASE_DIR}" + "${env.APP_NAME}" +'/build/'
                archiveArtifacts "${env.APP_NAME}" + '/target/*.jar'
                sh 'chmod +x ' + "${env.APP_DEPLOY_BASE_DIR}" + "${env.APP_NAME}" + '/deploy.sh'
                sh 'bash ' + "${env.APP_DEPLOY_BASE_DIR}" + "${env.APP_NAME}" + '/deploy.sh'
            }
        }
```

**解读**：
- 第 52 行：复制 `deploy.sh` 到部署目录
- 第 53 行：复制 jar 到 `build/` 目录（被 `deploy.sh` 读取）
- 第 54 行：`archiveArtifacts` 把 jar 归档到 Jenkins 制品库（可下载）
- 第 55 行：添加可执行权限
- 第 56 行：执行 `deploy.sh`（详见 `09-ruoyi-deploy.md`）

## 4. 关键要点总结

- 声明式 Pipeline 用 `pipeline { ... }` 包裹，**推荐** 写法
- 凭证（ID + 密码）通过 Jenkins 凭据管理注入，**不写在 Jenkinsfile**
- 用 `environment` 块集中管理变量
- 用 `parameters` 块实现参数化构建
- 用 `archiveArtifacts` 归档构建产物
- ruoyi 的配置覆盖技巧：构建时从 `$HOME/resources/` 复制 yaml 覆盖

## 5. 练习题

### 练习 1：基础（必做）

把 ruoyi 的 Jenkinsfile 改写为**声明式语法**（`pipeline { ... }`），保持三阶段（检出/构建/部署）功能不变。

### 练习 2：进阶

为 Jenkinsfile 添加 `parameters` 块：选择部署环境（dev / prod）、输入 Git tag，用 `${params.ENV}` 控制部署脚本。

### 练习 3：挑战（选做）

为 Jenkinsfile 添加 `post` 块：构建失败时发送企业微信通知（调用 webhook）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/script/jenkins/Jenkinsfile`
- `/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
- [Jenkins Pipeline 官方文档](https://www.jenkins.io/doc/book/pipeline/)
- [Jenkins 声明式 Pipeline 语法](https://www.jenkins.io/doc/book/pipeline/syntax/)

---

**文档版本**：v1.0
**最后更新**：2026-07-13
