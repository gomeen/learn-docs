# 13 - Linux 命令行与 Shell

> 后端开发日常必备的 Linux CLI 技能：文本处理、Shell 脚本、进程管理、网络排障。  
> 跨语言、跨项目通用（dify / ruoyi-vue-pro 等均可复用）。

## 知识点

- [ ] [13.1 Linux 常用命令：`grep` / `awk` / `sed` / `find`](./01-linux-commands.md)
- [ ] [13.2 Shell 脚本：变量、条件、循环、函数](./02-shell-scripting.md)
- [ ] [13.3 进程管理：`ps` / `top` / `kill` / `systemctl`](./03-process-management.md)
- [ ] [13.4 网络命令：`curl` / `wget` / `netstat` / `ss`](./04-network-commands.md)

## 🔗 相关章节

- 操作系统理论（进程、IO、调度）：[`../../_fundamentals/03-operating-system/`](../../_fundamentals/03-operating-system/)
- 计算机网络理论：[`../../_fundamentals/04-computer-network/`](../../_fundamentals/04-computer-network/)
- 容器与部署：[`../09-containerization/`](../09-containerization/)

## 🔗 项目中的实践场景

- **dify（Python）**：容器入口脚本、Gunicorn/Celery 进程、API 调试（`curl`）
- **ruoyi-vue-pro（Java）**：部署脚本、服务启停、端口与健康检查

## 💡 学习建议

1. 先练 **13.1** 文本三剑客，再写 **13.2** 脚本
2. **13.3 / 13.4** 与线上排障强相关，建议边看边在本机/容器里实操
