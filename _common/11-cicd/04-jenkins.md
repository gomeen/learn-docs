# 11.4 Jenkins 流水线

> 学习 Jenkinsfile 的 Groovy DSL 语法，掌握声明式（Declarative）流水线的标准写法，深度解读 ruoyi 的真实 Jenkinsfile。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释声明式 vs 脚本式 Jenkinsfile 的差异
- 用 `pipeline {}` 块描述构建 / 部署 / 健康检查
- 看懂 ruoyi `script/jenkins/Jenkinsfile` 的"Java 打包 + 部署脚本"模式
- 在 GitHub Actions 与 Jenkins 之间进行概念对照

## 📚 前置知识

- [11.1 CI/CD 概念](./01-concepts.md) / [11.2 GitHub Actions](./02-github-actions.md) / [11.3 GitLab CI](./03-gitlab-ci.md)
- Groovy 基础（DSL 不需要深入）

## 1. 核心概念

### 1.1 声明式 vs 脚本式

Jenkins 支持两种流水线语法，**推荐使用声明式**：

```groovy
// ✅ 声明式（Declarative）—— 推荐
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                sh 'mvn package'
            }
        }
    }
}

// 脚本式（Scripted）—— 历史遗留
node {
    stage('Build') {
        sh 'mvn package'
    }
}
```

**核心差异**：声明式有强约束（`pipeline {}` 顶层结构），校验和补全更好；脚本式是普通 Groovy，自由但易出错。

### 1.2 声明式的核心字段

```groovy
pipeline {
    agent any                       # 在哪个 agent 上跑（any / label / docker）

    options {
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
        disableConcurrentBuilds()    # 同一 job 不并发
    }

    parameters {                     # 构建参数
        string(name: 'TAG_NAME', defaultValue: '')
        booleanParam(name: 'FORCE_REBUILD', defaultValue: false)
    }

    environment {                    # 环境变量
        JAVA_HOME = '/usr/lib/jvm/java-8'
    }

    triggers {                       # 自动触发器
        pollSCM('H/15 * * * *')      # 轮询每 15 分钟
        githubPush()                 # GitHub 推送触发
    }

    stages {
        stage('名称') {
            when {                   # 条件
                branch 'main'
            }
            steps {
                sh '...'             # shell
                echo '...'            # 日志
                build 'other-job'    # 调用另一个 job
            }
        }
    }

    post {                           # 收尾动作
        success { echo 'success' }
        failure { mail to: '...' }
        always { junit '*.xml' }      # always 块无论成败都跑
    }
}
```

### 1.3 agent 三种形态

```groovy
agent any                                  # 任意 agent
agent { label 'linux && docker' }          # 有 label 的 agent
agent {
    docker {
        image 'maven:3.9-jdk-8'
        args '-v /root/.m2:/root/.m2'       # 缓存挂载
    }
}
```

**docker agent** 让每个步骤都在指定镜像里运行——和 GitLab CI 的 image 字段一致。

### 1.4 关键概念对比（GitHub Actions / GitLab CI / Jenkins）

| 概念 | GitHub Actions | GitLab CI | Jenkins |
|------|----------------|-----------|---------|
| 配置文件 | `.github/workflows/xx.yml` | `.gitlab-ci.yml` | `Jenkinsfile` |
| 顶层结构 | `jobs:` | `stages:` + `jobs` | `pipeline { stages {} }` |
| 触发器 | `on:` | `rules:` | `triggers {}` 或 UI 配置 |
| 步骤 | `run:` | `script:` | `sh '...'` |
| 缓存 | `actions/cache@v4` | `cache: paths:` | `cache {}` step |
| 凭证 | `secrets.X` | `Variables` | `withCredentials {}` |

## 2. 代码示例

### 2.1 标准 Java 项目 Jenkinsfile

