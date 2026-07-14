# 2.5 存储格式：行存储 vs 列存储

> 行存储适合 OLTP（在线交易），列存储适合 OLAP（数据分析）。两者代表了两种截然不同的优化思路。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解行存储的原理和适用场景
- 理解列存储的原理和适用场景
- 知道主流数据库的存储类型（MySQL/PG 是行存，ClickHouse/Doris 是列存）
- 识别 dify/ruoyi 使用的存储类型

## 📚 前置知识

- 05-architecture.md
- SQL 聚合函数（COUNT、SUM、AVG）

## 1. 核心概念

### 1.1 行存储（Row-Oriented）

```
一行记录连续存储：
[ id=1 | name=Alice | age=30 | dept=CS ]
[ id=2 | name=Bob   | age=25 | dept=EE ]
[ id=3 | name=Carol | age=35 | dept=CS ]
```

**特点**：
- 一行数据在物理上相邻
- 适合 OLTP：`SELECT * FROM users WHERE id = 1`（返回整行）
- 写入友好（一次写入一行）

**代表**：MySQL InnoDB、PostgreSQL、Oracle、SQL Server

### 1.2 列存储（Column-Oriented）

```
一列的所有值连续存储：
[ id=1, 2, 3 ]
[ name=Alice, Bob, Carol ]
[ age=30, 25, 35 ]
[ dept=CS, EE, CS ]
```

**特点**：
- 一列数据在物理上相邻
- 适合 OLAP：`SELECT AVG(age) FROM users`（只读 age 列）
- 压缩比极高（同类数据连续）
- 聚合查询快 10x-100x

**代表**：ClickHouse、Apache Doris、Apache HBase（列族）、Snowflake、BigQuery

### 1.3 对比

| 维度 | 行存储 | 列存储 |
|------|--------|--------|
| 读整行 | ✅ 快 | ❌ 慢（要重组多列） |
| 读单列 | ❌ 浪费 | ✅ 极快 |
| 聚合统计 | ❌ 慢 | ✅ 极快 |
| 写入 | ✅ 简单 | ⚠️ 多列要写多份 |
| 压缩比 | 低 | 高（同类型数据） |
| 适用 | OLTP | OLAP |

### 1.4 混合存储：HBase、Cassandra

**列族（Column Family）**：在列族内是行存，列族间是列存。兼顾两种场景。

## 2. 代码示例

### 2.1 用 Python 模拟行存储

```python
# 行存储：每行是连续的字典
row_store = [
    {"id": 1, "name": "Alice", "age": 30, "salary": 5000.0},
    {"id": 2, "name": "Bob",   "age": 25, "salary": 4500.0},
    {"id": 3, "name": "Carol", "age": 35, "salary": 6000.0},
]

def row_query_all(store, row_id):
    """OLTP 查询：按主键取整行"""
    for row in store:
        if row["id"] == row_id:
            return row
    return None
```

### 2.2 用 Python 模拟列存储

```python
# 列存储：每列是独立的数组
column_store = {
    "id":     [1, 2, 3],
    "name":   ["Alice", "Bob", "Carol"],
    "age":    [30, 25, 35],
    "salary": [5000.0, 4500.0, 6000.0],
}

def column_avg_age(store):
    """OLAP 查询：只读 age 列"""
    return sum(store["age"]) / len(store["age"])

# 列存储的聚合只遍历一列的数据
print(f"平均年龄: {column_avg_age(column_store)}")  # 30.0

def column_query_all(store, row_idx):
    """OLTP 查询：需要重组所有列"""
    return {col: store[col][row_idx] for col in store}
```

### 2.3 列存储的压缩优势

```python
# 列存储：同类数据连续 → 适合 RLE / 字典编码
column_store = {
    "dept": ["CS", "CS", "EE", "EE", "CS", "EE"],
}

# RLE 编码：CS×2, EE×2, CS, EE → 节省空间
# 字典编码：CS→0, EE→1 → [0,0,1,1,0,1]
rle_encoded = [("CS", 2), ("EE", 2), ("CS", 1), ("EE", 1)]
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 用 PostgreSQL（行存储）

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_database.py`
**核心代码**（行 1-30）：

```python
# 默认 PostgreSQL（行存储 OLTP）
SQLALCHEMY_DATABASE_URI = os.getenv(
    "DB_CONNECTION_STRING",
    "postgresql+psycopg2://postgres:difyai123456@localhost:5432/dify",
)
```

**解读**：
- dify 是 OLTP 系统（用户操作密集），用 PostgreSQL 行存储
- **向量数据**用 pgvector 扩展（仍是行存储表 + 向量字段）

### 3.2 ruoyi 也使用行存储（MySQL/PG）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/`
**核心代码**：

```java
// ruoyi 默认 MySQL——纯行存储
@MapperScan("cn.iocoder.yudao.**.dal.**.mapper")
public class YudaoMybatisAutoConfiguration {
    // MyBatis Plus 自动配置，行存储 OLTP
}
```

**解读**：
- ruoyi 是 OLTP 系统，用 MySQL 行存储
- **如需 OLAP**，ruoyi 集成 ClickHouse（`yudao-spring-boot-starter-protection` 中可选）

## 4. 关键要点总结

- 行存储适合 OLTP（按主键查询整行）
- 列存储适合 OLAP（聚合统计、报表分析）
- dify/ruoyi 都是 OLTP，使用行存储
- 列存储的代表：ClickHouse、Doris、Snowflake

## 5. 练习题

### 练习 1：基础
解释为什么 `SELECT AVG(salary) FROM users` 在列存储上更快。

### 练习 2：进阶
调研：dify 是否使用了 ClickHouse 或其他列存储数据库？（提示：查 `extensions/`）

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_database.py`
- ClickHouse 文档：https://clickhouse.com/docs/zh
- 《数据密集型应用系统设计》第 3 章：存储与检索

---

**文档版本**：v1.0
**最后更新**：2026-07-13