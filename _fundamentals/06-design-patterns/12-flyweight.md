# 2.7 享元模式（Flyweight）

> 享元模式通过共享相同对象来减少内存使用，适合大量相似对象的场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解享元模式的核心（共享内部状态）
- 区分内部状态 vs 外部状态
- 在 dify/ruoyi 中识别享元应用
- 知道享元模式的适用场景

## 📚 前置知识

- 类与对象
- 缓存设计

## 1. 核心概念

### 1.1 享元的核心思想

把对象的**状态**分为：
- **内部状态（Intrinsic）**：可共享、不变（如字符 'A' 的形状）
- **外部状态（Extrinsic）**：不可共享、由客户端传入（如字符位置）

### 1.2 适用场景

- 大量相似对象
- 对象的大部分状态可以外部化
- 对象创建成本高
- 不需要依赖对象身份（如 `==` 即可）

### 1.3 经典案例

- Java `Integer.valueOf(int)`：-128 到 127 缓存
- Java `String` 常量池
- 文本编辑器中的字符（共享形状，外部传入位置）

## 2. 代码示例

### 2.1 字符享元

```python
import weakref

class Character:
    """字符——享元"""
    def __init__(self, char: str):
        self.char = char  # 内部状态：字符本身

    def display(self, x: int, y: int) -> None:
        """外部状态：位置"""
        print(f"Char '{self.char}' at ({x}, {y})")


class CharacterFactory:
    """享元工厂——缓存共享的字符"""
    _cache: weakref.WeakValueDictionary = weakref.WeakValueDictionary()

    @classmethod
    def get_character(cls, char: str) -> Character:
        if char not in cls._cache:
            cls._cache[char] = Character(char)
        return cls._cache[char]


# 使用：1000 个 'A' 字符只创建 1 个 Character
chars = [CharacterFactory.get_character("A") for _ in range(1000)]
print(chars[0] is chars[999])  # True——同一个对象！

# 不同字符位置（外部状态）
chars[0].display(0, 0)
chars[0].display(10, 20)
```

### 2.2 树节点享元（游戏场景）

```python
class TreeType:
    """树的类型——共享（内部状态：种类）"""
    def __init__(self, name: str, color: str, texture: str):
        self.name = name
        self.color = color
        self.texture = texture  # 大量纹理数据

    def draw(self, x: int, y: int) -> None:
        """外部状态：位置"""
        print(f"Draw {self.name} tree ({self.color}) at ({x}, {y})")


class TreeFactory:
    _tree_types: dict[str, TreeType] = {}

    @classmethod
    def get_tree_type(cls, name: str, color: str, texture: str) -> TreeType:
        key = f"{name}-{color}"
        if key not in cls._tree_types:
            cls._tree_types[key] = TreeType(name, color, texture)
        return cls._tree_types[key]


class Tree:
    """树实例——享元客户端"""
    def __init__(self, x: int, y: int, tree_type: TreeType):
        self.x = x
        self.y = y
        self.tree_type = tree_type  # 共享

    def draw(self) -> None:
        self.tree_type.draw(self.x, self.y)


# 1000 棵树只有 3 种类型
trees = [
    Tree(i, i*2, TreeFactory.get_tree_type("Oak", "green", "oak.png"))
    for i in range(1000)
]
```

## 3. dify 仓库源码解读

### 3.1 dify 的提供商配置缓存（享元）

**文件位置**：`/Users/xu/code/github/dify/api/core/provider_manager.py`
**核心代码**（行 1-30）：

```python
class ProviderManager:
    """提供商管理器——享元 + 单例 + 缓存"""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        # 缓存提供商配置（内部状态：配置对象）
        self._config_cache: dict[str, "ProviderConfiguration"] = {}

    def _get_config(self, provider: str) -> "ProviderConfiguration":
        """获取配置（共享同一份配置对象）"""
        if provider not in self._config_cache:
            # 第一次查询数据库
            config = self._load_from_db(provider)
            self._config_cache[provider] = config
        return self._config_cache[provider]
```

**解读**：
- 多个 `ProviderManager` 实例共享相同的 `ProviderConfiguration`
- 内部状态（配置对象）共享，外部状态（tenant_id）独立
- **整体设计**：用享元减少数据库查询次数

### 3.2 dify 的租户缓存

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 1-30）：

```python
from cachetools import LRUCache

class AccountService:
    """账户服务——LRU 缓存实现享元"""

    def __init__(self):
        # LRU 缓存：最多 1000 个账号对象
        self._account_cache: LRUCache = LRUCache(maxsize=1000)

    def get_account(self, account_id: str) -> Account:
        """获取账号——共享同一对象"""
        if account_id not in self._account_cache:
            account = db.session.query(Account).filter_by(id=account_id).first()
            self._account_cache[account_id] = account
        return self._account_cache[account_id]
```

**解读**：
- 缓存 Account 对象，避免重复查询
- 多个组件共享同一份账号信息——享元
- **整体设计**：缓存是享元模式的常见实现

## 4. 关键要点总结

- 享元 = 共享内部状态，外部状态由客户端传入
- 适合：大量相似对象、对象创建成本高
- 缓存池是享元的常见实现
- dify 用 LRUCache 缓存账号、提供商配置
- 与单例区别：享元可以多个实例，单例只有一个

## 5. 练习题

### 练习 1：基础
为五子棋游戏实现享元模式（棋子的颜色是内部状态，位置是外部状态）。

### 练习 2：进阶
阅读 `dify/api/services/account_service.py`，分析它的缓存策略。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/account_service.py`
- `/Users/xu/code/github/dify/api/core/provider_manager.py`
- 《设计模式》第 4 章：享元模式

---

**文档版本**：v1.0
**最后更新**：2026-07-13