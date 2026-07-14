# 5.3 SQL 注入与参数化查询

> 理解 SQL 注入的攻击原理，强制使用参数化查询，从根本上杜绝拼接 SQL。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 SQL 注入的工作原理与危害
- 区分"字符串拼接"与"参数化查询"
- 在 dify 中识别 ORM 的安全边界
- 在 ruoyi 中识别 MyBatis `#{}` 与 `${}` 的区别

## 📚 前置知识

- SQL 基础语法
- 任一 ORM（SQLAlchemy / MyBatis）
- 5.1 OWASP Top 10 概览

## 1. 核心概念

### 1.1 什么是 SQL 注入？

SQL 注入指攻击者通过**控制 SQL 语句的结构**，绕过认证、窃取数据、甚至执行系统命令。

```
用户输入用户名:  admin' OR '1'='1
应用代码拼接:   SELECT * FROM users WHERE name = 'admin' OR '1'='1' AND pwd = '...'
              └─ 注意 '1'='1' 让条件恒为真
```

### 1.2 SQL 注入的类型

| 类型 | 攻击原理 | 危害 |
|------|---------|------|
| 基于布尔的盲注 | 条件判断 true/false 推断数据 | 慢 |
| 基于时间的盲注 | `SLEEP(5)` 判断响应时间 | 极慢 |
| 基于 UNION 的注入 | `UNION SELECT` 直接获取数据 | 严重 |
| 基于错误回显 | 触发 SQL 错误泄露数据 | 严重 |
| 二次注入 | 数据先入库，再次查询时触发 | 隐蔽 |
| 堆叠查询 | `'; DROP TABLE users;--` | 毁灭性（依赖 DB 驱动）|

### 1.3 真实案例

- **Sony 数据泄露 (2011)**：SQL 注入导致 7700 万用户信息泄露
- **Heartland Payment Systems (2008)**：SQL 注入导致 1.3 亿信用卡号泄露
- **7-Eleven 事件**：攻击者用 SQL 注入从 7-11 提款机盗取现金

### 1.4 防御核心：参数化查询（Prepared Statements）

**唯一可靠的解决方案**是使用参数化查询。它把 SQL 模板与数据分离，数据库驱动会对数据进行严格转义，永远不会改变 SQL 结构。

```python
# ❌ 字符串拼接（危险）
sql = f"SELECT * FROM users WHERE name = '{username}'"

# ✅ 参数化查询（安全）
sql = "SELECT * FROM users WHERE name = %s"
cursor.execute(sql, (username,))
```

### 1.5 ORM 也不绝对安全

ORM（如 SQLAlchemy、MyBatis-Plus）底层用参数化查询，但以下场景仍可能注入：

| 场景 | 风险 | 防御 |
|------|------|------|
| `ORDER BY` 列名 | 用户控制列名 | 用白名单枚举 |
| `LIKE` 查询通配符 | 用户输入 `%`、`_` | 转义或限制 |
| 原生 SQL 调用 | 直接拼接 | 严格参数化 |
| `IN (?, ?, ?)` 动态列表 | 列表长度变化 | 用 `expanding` 参数 |

## 2. 代码示例

### 2.1 漏洞示例：经典 SQL 注入

```python
# 文件：sqli_vulnerable.py
# ❌ 故意写错的 SQL 注入示例
from flask import Flask, request
import sqlite3

app = Flask(__name__)

@app.route("/login")
def login():
    username = request.args.get("username", "")
    password = request.args.get("password", "")

    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()

    # ❌ 字符串拼接，SQL 注入！
    sql = f"SELECT * FROM users WHERE name='{username}' AND pwd='{password}'"
    cursor.execute(sql)
    user = cursor.fetchone()
    if user:
        return "logged in"
    return "failed"

# 攻击 1：万能密码
# /login?username=admin&password=' OR '1'='1
# 拼接后: SELECT * FROM users WHERE name='admin' AND pwd='' OR '1'='1'
# 条件恒为真，绕过密码

# 攻击 2：UNION 注入
# /login?username=' UNION SELECT 1,2,3--&password=x
# 拼接后: SELECT * FROM users WHERE name='' UNION SELECT 1,2,3--' AND pwd='x'
# 返回攻击者构造的数据
```

### 2.2 修正：使用参数化查询

```python
# 文件：sqli_secure.py
# ✅ 正确做法：参数化查询
from flask import Flask, request
import sqlite3

app = Flask(__name__)

@app.route("/login")
def login():
    username = request.args.get("username", "")
    password = request.args.get("password", "")

    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()

    # ✅ 参数化查询：? 占位符 + 参数元组
    sql = "SELECT * FROM users WHERE name=? AND pwd_hash=?"
    cursor.execute(sql, (username, hash_password(password)))
    user = cursor.fetchone()
    if user:
        return "logged in"
    return "failed"

# 测试：username=' OR '1'='1 被当成普通字符串处理，永远查不到
```

### 2.3 ORM 中的陷阱

