# 2.3 代理模式（Proxy）

> 代理模式为其他对象提供一种代理以控制对这个对象的访问。MyBatis Mapper、Spring AOP 都是动态代理。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解代理模式的核心（控制访问）
- 区分静态代理、动态代理（JDK/CGLIB）
- 识别 MyBatis Mapper 接口的动态代理
- 知道代理 vs 装饰器的区别

## 📚 前置知识

- 07-decorator.md
- Java 反射机制

## 1. 核心概念

### 1.1 代理的核心思想

不直接调用目标对象，而是通过**代理对象**间接调用，代理可以在调用前后插入逻辑。

### 1.2 代理的分类

| 类型 | 实现 | 性能 | 限制 |
|------|------|------|------|
| 静态代理 | 手动写代理类 | 较慢 | 类数量爆炸 |
| JDK 动态代理 | `java.lang.reflect.Proxy` | 较快 | 只能代理接口 |
| CGLIB 动态代理 | 继承目标类 | 最快 | 不能代理 final 类 |

### 1.3 代理 vs 装饰器

| 维度 | 代理 | 装饰器 |
|------|------|--------|
| 目的 | **控制访问**（延迟、安全、远程） | **增加功能** |
| 创建时机 | 通常提前创建 | 运行时动态包装 |
| 关系 | 代理对象可隐藏真实对象 | 装饰对象始终可见 |

### 1.4 代理的常见用途

- **远程代理**：RPC、WebService
- **虚拟代理**：延迟加载（大图片、视频）
- **保护代理**：权限控制
- **智能代理**：引用计数、懒加载
- **缓存代理**：缓存方法返回值

## 2. 代码示例

### 2.1 Python 静态代理

```python
from typing import Protocol

class Image(Protocol):
    def display(self) -> None: ...

class RealImage:
    def __init__(self, filename: str):
        self.filename = filename
        self._load_from_disk()  # 昂贵操作

    def display(self) -> None:
        print(f"Displaying {self.filename}")

    def _load_from_disk(self) -> None:
        print(f"Loading {self.filename} from disk...")

class ImageProxy:
    """虚拟代理——延迟加载"""
    def __init__(self, filename: str):
        self.filename = filename
        self._real_image: RealImage | None = None  # 延迟创建

    def display(self) -> None:
        if self._real_image is None:
            self._real_image = RealImage(self.filename)  # 第一次调用才加载
        self._real_image.display()


# 使用
img = ImageProxy("photo.jpg")
print("Created")           # 不加载
img.display()              # 第一次调用才真正加载
img.display()              # 已加载，直接显示
```

### 2.2 JDK 动态代理

```java
public interface UserService {
    String getUserById(Long id);
}

public class UserServiceImpl implements UserService {
    @Override
    public String getUserById(Long id) {
        return "User-" + id;
    }
}

// 动态代理：自动生成实现类
public class CacheHandler implements InvocationHandler {
    private final Object target;
    private final Map<String, Object> cache = new HashMap<>();

    public CacheHandler(Object target) {
        this.target = target;
    }

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        String key = method.getName() + Arrays.toString(args);
        if (cache.containsKey(key)) {
            return cache.get(key);
        }
        Object result = method.invoke(target, args);
        cache.put(key, result);
        return result;
    }
}

// 使用
UserService target = new UserServiceImpl();
UserService proxy = (UserService) Proxy.newProxyInstance(
    UserService.class.getClassLoader(),
    new Class[]{UserService.class},
    new CacheHandler(target)
);
String user1 = proxy.getUserById(1L);  // 调用真实方法
String user2 = proxy.getUserById(1L);  // 命中缓存
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 ruoyi 的 MyBatis Mapper 动态代理

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/mysql/user/AdminUserMapper.java`
**核心代码**：

```java
public interface AdminUserMapper extends BaseMapperX<AdminUserDO> {
    /**
     * 通过用户名查询用户——接口，无实现类！
     */
    default AdminUserDO selectByUsername(String username) {
        return selectOne(AdminUserDO::getUsername, username);
    }

    /**
     * 通过 ID 列表批量查询
     */
    default List<AdminUserDO> selectByIds(Collection<Long> ids) {
        return selectBatchIds(ids);
    }
}

// 调用
// userMapper 是接口，但能调用方法——JDK 动态代理
AdminUserDO user = userMapper.selectByUsername("admin");
```

**解读**：
- `AdminUserMapper` 是接口，没有实现类——MyBatis 自动生成代理
- MyBatis 用 JDK 动态代理根据 XML 注解生成实现
- **整体设计**：开发者只写接口，MyBatis 框架动态生成代理对象

### 3.2 ruoyi 的 Spring AOP 代理

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/`
**核心代码**：

```java
@Aspect
@Component
public class DataPermissionAspect {
    // 数据权限拦截——CGLIB 动态代理
    @Around("@annotation(dataPermission)")
    public Object around(ProceedingJoinPoint pjp, DataPermission dataPermission) {
        // 1. 在调用前设置数据权限上下文
        DataPermissionContextHolder.push(...);
        try {
            // 2. 调用原方法
            return pjp.proceed();
        } finally {
            // 3. 清理上下文
            DataPermissionContextHolder.pop();
        }
    }
}
```

**解读**：
- Spring AOP 用 **CGLIB 动态代理**生成 Service 子类
- `@Around` 在方法调用前后插入权限检查
- 业务代码无感知——典型的代理模式

### 3.3 dify 的 Provider Manager（远程代理）

**文件位置**：`/Users/xu/code/github/dify/api/core/provider_manager.py`
**核心代码**：

```python
class ProviderManager:
    """模型提供商的代理——缓存 + 转发"""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._cache: dict = {}  # 缓存提供商配置

    def get_provider_config(self, provider: str) -> dict:
        """获取提供商配置（带缓存的代理）"""
        if provider not in self._cache:
            # 实际查询数据库——第一次访问
            config = self._load_from_db(provider)
            self._cache[provider] = config
        return self._cache[provider]
```

**解读**：
- `ProviderManager` 是 `Provider` 的代理——加了缓存
- 客户端通过代理访问，代理决定要不要打 DB
- **整体设计**：用代理做缓存，避免重复查询

## 4. 关键要点总结

- 代理 = 控制对真实对象的访问
- 静态代理：手动写代理类（类爆炸）
- 动态代理：JDK 反射（接口）或 CGLIB（继承）
- ruoyi 的 MyBatis Mapper 是 JDK 动态代理
- Spring AOP 是 CGLIB 动态代理
- 代理 vs 装饰器：代理控制访问，装饰器增加功能

## 5. 练习题

### 练习 1：基础
实现一个虚拟代理 `LazyImage`，只在第一次 `display()` 时才加载真实图片。

### 练习 2：进阶
阅读 ruoyi 的 `DataPermissionAspect`，分析 AOP 代理如何实现数据权限。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/provider_manager.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/dal/mysql/user/AdminUserMapper.java`
- MyBatis 动态代理：https://mybatis.org/mybatis-3/zh/configuration.html
- 《设计模式》第 4 章：代理模式

---

**文档版本**：v1.0
**最后更新**：2026-07-13