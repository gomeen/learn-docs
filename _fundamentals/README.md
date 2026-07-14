# 通用基础（_fundamentals）

> 跨语言、跨项目共享的基础知识。本目录是 **dify** 和 **ruoyi-vue-pro** 的共同前置知识。

## 🎯 为什么有这个目录？

之前的项目（dify、ruoyi-vue-pro）各自只覆盖了 **语言特定** 的基础知识（Python 基础 / Java 基础），但缺失了大量 **跨语言通用** 的核心知识：

- 数据结构与算法
- 操作系统
- 计算机网络
- 数据库原理
- 设计模式
- 编码与加密
- 正则表达式

这些知识**所有后端开发都必备**，且**与具体语言无关**，所以抽取到公共目录。

## 📚 知识分类

| 分类 | 主题 | 目录 |
|------|------|------|
| **01** | 数据结构 | [`01-data-structures/`](./01-data-structures/) |
| **02** | 算法基础 | [`02-algorithms/`](./02-algorithms/) |
| **03** | 操作系统 | [`03-operating-system/`](./03-operating-system/) |
| **04** | 计算机网络 | [`04-computer-network/`](./04-computer-network/) |
| **05** | 数据库原理 | [`05-database-theory/`](./05-database-theory/) |
| **06** | 设计模式 | [`06-design-patterns/`](./06-design-patterns/) |
| **07** | 编码与加密 | [`07-encoding-and-crypto/`](./07-encoding-and-crypto/) |
| **08** | 正则表达式 | [`08-regular-expression/`](./08-regular-expression/) |

## 📖 学习顺序建议

```
01-data-structures（数据结构） + 02-algorithms（算法）
    ↓
03-operating-system（操作系统） + 04-computer-network（计算机网络）
    ↓
05-database-theory（数据库原理）
    ↓
06-design-patterns（设计模式）
    ↓
07-encoding-and-crypto（编码与加密） + 08-regular-expression（正则）
```

## 🔗 与项目目录的关系

- **dify**（Python）：`../dify/01-fundamentals/`（Python 特定） + 本目录（通用）
- **ruoyi-vue-pro**（Java）：`../ruoyi-vue-pro/01-java-fundamentals/`（Java 特定） + 本目录（通用）

## 💡 学习建议

1. **入门后端开发**：先看 01-02（数据结构算法），再看 03-04（系统网络）
2. **面试冲刺**：重点看 01-02-06（数据结构算法设计模式）
3. **工作中查漏补缺**：按需查阅各个分类
