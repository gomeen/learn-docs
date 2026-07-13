# 5.3.2 SQL 注入与参数化查询

> 理解 SQL 注入的攻击原理，掌握参数化查询这一根本防御手段。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 SQL 注入的攻击原理（字符串拼接）
- 掌握参数化查询的防御机制（预编译）
- 能在 dify 中识别所有 ORM 查询都已使用参数化
- 识别仍可能出现的"二阶注入"和"ORM 反模式"

## 📚 前置知识

- 01-fundamentals/05-sqlalchemy-orm.md
- 13-owasp-top10.md

## 1. 核心概念

### 1.1 什么是 SQL 注入？

攻击者通过把 SQL 语句片段插入到用户输入中，让数据库执行**未预期的命令**。

```
原始查询（不安全）：
  SELECT * FROM users WHERE name = '{input}'

用户输入：admin' --
变成的查询：
  SELECT * FROM users WHERE name = 'admin' --'
                                                  ↑
                                  注释掉了后面的单引号
```

### 1.2 攻击能做什么？

- **绕过登录**：`' OR 1=1 --` 让 WHERE 永远为真
- **数据泄露**：UNION SELECT 拉其他表
- **数据篡改**：UPDATE/DELETE 注入
- **数据库提权**：在 SQL Server 上甚至能执行系统命令

### 1.3 根本防御：参数化查询

数据库驱动在执行前**先编译** SQL 模板（绑定参数位置），再把用户输入**作为数据**填入，用户输入永远不会被当成代码执行。

```python
# ✅ 参数化（安全）
cursor.execute("SELECT * FROM users WHERE name = ?", (user_input,))

# ❌ 字符串拼接（不安全）
cursor.execute(f"SELECT * FROM users WHERE name = '{user_input}'")
```

**SQLAlchemy ORM** 默认就是参数化的，使用 `.filter_by()` 或 `.where()` 等方法都是安全的。

## 2. 代码示例

### 2.1 不安全 vs 安全的对比

```python
# ❌ 不安全：f-string 拼接
def find_user_unsafe(email: str):
    sql = f"SELECT * FROM users WHERE email = '{email}'"
    return db.session.execute(sql)

# 攻击：email = "x'; DROP TABLE users; --"
# 变成：SELECT * FROM users WHERE email = 'x'; DROP TABLE users; --'


# ✅ 安全：参数化
def find_user_safe(email: str):
    sql = "SELECT * FROM users WHERE email = :email"
    return db.session.execute(sql, {"email": email})


# ✅ 更安全：SQLAlchemy ORM（永远参数化）
def find_user_orm(email: str):
    return db.session.scalar(select(User).where(User.email == email))
```

### 2.2 SQLAlchemy 中所有"安全"的查询方式

```python
from sqlalchemy import select, text
from sqlalchemy.orm import Session

# ✅ Query 1：select() + where()
session.scalar(select(User).where(User.email == email))

# ✅ Query 2：filter_by()
session.query(User).filter_by(email=email).first()

# ✅ Query 3：filter() + 表达式
session.query(User).filter(User.email == email).first()

# ❌ 反例：text() 拼接字符串（必须警惕！）
session.execute(text(f"SELECT * FROM users WHERE email = '{email}'"))  # 不安全

# ✅ text() 的正确用法：用 bindparam
session.execute(text("SELECT * FROM users WHERE email = :email"),
                {"email": email})
```

## 3. dify 仓库源码解读

### 3.1 ORM 参数化查询

**文件位置**：`/Users/xu/code/github/dify/api/controllers/common/wraps.py`
**核心代码**（行 109-119）：

```python
def _is_resource_owned_by_current_user(
    tenant_id: str, account_id: str, resource_type: RBACResourceScope, resource_id: str
) -> bool:
    """Check if current user is the resource owner."""
    if resource_type == RBACResourceScope.APP:
        with sessionmaker(db.engine).begin() as session:
            resource = session.scalar(
                select(App).where(App.id == resource_id, App.tenant_id == tenant_id)
            )
        if resource is None:
            return False
        return resource.created_by == account_id
```

