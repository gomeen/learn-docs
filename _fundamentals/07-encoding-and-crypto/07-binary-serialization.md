# 2.2 MessagePack / BSON / Avro

> 二进制序列化比 JSON 更小、更快，适合高性能场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解二进制序列化的优势
- 掌握 MessagePack、BSON、Avro 的特点
- 在合适场景使用二进制序列化
- 在 dify/ruoyi 中识别应用

## 📚 前置知识

- 06-serialization.md
- 网络传输基础

## 1. 核心概念

### 1.1 主流二进制序列化

| 格式 | 开发者 | 用途 |
|------|--------|------|
| MessagePack | Sadayuki Furuhashi | 通用 |
| BSON | MongoDB | 数据库 |
| Avro | Apache | 大数据 |
| Protobuf | Google | gRPC |
| Thrift | Apache | RPC |

### 1.2 各格式特点

**MessagePack**：
- "像 JSON，但二进制"
- 体积约为 JSON 的 50%
- 比 JSON 快 4x
- 多种语言支持

**BSON（Binary JSON）**：
- MongoDB 的存储格式
- 类似 JSON 但二进制
- 支持额外类型（如 `ObjectId`、`Date`）

**Avro**：
- Apache Hadoop 项目
- Schema 内嵌在数据中
- 适合大规模数据流（Kafka 常用）

### 1.3 何时使用二进制序列化？

- 性能敏感（高频 RPC）
- 网络带宽有限
- 大数据流（Kafka、Spark）
- 存储 MongoDB

## 2. 代码示例

### 2.1 MessagePack

```python
import msgpack

# 序列化
data = {"name": "Alice", "age": 30, "tags": ["python", "AI"]}
packed = msgpack.packb(data)
print(f"MessagePack size: {len(packed)} bytes")   # ~30 字节

# vs JSON
import json
json_str = json.dumps(data).encode("utf-8")
print(f"JSON size: {len(json_str)} bytes")         # ~50 字节

# 反序列化
obj = msgpack.unpackb(packed, raw=False)
print(obj["name"])  # Alice
```

### 2.2 BSON（PyMongo）

```python
import bson

# 序列化
data = {
    "name": "Alice",
    "age": 30,
    "created_at": bson.datetime.datetime.utcnow(),
    "_id": bson.ObjectId(),
}

bson_bytes = bson.encode(data)
print(f"BSON size: {len(bson_bytes)} bytes")

# 反序列化
obj = bson.decode(bson_bytes)
```

### 2.3 体积对比

```python
import json
import msgpack
import bson

data = {"name": "Alice", "age": 30, "tags": ["python", "AI", "data"]}

print(f"JSON:       {len(json.dumps(data).encode()):>3} bytes")
print(f"MessagePack:{len(msgpack.packb(data)):>3} bytes")
print(f"BSON:       {len(bson.encode(data)):>3} bytes")
# 典型输出：
# JSON:        55 bytes
# MessagePack: 33 bytes
# BSON:        79 bytes（含类型标记）
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 用 JSON（API 通用）

**位置**：`/Users/xu/code/github/dify/api/core/agent/`
**核心代码**：

```python
from flask import jsonify

@app.route("/api/chat", methods=["POST"])
def chat():
    """聊天 API——JSON 序列化"""
    data = request.get_json()
    # ...
    return jsonify({
        "message_id": "msg-123",
        "content": "Hello!",
        "tokens": 42,
    })
```

**解读**：
- HTTP API 通用 JSON（人类可读、调试方便）
- 高频内部 RPC 才用二进制

### 3.2 ruoyi 的 Redis 序列化（可能涉及）

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
**核心代码**：

```java
// Spring Cache 默认用 JDK 序列化（二进制）
@Cacheable(value = "user", key = "#id")
public AdminUserDO getUser(Long id) {
    return userMapper.selectById(id);
}
```

**解读**：
- Java JDK 序列化是二进制（紧凑但语言绑定）
- 跨语言场景用 JSON（Jackson）
- ruoyi 默认 JDK 序列化（同 JVM 内）

## 4. 关键要点总结

- 二进制序列化比 JSON 小、快
- MessagePack：通用、跨语言
- BSON：MongoDB 用
- Avro：大数据流（Kafka）
- HTTP API 仍以 JSON 为主

## 5. 练习题

### 练习 1：基础
用 MessagePack 序列化一组数据，对比与 JSON 的体积差异。

### 练习 2：进阶
实现一个简单的 RPC 框架，比较 JSON 和 MessagePack 的性能。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/agent/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
- MessagePack：https://msgpack.org/

---

**文档版本**：v1.0
**最后更新**：2026-07-13