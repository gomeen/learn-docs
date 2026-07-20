# 3.3.7 dify 的 TypeBase 基类与模型规范

> 理解 dify 统一 metadata、dataclass 映射、默认字段 mixin 与 UUID 生成策略背后的模型约定。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 TypeBase 与 MappedAsDataclass 的组合
- 使用 DefaultFieldsMixin / DefaultFieldsDCMixin
- 理解统一 metadata 与命名约定
- 识别 UUIDv7、init=False 与默认工厂

## 📚 前置知识

- [3.3.1 声明式映射](./02-sqlalchemy-mapping.md)
- Python dataclass 基础（详见 [dataclass](../01-fundamentals/26-dataclasses.md)）

## 1. 核心概念

### 1.1 TypeBase 的角色

`TypeBase(MappedAsDataclass, DeclarativeBase)` 让模型既是映射类，又按 dataclass 规则生成构造器。列是否进入构造器由 `init` 控制；系统生成字段常设 `init=False`。

### 1.2 两套默认字段 mixin

`DefaultFieldsMixin` 面向非 dataclass 的 `Base`；`DefaultFieldsDCMixin` 面向 `TypeBase`。二者统一 ID、时间和 repr，但默认参数适配各自映射方式。

### 1.3 UUIDv7 与统一 metadata

UUIDv7 有时间有序前缀，相比随机 UUIDv4 对 B-tree 插入局部性更友好（B-tree 索引详见 [索引原理](../../_common/21-sql/03-sql-index.md)）。所有模型绑定同一个 metadata，Alembic 才能稳定发现表和约束（详见 [Alembic 基础](./13-alembic-basics.md)）。

## 2. 代码示例

### 2.1 复用 dataclass 默认 ID mixin

```python
from uuid import uuid4
from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column

class TypeBase(MappedAsDataclass, DeclarativeBase):
    pass

class DefaultIdMixin(MappedAsDataclass):
    __abstract__ = True
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default_factory=lambda: str(uuid4()),
        init=False,
    )

class Note(DefaultIdMixin, TypeBase):
    __tablename__ = "notes"
    title: Mapped[str] = mapped_column(String(100))

engine = create_engine("sqlite://")
TypeBase.metadata.create_all(engine)
note = Note(title="typed model")
print(note.id, note.title)
```

**说明**：调用方只提供业务字段；实际 dify 使用统一 StringUUID、UTC 工具和 UUIDv7。

## 3. 关键要点总结

- TypeBase 是类型化 dataclass 声明式基类
- 不同基类使用相应默认字段 mixin
- 系统生成字段通常 `init=False`
- 新主键优先 UUIDv7，模型共享 metadata

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