```groovy
#!groovy
pipeline {
    agent any

    options {
        timeout(time: 20, unit: 'MINUTES')
        timestamps()
    }

    parameters {
        choice(name: 'ENV', choices: ['dev', 'staging', 'prod'], description: 'Target env')
    }

    environment {
        JAVA_HOME = '/usr/lib/jvm/java-17'
        MAVEN_OPTS = '-Xmx2g -Dmaven.repo.local=/root/.m2/repository'
    }

    triggers {
        pollSCM('H/15 * * * *')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build') {
            steps {
                sh '''
                    cd yudao-server
                    mvn clean package -B -Dmaven.test.skip=true
                '''
            }
        }

        stage('Unit Test') {
            when {
                expression { params.ENV != 'prod' }
            }
            steps {
                sh 'mvn test'
            }
            post {
                always {
                    junit 'target/surefire-reports/*.xml'
                }
            }
        }

        stage('Deploy') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'ssh-deploy-key',
                    usernameVariable: 'SSH_USER',
                    passwordVariable: 'SSH_KEY'
                )]) {
                    sh '''
                        scp target/*.jar deploy@server:/work/build/
                        ssh deploy@server "bash /work/projects/app/deploy.sh ${ENV}"
                    '''
                }
            }
        }
    }

    post {
        success {
            slackSend(channel: '#deploy', message: "Build #${BUILD_NUMBER} succeeded")
        }
        failure {
            mail to: 'team@example.com',
                 subject: "Build Failed: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                 body: "Check ${env.BUILD_URL}"
        }
    }
}
```

### 2.2 多分支流水线（在 Jenkinsfile 内）

```groovy
pipeline {
    agent any

    options {
        disableConcurrentBuilds()
    }

    stages {
        stage('Build') {
            steps {
                sh 'mvn package'
            }
        }
    }

    post {
        success {
            // 不同分支用不同通知
            script {
                if (env.BRANCH_NAME == 'main') {
                    slackSend(channel: '#prod', message: 'Production build!')
                } else if (env.BRANCH_NAME.startsWith('feature/')) {
                    echo "feature branch build"
                }
            }
        }
    }
}
```

### 2.3 常见错误：超时未设上限

```groovy
// ❌ 错误：构建卡死可能占据 agent 数小时
pipeline {
    agent any
    stages { stage('Test') { steps { sh '...' } } }
}

// ✅ 正确：显式 timeout
pipeline {
    agent any
    options { timeout(time: 30, unit: 'MINUTES') }
    stages { ... }
}
```

### 2.4 常见错误：`sh` 误用环境变量

```groovy
// ❌ 错误：Pipeline 级变量在 sh 里取不到
pipeline {
    environment { FOO = 'bar' }
    stages {
        stage('Test') {
            steps {
                sh 'echo $FOO'   // 输出空（Groovy 字符串单引号不插值）
            }
        }
    }
}

// ✅ 正确：用 Groovy 三引号字符串插值或显式 withEnv
pipeline {
    environment { FOO = 'bar' }
    stages {
        stage('Test') {
            steps {
                sh "echo $FOO"    // Groovy 插值
            }
        }
    }
}
```

## 3. dify 与 ruoyi 源码解读