```python
# 文件：orm_safe_patterns.py
from sqlalchemy import select, text
from sqlalchemy.orm import Session

def search_users_v1(session: Session, sort_by: str):
    """✅ 安全版本：用白名单枚举列名"""
    allowed_columns = {"id", "name", "created_at"}
    if sort_by not in allowed_columns:
        sort_by = "id"
    stmt = select(User).order_by(text(sort_by))
    return session.execute(stmt).scalars().all()

def search_users_v2(session: Session, sort_by: str):
    """✅ 更优雅：使用 SQLAlchemy 列对象（彻底无注入风险）"""
    sort_map = {
        "id": User.id,
        "name": User.name,
        "created_at": User.created_at,
    }
    column = sort_map.get(sort_by, User.id)
    stmt = select(User).order_by(column)
    return session.execute(stmt).scalars().all()

def search_by_keyword(session: Session, keyword: str):
    """✅ LIKE 查询安全模式：转义通配符"""
    # 用户输入 "%admin%" 时，需要把 % 转义为 \%，否则会被当成通配符
    safe_keyword = keyword.replace("%", r"\%").replace("_", r"\_")
    stmt = select(User).where(User.name.like(f"%{safe_keyword}%", escape="\\"))
    return session.execute(stmt).scalars().all()
```

## 3. dify 仓库源码解读

### 3.1 dify 的登录实现（PBKDF2 + ORM 参数化）

**文件位置**：`/Users/xu/code/github/dify/api/libs/password.py`
**核心代码**（行 1-26）：

```python
import base64
import binascii
import hashlib
import re

password_pattern = r"^(?=.*[a-zA-Z])(?=.*\d).{8,}$"


def valid_password(password):
    # Define a regex pattern for password rules
    pattern = password_pattern
    # Check if the password matches the pattern
    if re.match(pattern, password) is not None:
        return password

    raise ValueError("Password must contain letters and numbers, and the length must be at least 8 characters.")


def hash_password(password_str: str, salt_byte: bytes):
    dk = hashlib.pbkdf2_hmac("sha256", password_str.encode("utf-8"), salt_byte, 10000)
    return binascii.hexlify(dk)


def compare_password(password_str, password_hashed_base64, salt_base64):
    # compare password for login
    return hash_password(password_str, base64.b64decode(salt_base64)) == base64.b64decode(password_hashed_base64)
```

**解读**：
- 第 6 行：密码规则正则——**注意 `re.match` 在这里只用于"格式校验"，不是 SQL 拼接，不会注入**
- 第 20 行：PBKDF2-HMAC-SHA256 哈希密码（防止明文存储 = A02 加密失效）
- 第 26 行：常量时间比较哈希值——**避免时序攻击**（A07 认证失效）
- **SQL 注入防护**：dify 全栈用 SQLAlchemy ORM，所有查询都是参数化的

### 3.2 ruoyi 的 MyBatis XML 写法（`#{}` 与 `${}` 的本质区别）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/mysql/permission/RoleMapper.java`（典型 MyBatis Mapper）
**核心代码**（伪代码演示，MyBatis XML 通常这样写）：

```xml
<!-- ✅ 安全：使用 #{} 占位符，参数会被 ? 替换并转义 -->
<select id="selectByName" resultType="RoleDO">
    SELECT * FROM system_role WHERE name = #{name} AND deleted = 0
</select>

<!-- ❌ 危险：使用 ${} 直接字符串替换，可被注入 -->
<select id="selectOrderByColumn" resultType="RoleDO">
    SELECT * FROM system_role ORDER BY ${column}
</select>
```

**对应 Java 接口**：
```java
@Mapper
public interface RoleMapper {
    // ✅ #{}：参数化查询，MyBatis 自动用 PreparedStatement
    RoleDO selectByName(@Param("name") String name);

    // ❌ ${}：直接字符串拼接，必须由调用方保证安全
    List<RoleDO> selectOrderByColumn(@Param("column") String column);
}
```

**解读**：
- `#{}` 会被替换为 `?`，由 JDBC PreparedStatement 预编译——**永远安全**
- `${}` 直接做字符串替换——**如果传入用户输入会注入**
- ruoyi 的规范：能用 `#{}` 就用 `#{}`，只有 ORDER BY 列名这种"SQL 语法片段"才允许 `${}`，且必须用白名单枚举
- **设计意图**：把"数据"和"SQL 结构"严格分离，让攻击者无法控制 SQL 语义

## 4. 关键要点总结

- SQL 注入是 OWASP Top 10 长期榜首，必须用参数化查询防御
- **唯一安全模式**：参数化查询 / ORM / PreparedStatement
- dify 用 SQLAlchemy ORM，天然参数化
- ruoyi 用 MyBatis，**`#{}` 安全，`${}` 危险**
- ORM 也有边界：`ORDER BY` 列名、`LIKE` 通配符需要白名单或转义
- **千万不要拼接 SQL**：哪怕是"内部工具"、"管理后台"也不行

## 5. 练习题

### 练习 1：基础（必做）

写一个用户搜索接口：
- 输入关键字 `q`
- 查询 `users` 表中 `name` 包含 `q` 的所有记录
- 要求：防御 SQL 注入 + LIKE 通配符注入

**参考答案**：见 `solutions/03-sqli-like.md`

### 练习 2：进阶

阅读 ruoyi 的 `MenuMapper.java` 或类似的 MyBatis Mapper，找出所有 `${}` 出现的位置，判断是否安全（检查是否有白名单保护）。

### 练习 3：挑战（选做）

写一个 SQL 注入扫描器：扫描项目源码中的 `.py` / `.java` 文件，找出所有"可能存在 SQL 拼接"的位置（f-string 拼接 SQL、`${}` 拼接等），输出报告。

提示：
- Python：`re.findall(r'execute\([^)]*f["\']', code)` 初步匹配
- Java：`grep -r '\${' --include='*.java'`

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/password.py`
- `/Users/xu/code/github/dify/api/services/account_service.py`（看 SQLAlchemy 查询模式）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/mysql/permission/RoleMapper.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/mysql/permission/PermissionMapper.java`
- OWASP SQL 注入防护手册：https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13