**解读**：
- 第 7 行：`select(App).where(...)` 是纯 ORM 调用，参数完全参数化
- 第 7-8 行：所有 `==` 比较都会被翻译成 SQL 的 `?` 占位符
- **dify 规范**：业务代码 **必须** 用 ORM 或 `text()` + bindparam，禁止 f-string 拼接 SQL

### 3.2 ApiToken 唯一性检查

**文件位置**：`/Users/xu/code/github/dify/api/models/model.py`
**核心代码**（行 2253-2259）：

```python
    @staticmethod
    def generate_api_key(prefix: str, n: int) -> str:
        while True:
            result = prefix + generate_string(n)
            if db.session.scalar(select(exists().where(ApiToken.token == result))):
                continue
            return result
```

**解读**：
- 第 3 行：`generate_string(n)` 生成 n 位随机串
- 第 4 行：`select(exists().where(...))` 检查 token 是否已存在——**完全参数化**
- **设计意图**：循环重试直到生成唯一 Token（碰撞概率极低但不为零）
- **安全启示**：即使是内部生成的字符串，也走 ORM 参数化查询

### 3.3 API Token 缓存键

**文件位置**：`/Users/xu/code/github/dify/api/services/api_token_service.py`
**核心代码**（行 88-103）：

```python
    @staticmethod
    def _serialize_token(api_token: Any) -> bytes:
        """Serialize ApiToken object to JSON bytes."""
        if isinstance(api_token, CachedApiToken):
            return api_token.model_dump_json().encode("utf-8")

        cached = CachedApiToken(
            id=str(api_token.id),
            app_id=str(api_token.app_id) if api_token.app_id else None,
            tenant_id=str(api_token.tenant_id) if api_token.tenant_id else None,
            type=api_token.type,
            token=api_token.token,
            last_used_at=api_token.last_used_at,
            created_at=api_token.created_at,
        )
        return cached.model_dump_json().encode("utf-8")
```

**解读**：
- 第 12-19 行：**Pydantic 模型**的字段序列化，不走 SQL
- **关联点**：上层 ORM 已经从 DB 安全地读到对象，这里只做内存操作
- **设计意图**：DB 层和缓存层职责分明，DB 层用 ORM，缓存层用 Pydantic

## 4. 关键要点总结

- SQL 注入 = 用户输入被当成 SQL 代码执行
- **根本防御**：参数化查询（Prepared Statements）
- SQLAlchemy ORM 默认安全（`.filter()` / `.where()`）
- **`text()` 是危险入口**，必须配合 `bindparam`
- dify 全代码库遵循 ORM 规范，无明显注入风险
- **二阶注入** 仍需警惕：把 DB 数据再拼到 SQL 时也要参数化

## 5. 练习题

### 练习 1：基础（必做）

用 SQLAlchemy ORM 写一个 `find_user_by_email(session, email)`，要求 100% 参数化。

### 练习 2：进阶

阅读 `api/services/api_token_service.py:88-103`，思考：为什么 dify 用 Pydantic 序列化 Token 而不是直接用 ORM 对象？这种"分层"对安全有什么好处？

### 练习 3：挑战（选做）

设计一个 **SQL 注入检测脚本**：用 AST 扫描 Python 代码，识别所有 `f"...SELECT..."` 模式或 `text()` 中带 `%` / `+` 的拼接，给出警告。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/common/wraps.py`
- `/Users/xu/code/github/dify/api/models/model.py`
- `/Users/xu/code/github/dify/api/services/api_token_service.py`
- OWASP SQL 注入：https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
- SQLAlchemy 安全：https://docs.sqlalchemy.org/en/20/core/sqlelement.html#sql-expression-language

---

**文档版本**：v1.0
**最后更新**：2026-07-13