### 3.1 ruoyi Jenkinsfile：典型 Java 项目流水线

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/jenkins/Jenkinsfile`
**核心代码**（行 1-60）：

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

**解读**：

**A. 凭证管理设计**：

```groovy
DOCKER_CREDENTIAL_ID = 'dockerhub-id'
GITHUB_CREDENTIAL_ID = 'github-id'
KUBECONFIG_CREDENTIAL_ID = 'demo-kubeconfig'
```

- 这种"_CREDENTIAL_ID = 'xxx-id'"是 Jenkins 的**凭证引用约定**
- 但**当前文件实际上没用 `withCredentials`**！这些 ID 是占位符，必须在 Jenkins 凭据管理里创建同名 ID 才能用
- 团队复制此 Jenkinsfile 时，需要：
  1. 在 Jenkins UI → Credentials → Create
  2. 创建名为 `dockerhub-id`、`github-id`、`demo-kubeconfig` 的凭证
  3. 然后在后续 stage 加 `withCredentials([...]) { sh '...' }`

**B. 环境变量命名规范**：
- `APP_NAME = 'yudao-server'`：被多处引用的核心变量
- `APP_DEPLOY_BASE_DIR = '/media/pi/KINGTON/data/work/projects/'`：**绝对路径硬编码到个人电脑**！这是项目维护者的本地路径，使用时需要修改

**C. 阶段 1（检出）**：

```groovy
stage('检出') {
    steps {
        git url: "https://gitee.com/will-we/ruoyi-vue-pro.git",
                branch: "devops"
    }
}
```

- 注意 **Gitee** 而不是 GitHub——这是 fork 的 fork
- 分支 `devops`——Jenkins 检出的不是主分支，而是部署专用分支

**D. 阶段 2（构建）**：

```groovy
sh 'mvn clean package -Dmaven.test.skip=true'
```

- **`-Dmaven.test.skip=true`**——跳过所有测试！这是简化流水线（生产环境也不必测试，因为测试已经在 IDE 跑过）
- 没有 `mvn test`、没有 lint、没有静态分析
- 对比 dify：dify 的 CI **必须**通过 ruff / mypy / pytest / DB migration 测试才能合并

**E. 阶段 3（部署）**：

```groovy
sh 'cp -f bin/deploy.sh ${APP_DEPLOY_BASE_DIR}/${APP_NAME}'
sh 'cp -f ${APP_NAME}/target/*.jar ${APP_DEPLOY_BASE_DIR}/${APP_NAME}/build/'
archiveArtifacts "${env.APP_NAME}" + '/target/*.jar'
sh 'chmod +x ${APP_DEPLOY_BASE_DIR}/${APP_NAME}/deploy.sh'
sh 'bash ${APP_DEPLOY_BASE_DIR}/${APP_NAME}/deploy.sh'
```

四步：
1. 复制 `deploy.sh` 脚本到部署目录（详见 [12 章部署策略](../12-deploy-strategies/)）
2. 复制 jar 包到部署 build 目录
3. **archiveArtifacts**——这是 Jenkins 关键字，把 jar 存档到 Jenkins UI
4. 给 `deploy.sh` 加执行权限
5. **执行 deploy.sh**——这是手工脚本（备份、停止、启动、健康检查），详见 [12 章](../12-deploy-strategies/01-blue-green.md)

**总结 ruoyi 的 Jenkins 设计**：

| 优点 | 缺点 |
|------|------|
| 简单直接，新人易上手 | 缺少测试 / lint / type-check |
| 复用 `deploy.sh` 脚本（统一部署逻辑） | 缺少凭证管理（withCredentials 缺失） |
| archiveArtifacts 留存构建产物 | 缺少多环境（dev/staging/prod）|
| 手动点构建按钮，安全 | 没有超时配置 |
| | 硬编码个人电脑路径 |

**对比 GitHub Actions / GitLab CI**：

| 维度 | ruoyi Jenkinsfile | GitHub Actions |
|------|-------------------|----------------|
| 流水线定义 | Groovy DSL | YAML |
| 阶段 | `stage('名称')` | `name:` |
| 步骤 | `sh '...'` | `run: ...` |
| 上下文变量 | `${env.APP_NAME}` | `${{ env.APP_NAME }}` |
| Credentials | `credentials 'ID'` | `${{ secrets.NAME }}` |
| 缓存 | `caching {}` step | `actions/cache@v4` |
| 依赖并行 | `parallel {}` | `needs:` + 多 job |

## 4. 关键要点总结

- **声明式推荐**：`pipeline { }` 顶层结构，`stages > steps`
- **agent 三形态**：any / label / docker（可在容器内跑步骤）
- **environment vs parameters**：environment 是常量，parameters 是构建参数
- **post 块**：success / failure / always 分别收尾
- **withCredentials**：所有凭证必须在 Jenkins Credentials 创建
- **ruoyi 的"轻量流水线"**：跳过测试 + 直接部署，注重"上线速度"

## 5. 练习题

### 练习 1：基础（必做）

用 `pipeline {}` 写一份简单 Java 项目的 Jenkinsfile：
1. agent any
2. 选项 timeout 20 分钟
3. 三个 stage：Checkout / Build / Deploy
4. post success 发邮件

**参考答案**：见 `solutions/01-jenkins-java.md`

### 练习 2：进阶

阅读 `ruoyi-vue-pro/script/jenkins/Jenkinsfile` 第 37-48 行：

```groovy
stage('构建') {
    steps {
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

回答：
1. 这种 Groovy 字符串拼接 `+ ${env.HOME} +` 写得如何？是否可以更优雅？
2. 为什么用 `/resources/*.yaml` 而不是 `application-prod.yaml` 这种命名？

### 练习 3：挑战（选做）

改造 ruoyi 的 Jenkinsfile 加入：
1. 加入 `mvn test` 单元测试阶段
2. 加入 JUnit 报告收集
3. 用 `withCredentials` 加密 SSH 密码
4. 加入多环境参数（`params.ENV`）并条件化部署

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/script/jenkins/Jenkinsfile`
- Jenkins 文档：https://www.jenkins.io/doc/book/pipeline/
- 声明式语法参考：https://www.jenkins.io/doc/book/pipeline/syntax/
- Jenkins vs GitLab CI vs GitHub Actions：https://www.jenkins.io/blog/2020/12/14/jenkins-vs-other-tools/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
