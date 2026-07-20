# 3.4.5 dify 的迁移目录结构分析

> 从配置、环境、模板和版本脚本四个层次理解 dify 如何组织 SQLAlchemy 数据库演进。

## 🎯 学习目标

完成本文档后，你将能够：
- 定位 dify 迁移目录中的关键文件
- 解释 Flask-Migrate 与应用 Engine 的接入
- 理解 Dify 的模板、命名和对象过滤策略
- 能审查一个 dify 迁移的升级/回滚顺序

## 📚 前置知识

- [3.4.1 Alembic 基础](./13-alembic-basics.md)
- [3.4.4 迁移分支与合并](./16-alembic-branch.md)

## 1. 核心概念

### 1.1 目录地图

```text
api/migrations/
├── alembic.ini       # 文件命名与日志
├── env.py            # Engine、metadata、在线/离线执行
├── script.py.mako    # 新 revision 模板
└── versions/         # 历史迁移脚本
```

### 1.2 与 Flask 应用集成

env.py 从 `current_app.extensions['migrate']` 取得 Engine 和 configure_args，因此迁移使用与应用一致的数据库配置（Flask 应用上下文详见 [Flask 上下文](../02-backend/04-flask-context.md)）。连接 URL 会保留密码用于内部配置，同时转义 `%` 以避免 ConfigParser 解释。

### 1.3 项目特征

Dify 版本跨多年，既有早期短文件名，也有日期前缀；存在 PostgreSQL/MySQL 方言分支、批量 alter、数据回填、merge revision。审查时必须以 revision 图和代码为准，不能假设所有文件都由当前模板生成。

## 2. 代码示例

### 2.1 检查迁移图的常用命令

```bash
cd /Users/xu/code/github/dify/api

# 查看当前数据库版本
uv run flask db current

# 查看所有 head；正常发布通常期待一个 head
uv run flask db heads

# 查看版本历史和分支点
uv run flask db history --verbose

# 生成候选迁移后必须人工审查
uv run flask db migrate -m "add example field"

# 在测试数据库升级到最新
uv run flask db upgrade

# 如需审计 SQL，使用离线 SQL 模式（以项目命令支持为准）
uv run flask db upgrade --sql
```

**说明**：Dify 后端命令按项目要求通过 `uv run --project api` 或在 api 目录使用 uv 执行；实际运行前确认环境指向测试数据库。

## 3. 关键要点总结

- Dify 迁移由 ini、env、模板和 versions 四层组成
- Engine 与参数来自 Flask-Migrate 应用扩展
- 历史文件风格多样，revision 图才是执行顺序
- 迁移应在测试库验证正向、反向与跨方言行为

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
