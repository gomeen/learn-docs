# 2.1 适配器模式（Adapter）

> 适配器模式将不兼容的接口转换为客户端期望的接口。MyBatis Plus 多数据库适配、Spring MVC HandlerAdapter 都是典型应用。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解适配器模式的核心（接口转换）
- 区分对象适配器 vs 类适配器
- 识别 ruoyi 的 MyBatis 多数据库适配
- 知道适配器 vs 装饰器的区别

## 📚 前置知识

- 继承/接口
- 多态

## 1. 核心概念

### 1.1 适配器的核心思想

把一个类的接口**转换成**另一个接口，使原本不兼容的类可以协同工作。

### 1.2 两种实现方式

| 类型 | 实现 | 语言支持 |
|------|------|---------|
| 对象适配器 | 组合（持有被适配者） | 所有 OO 语言 |
| 类适配器 | 多继承 | C++ 支持，Java/Python 不支持 |

### 1.3 经典比喻

电源适配器：220V 交流电（被适配者）→ USB 5V（目标接口）

### 1.4 适配器 vs 装饰器

| 维度 | 适配器 | 装饰器 |
|------|--------|--------|
| 目的 | 接口转换 | 功能增强 |
| 关系 | 适配后接口可能完全不同 | 装饰前后接口一致 |
| 数量 | 通常 1 个 | 可以多层嵌套 |

## 2. 代码示例

### 2.1 Python 对象适配器

```python
from typing import Protocol

# 目标接口
class PaymentProcessor(Protocol):
    def pay(self, amount: float, currency: str) -> bool: ...

# 已有类（不兼容接口）
class StripeSDK:
    def charge(self, amount_cents: int, currency: str) -> dict:
        return {"status": "ok", "id": "ch_123"}

class PayPalSDK:
    def send_payment(self, total: float, money: str) -> dict:
        return {"state": "approved", "txn_id": "PAY-1"}

# 适配器：把 Stripe/PayPal 适配到统一接口
class StripeAdapter(PaymentProcessor):
    def __init__(self, sdk: StripeSDK):
        self._sdk = sdk

    def pay(self, amount: float, currency: str) -> bool:
        result = self._sdk.charge(int(amount * 100), currency)
        return result["status"] == "ok"

class PayPalAdapter(PaymentProcessor):
    def __init__(self, sdk: PayPalSDK):
        self._sdk = sdk

    def pay(self, amount: float, currency: str) -> bool:
        result = self._sdk.send_payment(amount, currency)
        return result["state"] == "approved"


# 客户端统一调用
def checkout(processor: PaymentProcessor, amount: float) -> None:
    if processor.pay(amount, "USD"):
        print("Payment success")

checkout(StripeAdapter(StripeSDK()), 99.99)
checkout(PayPalAdapter(PayPalSDK()), 99.99)
```

### 2.2 Java 类适配器（理论示例）

```java
// 类适配器需要多继承——Java 不支持
// 实际用对象适配器（组合）

public class StripeAdapter implements PaymentProcessor {
    private StripeSDK stripe;  // 组合

    public StripeAdapter(StripeSDK stripe) {
        this.stripe = stripe;
    }

    @Override
    public boolean pay(double amount, String currency) {
        return stripe.charge((int)(amount * 100), currency).getStatus().equals("ok");
    }
}
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 ruoyi 的 MyBatis Plus 数据库方言适配

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/YudaoMybatisAutoConfiguration.java`
**核心代码**：

```java
@AutoConfiguration
public class YudaoMybatisAutoConfiguration {

    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();

        // 多数据库方言适配——适配器模式
        DialectFactory dialectFactory = DialectFactory.getDialect(dataSource);
        if (dialectFactory instanceof MySQLDialect) {
            interceptor.addInnerInterceptor(new PaginationInnerInterceptor());
        } else if (dialectFactory instanceof PostgreSQLDialect) {
            // PostgreSQL 分页语法不同
            interceptor.addInnerInterceptor(new PaginationInnerInterceptor(DbType.POSTGRE_SQL));
        } else if (dialectFactory instanceof OracleDialect) {
            interceptor.addInnerInterceptor(new PaginationInnerInterceptor(DbType.ORACLE));
        }
        return interceptor;
    }
}
```

**解读**：
- 不同数据库（MySQL/PG/Oracle）的分页 SQL 语法不同
- `DialectFactory` 检测数据库类型，返回对应的方言适配器
- `PaginationInnerInterceptor` 根据方言生成对应 SQL
- **整体设计**：ruoyi 通过适配器模式屏蔽数据库差异，业务代码无感知

### 3.2 dify 的向量数据库适配

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/datasource/vdb/vector_factory.py`
**核心代码**（行 1-50）：

```python
class Vector:
    """向量数据库抽象——适配多种后端"""

    def __init__(self, dataset_id: str, vector_type: str):
        self.dataset_id = dataset_id
        # 根据类型创建不同的向量客户端
        if vector_type == "pgvector":
            self.client = self._create_pgvector()
        elif vector_type == "chroma":
            self.client = self._create_chroma()
        elif vector_type == "qdrant":
            self.client = self._create_qdrant()
        else:
            raise ValueError(f"Unknown vector type: {vector_type}")

    def search_by_vector(self, query_vector: list[float], top_k: int) -> list[dict]:
        # 适配器：统一接口
        return self.client.search(query_vector=query_vector, top_k=top_k)
```

**解读**：
- dify 支持 pgvector、Chroma、Qdrant 等多种向量数据库
- 通过适配器统一 search_by_vector 接口
- **整体设计**：用适配器让上层业务无感知底层向量库差异

## 4. 关键要点总结

- 适配器 = 接口转换器
- 对象适配器（组合）更灵活，是主流
- ruoyi 的多数据库方言、dify 的多向量库都是适配器
- 与装饰器区别：适配器改变接口，装饰器保持接口

## 5. 练习题

### 练习 1：基础
为不同的日志库（logging、loguru、structlog）实现统一接口的适配器。

### 练习 2：进阶
阅读 ruoyi 的 `DialectFactory`，分析它如何检测数据库类型。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/datasource/vdb/vector_factory.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/`
- 《设计模式》第 4 章：结构型模式

---

**文档版本**：v1.0
**最后更新**：2026-07-13