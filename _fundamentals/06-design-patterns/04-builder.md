# 1.4 建造者模式（Builder）

> 建造者模式用于构建复杂对象，把构造过程与表示分离。SQL 查询构造器、HTTP 请求构造器都是典型应用。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解建造者模式的核心思想（分步构造）
- 掌握 Python/Java 的 Builder 实现
- 识别 SQLAlchemy 的链式查询就是建造者
- 在 dify/ruoyi 中识别建造者应用

## 📚 前置知识

- 02-factory-method.md
- 链式调用（Fluent Interface）

## 1. 核心概念

### 1.1 建造者的核心思想

把复杂对象的构建**分步骤**进行，每步返回 builder 自身以支持链式调用。

### 1.2 适用场景

- 对象有很多属性（>4 个），构造器参数过多
- 不同表示需要不同构造过程
- 需要分步骤构造（逐步设置）

### 1.3 建造者 vs 工厂方法

| 维度 | 工厂方法 | 建造者 |
|------|---------|--------|
| 关注点 | 创建什么 | 如何创建 |
| 过程 | 一步 | 多步 |
| 复杂度 | 简单 | 复杂 |
| 链式调用 | 一般不支持 | 支持 |

## 2. 代码示例

### 2.1 Python 建造者

```python
from dataclasses import dataclass, field
from typing import Self

@dataclass
class HttpRequest:
    url: str
    method: str = "GET"
    headers: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    body: str | None = None
    timeout: float = 30.0


class HttpRequestBuilder:
    """HTTP 请求构造器——链式 API"""

    def __init__(self, url: str):
        self._request = HttpRequest(url=url)

    def method(self, method: str) -> Self:
        self._request.method = method
        return self

    def header(self, key: str, value: str) -> Self:
        self._request.headers[key] = value
        return self

    def param(self, key: str, value: str) -> Self:
        self._request.params[key] = value
        return self

    def body(self, body: str) -> Self:
        self._request.body = body
        return self

    def timeout(self, seconds: float) -> Self:
        self._request.timeout = seconds
        return self

    def build(self) -> HttpRequest:
        return self._request


# 使用：链式构造
req = (
    HttpRequestBuilder("https://api.example.com/users")
    .method("POST")
    .header("Authorization", "Bearer xxx")
    .param("limit", "10")
    .body('{"name": "Alice"}')
    .timeout(60.0)
    .build()
)
```

### 2.2 Java Lombok @Builder

```java
import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class HttpRequest {
    private String url;
    @Builder.Default
    private String method = "GET";
    @Builder.Default
    private Map<String, String> headers = new HashMap<>();
    @Builder.Default
    private Map<String, String> params = new HashMap<>();
    private String body;
    @Builder.Default
    private double timeout = 30.0;
}

// 使用
HttpRequest req = HttpRequest.builder()
    .url("https://api.example.com/users")
    .method("POST")
    .header("Authorization", "Bearer xxx")
    .body("{\"name\": \"Alice\"}")
    .build();
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 SQLAlchemy Query Builder（dify 用法）

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 1-30）：

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.account import Account, TenantAccountJoin

def get_user_tenants(user_id: str) -> list[Tenant]:
    """查询用户租户——SQLAlchemy Query Builder"""
    with Session(db.engine) as session:
        stmt = (
            select(Tenant)                           # 开始构造
            .join(                                   # JOIN 子句
                TenantAccountJoin,
                Tenant.id == TenantAccountJoin.tenant_id,
            )
            .where(                                  # WHERE 子句
                TenantAccountJoin.account_id == user_id
            )
            .order_by(Tenant.created_at.desc())      # ORDER BY
        )
        return list(session.scalars(stmt).all())     # 执行
```

**解读**：
- `select().join().where().order_by()` 链式调用——典型建造者
- 每次调用返回新 Query 对象（不可变）
- **整体设计**：SQLAlchemy 用建造者构造 SQL，避免字符串拼接

### 3.2 ruoyi 的 LambdaQueryWrapper（MyBatis Plus）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/mysql/user/AdminUserMapper.java`
**核心代码**：

```java
public interface AdminUserMapper extends BaseMapperX<AdminUserDO> {
    // MyBatis Plus 用 LambdaQueryWrapper 构造查询——建造者模式

    default PageResult<AdminUserDO> getUserPage(UserPageReqVO reqVO) {
        return selectPage(reqVO, new LambdaQueryWrapperX<AdminUserDO>()
            .likeIfPresent(AdminUserDO::getUsername, reqVO.getUsername())
            .likeIfPresent(AdminUserDO::getMobile, reqVO.getMobile())
            .eqIfPresent(AdminUserDO::getStatus, reqVO.getStatus())
            .betweenIfPresent(AdminUserDO::getCreateTime,
                new Object[]{reqVO.getCreateTime()[0], reqVO.getCreateTime()[1]})
            .orderByDesc(AdminUserDO::getId));
    }
}
```

**解读**：
- `LambdaQueryWrapperX` 是 MyBatis Plus 的查询建造者
- 链式调用：`.like().eq().between().orderBy()`
- **整体设计**：用建造者构造动态 SQL，避免 XML 拼接

## 4. 关键要点总结

- 建造者模式 = 分步构造 + 链式调用
- 适用：复杂对象（多属性、多步骤）
- SQLAlchemy Query、MyBatis Plus Wrapper 都是建造者
- Java Lombok @Builder 自动生成建造者代码
- dify 用 SQLAlchemy，ruoyi 用 LambdaQueryWrapperX

## 5. 练习题

### 练习 1：基础
为发送邮件的 `EmailMessage` 实现 Builder 模式（支持收件人、主题、正文、附件、抄送、密送）。

### 练习 2：进阶
阅读 ruoyi 的 `LambdaQueryWrapperX`，找出所有链式方法。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/account_service.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/`
- 《Effective Java》第 2 章：Builder 模式

---

**文档版本**：v1.0
**最后更新**：2026-07-13