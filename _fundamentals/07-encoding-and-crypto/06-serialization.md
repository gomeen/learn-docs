# 2.1 JSON / YAML / XML / Protobuf

> 序列化（Serialization）是把对象转为可存储/传输格式的过程。不同场景选择不同格式。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 4 种主流序列化格式
- 对比 JSON、YAML、XML、Protobuf 的差异
- 为场景选择合适的序列化方案
- 在 dify/ruoyi 中识别序列化应用

## 📚 前置知识

- Python 基础
- HTTP API 基础

## 1. 核心概念

### 1.1 4 种格式对比

| 格式 | 可读性 | 体积 | 性能 | 用途 |
|------|--------|------|------|------|
| JSON | 高 | 中 | 中 | API（最主流） |
| YAML | 极高 | 中 | 慢 | 配置文件 |
| XML | 中 | 大 | 慢 | 老系统、SOAP |
| Protobuf | 低 | 极小 | 极快 | 高性能 RPC |

### 1.2 各格式特点

**JSON（JavaScript Object Notation）**：
- 键值对结构
- 6 种数据类型（string、number、object、array、true/false、null）
- 几乎所有语言都支持

**YAML（YAML Ain't Markup Language）**：
- 缩进表示层级（类似 Python）
- 支持注释
- 主要用于配置文件（K8s、Ansible、Docker Compose）

**XML（eXtensible Markup Language）**：
- 标签嵌套结构
- 支持命名空间、Schema、样式表
- 早期 SOAP、Web Service 标准

**Protobuf（Protocol Buffers）**：
- Google 开发
- 二进制格式
- 需要 .proto 定义 schema
- 体积小、速度快

### 1.3 选型建议

| 场景 | 推荐 |
|------|------|
| Web API | JSON |
| 配置文件 | YAML |
| 跨语言 RPC | Protobuf |
| 老系统集成 | XML |

## 2. 代码示例

### 2.1 JSON

```python
import json

# 序列化
data = {"name": "Alice", "age": 30, "tags": ["python", "AI"]}
json_str = json.dumps(data, ensure_ascii=False, indent=2)
print(json_str)
# {
#   "name": "Alice",
#   "age": 30,
#   "tags": ["python", "AI"]
# }

# 反序列化
obj = json.loads(json_str)
```

### 2.2 YAML

```python
import yaml

# 序列化
data = {"name": "Alice", "age": 30, "skills": ["Python", "AI"]}
yaml_str = yaml.dump(data, allow_unicode=True, default_flow_style=False)
print(yaml_str)
# name: Alice
# age: 30
# skills:
#   - Python
#   - AI

# 反序列化
obj = yaml.safe_load(yaml_str)
```

### 2.3 XML

```python
import xml.etree.ElementTree as ET

# 序列化
root = ET.Element("user")
ET.SubElement(root, "name").text = "Alice"
ET.SubElement(root, "age").text = "30"
xml_str = ET.tostring(root, encoding="unicode")
print(xml_str)
# <user><name>Alice</name><age>30</age></user>

# 反序列化
tree = ET.fromstring(xml_str)
print(tree.find("name").text)  # Alice
```

### 2.4 Protobuf（简化示例）

```protobuf
// user.proto
syntax = "proto3";

message User {
  string name = 1;
  int32 age = 2;
  repeated string tags = 3;
}
```

```python
# Python 端（需 pip install protobuf）
# 编译 proto 后使用
from user_pb2 import User

user = User(name="Alice", age=30)
serialized = user.SerializeToString()
print(len(serialized))  # 10 字节

# 反序列化
user2 = User()
user2.ParseFromString(serialized)
print(user2.name)  # Alice
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的 JSON 配置

**位置**：`/Users/xu/code/github/dify/api/configs/`
**核心代码**：

```python
import json
import os

# dify 用 JSON 存储模型配置
def load_model_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# 或从环境变量加载 JSON
config_json = os.getenv("APP_CONFIG", "{}")
config = json.loads(config_json)
```

**解读**：
- dify 配置文件用 JSON（轻量、易解析）
- 模型参数用 JSON 在前后端传输

### 3.2 ruoyi 的 YAML 配置

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application.yml`
**核心代码**：

```yaml
spring:
  application:
    name: yudao-server
  datasource:
    url: jdbc:mysql://localhost:3306/yudao?useUnicode=true&characterEncoding=utf8mb4
    username: root
    password: root
  redis:
    host: localhost
    port: 6379
```

**解读**：
- ruoyi 用 YAML（Spring Boot 默认）
- YAML 比 properties 易读、支持注释

### 3.3 dify 的 YAML 工作流定义

**位置**：`/Users/xu/code/github/dify/api/core/app/`
**核心代码**：

```python
import yaml
from pathlib import Path

def load_workflow_from_yaml(path: Path) -> dict:
    """加载工作流定义"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
```

**解读**：
- 工作流定义用 YAML（可读性高、支持注释）
- 便于人工编辑和版本控制

## 4. 关键要点总结

- JSON：API 最主流，几乎所有语言支持
- YAML：配置文件首选，支持注释
- XML：老系统、SOAP 仍用
- Protobuf：高性能 RPC（gRPC）
- dify 用 JSON/YAML，ruoyi 用 YAML

## 5. 练习题

### 练习 1：基础
把同一份数据分别序列化为 JSON、YAML、XML，对比体积和可读性。

### 练习 2：进阶
实现一个 Protobuf 消息，序列化为二进制，对比与 JSON 的体积差异。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/configs/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application.yml`
- JSON 规范：https://www.json.org/
- YAML 规范：https://yaml.org/

---

**文档版本**：v1.0
**最后更新**：2026-07-13