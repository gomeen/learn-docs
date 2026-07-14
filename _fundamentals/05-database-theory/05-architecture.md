# 2.1 数据库架构：连接器 / 解析器 / 优化器 / 执行器

> 理解一条 SQL 从发送到返回结果经历了哪些步骤，是性能调优的基础。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握数据库服务器的 4 大组件：连接器、解析器、优化器、执行器
- 理解一条 SQL 的完整执行流程
- 识别 SQL 慢在哪一步
- 在 dify 中理解 SQLAlchemy 与数据库的交互过程

## 📚 前置知识

- SQL 基础
- 关系代数（02-relational-algebra.md）

## 1. 核心概念

### 1.1 数据库服务器的 4 大组件

```
Client ──> [连接器] ──> [解析器] ──> [优化器] ──> [执行器] ──> 存储引擎
              │            │            │            │
           连接池      语法/语义      CBO/RBO      算子树
                       分析器        代价估算       执行
```

| 组件 | 职责 | 关键技术 |
|------|------|---------|
| 连接器 | 管理客户端连接、权限校验 | 连接池、SSL |
| 解析器 | 词法分析、语法分析、语义分析 | AST、语法树 |
| 优化器 | 生成最优执行计划 | CBO（基于代价）、RBO（基于规则） |
| 执行器 | 按计划访问存储引擎、返回结果 | 火山模型、迭代器 |

### 1.2 SQL 执行流程详解

```
1. 连接器：客户端 TCP 连接 → 校验用户名密码 → 权限检查
2. 解析器：SQL 字符串 → 词法分析（tokens）→ 语法分析（AST）→ 语义分析
3. 优化器：AST → 逻辑计划 → 物理计划（选索引、决定 JOIN 顺序）→ 执行计划
4. 执行器：执行计划 → 调用存储引擎 API → 返回结果集
```

### 1.3 关键概念

- **查询计划（Query Plan）**：优化器输出的执行步骤树
- **CBO（Cost-Based Optimizer）**：基于代价估算（如 PostgreSQL、Oracle）
- **RBO（Rule-Based Optimizer）**：基于规则（旧版 MySQL）
- **火山模型（Volcano Model）**：迭代式算子执行（`open()`/`next()`/`close()`）

## 2. 代码示例

### 2.1 模拟 SQL 执行流程（教学用）

```python
from dataclasses import dataclass

@dataclass
class ParsedSQL:
    """解析器输出：AST（抽象语法树）"""
    action: str           # SELECT/INSERT/UPDATE
    columns: list[str]
    table: str
    conditions: list[tuple[str, str, object]]

@dataclass
class QueryPlan:
    """优化器输出：执行计划"""
    steps: list[str]
    estimated_cost: float
    index_used: str | None

def parse(sql: str) -> ParsedSQL:
    """解析器：SQL 字符串 → AST（简化版）"""
    if sql.startswith("SELECT"):
        # 实际中会用 Lex/Yacc 或 SQL 解析器
        return ParsedSQL(
            action="SELECT",
            columns=["name", "age"],
            table="users",
            conditions=[("age", ">", 25)],
        )
    raise ValueError("未实现的 SQL")

def optimize(ast: ParsedSQL) -> QueryPlan:
    """优化器：AST → 执行计划"""
    has_index = True  # 假设 age 有索引
    if has_index and any(c[0] == "age" for c in ast.conditions):
        return QueryPlan(
            steps=["IndexScan(age>25)", "Project(name, age)"],
            estimated_cost=5.0,
            index_used="idx_users_age",
        )
    return QueryPlan(
        steps=["SeqScan(users)", "Filter(age>25)", "Project(name, age)"],
        estimated_cost=1000.0,
        index_used=None,
    )

def execute(plan: QueryPlan) -> list[dict]:
    """执行器：按计划访问存储引擎"""
    print(f"执行计划: {' -> '.join(plan.steps)}")
    print(f"估算代价: {plan.estimated_cost}")
    # 实际中会调用存储引擎的 scan/fetch 接口
    return [{"name": "Alice", "age": 30}, {"name": "Carol", "age": 35}]

# ===== 完整流程 =====
ast = parse("SELECT name, age FROM users WHERE age > 25")
plan = optimize(ast)
results = execute(plan)
```

### 2.2 EXPLAIN 看执行计划（MySQL/PostgreSQL）

```sql
EXPLAIN SELECT * FROM users WHERE age > 25;

-- 输出（PostgreSQL 示例）：
-- Index Scan using idx_users_age on users
--   (cost=0.42..8.44 rows=10 width=42)
--   Index Cond: (age > 25)
```

## 3. dify 仓库源码解读

### 3.1 SQLAlchemy 与数据库的交互

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_database.py`
**核心代码**（行 1-50）：

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from configs import dify_config

# ===== 连接器：创建数据库引擎 =====
# SQLAlchemy 的 create_engine 封装了连接池（连接器功能）
engine = create_engine(
    dify_config.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,             # 连接前检查健康
    pool_size=10,                   # 连接池大小
    max_overflow=20,                # 最大溢出
    pool_recycle=3600,              # 1 小时回收
)

# Session 工厂（会话管理）
SessionFactory = sessionmaker(bind=engine)

# 全局 scoped session（线程安全）
db = scoped_session(SessionFactory)
```

**解读**：
- 第 11-16 行：`create_engine` 是 SQLAlchemy 的**连接器**：管理连接池
- 第 10 行：`pool_pre_ping=True` 防止拿到已断开的连接
- 第 19 行：`scoped_session` 保证每个线程一个独立 session
- **完整流程**：应用调用 `db.session.execute(sql)` → 连接器获取连接 → 解析器编译 SQL → 优化器生成计划 → 执行器返回结果

## 4. 关键要点总结

- 一条 SQL 经历 4 个组件：连接器 → 解析器 → 优化器 → 执行器
- 优化器决定 SQL 性能（是否走索引、JOIN 顺序）
- EXPLAIN 是查看执行计划的工具
- dify 用 SQLAlchemy 封装了连接管理，开发者无需关心连接池细节

## 5. 练习题

### 练习 1：基础
执行 `EXPLAIN SELECT * FROM messages WHERE conversation_id = 'xxx'`，判断是否走了索引。

### 练习 2：进阶
阅读 `dify/api/extensions/ext_database.py`，找出连接池相关配置（pool_size、pool_recycle）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_database.py`
- 《PostgreSQL 实战》第 5 章：查询处理
- https://www.postgresql.org/docs/current/using-explain.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13