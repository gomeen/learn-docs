# 1.1 单例模式（Singleton）

> 单例模式保证一个类只有一个实例，并提供全局访问点。Spring 框架的核心就是单例。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 5 种单例实现方式（懒汉、饿汉、双重检查、静态内部类、枚举）
- 理解 Python 中模块级单例的天然支持
- 知道 Spring Bean 默认就是单例
- 在 dify/ruoyi 中识别单例应用

## 📚 前置知识

- Python 类与对象
- Java 类基础

## 1. 核心概念

### 1.1 单例的三个要点

1. **私有构造**：禁止外部 `new`
2. **唯一实例**：类内部维护一个静态实例
3. **全局访问**：提供静态方法返回实例

### 1.2 5 种实现方式对比

| 方式 | 线程安全 | 延迟加载 | 实现难度 | 推荐度 |
|------|---------|---------|---------|--------|
| 饿汉式 | ✅ | ❌ | ⭐ | ⭐⭐ |
| 懒汉式（同步方法） | ✅ | ✅ | ⭐ | ⭐⭐ |
| 双重检查锁 | ✅ | ✅ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 静态内部类 | ✅ | ✅ | ⭐⭐ | ⭐⭐⭐⭐ |
| 枚举 | ✅ | ❌ | ⭐ | ⭐⭐⭐⭐⭐（Effective Java 推荐）|

### 1.3 单例的破坏与防护

- **反射攻击**：通过反射调用私有构造
- **反序列化**：反序列化会创建新实例
- **防护**：枚举最安全（Java 强制保证）

## 2. 代码示例

### 2.1 Python 单例实现

```python
class SingletonMeta(type):
    """元类实现单例——Python 推荐方式"""
    _instances: dict = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class DatabaseConnection(metaclass=SingletonMeta):
    def __init__(self, url: str):
        self.url = url

    def query(self, sql: str):
        return f"Executing on {self.url}: {sql}"


# 验证单例
db1 = DatabaseConnection("postgresql://...")
db2 = DatabaseConnection("postgresql://other...")
print(db1 is db2)  # True——始终是同一个实例
```

### 2.2 Python 模块级单例（更 Pythonic）

```python
# config.py
class _Config:
    def __init__(self):
        self.database_url = "postgresql://..."
        self.api_key = "..."

config = _Config()  # 模块级单例——天然单例

# 任何地方 from config import config 都是同一个实例
```

### 2.3 Java 单例实现（双重检查锁）

```java
public class Singleton {
    // volatile 防止指令重排序
    private static volatile Singleton instance;

    private Singleton() {}  // 私有构造

    public static Singleton getInstance() {
        if (instance == null) {                    // 第一次检查
            synchronized (Singleton.class) {
                if (instance == null) {            // 第二次检查
                    instance = new Singleton();
                }
            }
        }
        return instance;
    }
}
```

### 2.4 枚举单例（最安全）

```java
public enum DatabaseConfig {
    INSTANCE;

    private final String url = "postgresql://...";

    public String getUrl() {
        return url;
    }
}

// 使用
String url = DatabaseConfig.INSTANCE.getUrl();
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 用 SQLAlchemy `scoped_session` 实现单例

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_database.py`
**核心代码**（行 1-30）：

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(dify_config.SQLALCHEMY_DATABASE_URI, pool_size=10)
SessionFactory = sessionmaker(bind=engine)

# 单例：scoped_session 保证每个线程一个实例
db = scoped_session(SessionFactory)

# 任何地方通过 from extensions.ext_database import db 获取同一个 session 工厂
```

**解读**：
- `scoped_session` 是 SQLAlchemy 的线程局部单例
- 第 10 行：模块级变量 `db` 是天然的 Python 单例
- **整体设计**：用模块级单例避免每次创建 session 工厂

### 3.2 ruoyi 用 Spring 单例 Bean

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/`
**核心代码**：

```java
@Bean
@Scope(value = ConfigurableBeanFactory.SCOPE_SINGLETON)  // 默认就是 SINGLETON
public DataSource dataSource(DataSourceProperties properties) {
    HikariDataSource dataSource = new HikariDataSource();
    // ... 配置 ...
    return dataSource;
}
```

**解读**：
- `@Bean` 默认就是单例（`SCOPE_SINGLETON`）
- Spring IoC 容器保证整个应用只有一个 DataSource 实例
- **整体设计**：Spring 容器统一管理所有 Bean 的生命周期

## 4. 关键要点总结

- 单例 = 全局唯一实例 + 全局访问点
- Python 推荐用模块级变量或元类
- Java 推荐用枚举或双重检查锁
- Spring Bean 默认就是单例
- dify 用模块级单例（`db = scoped_session(...)`）

## 5. 练习题

### 练习 1：基础
用 Python 元类实现一个配置类 ConfigSingleton，确保整个应用只有一个实例。

### 练习 2：进阶
阅读 ruoyi 的 `AdminUserServiceImpl.java`，确认它是单例 Bean。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_database.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/`
- 《Effective Java》第 3 章：枚举单例

---

**文档版本**：v1.0
**最后更新**：2026-07-13