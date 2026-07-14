# 01 - 数据结构

> 后端开发的基石。理解数据结构是写出高效代码的前提，也是面试必考。

## 模块 1.1 基础概念

- [ ] [1.1 时间复杂度与空间复杂度](./01-complexity.md)
- [ ] [1.2 大 O 表示法详解](./02-big-o.md)
- [ ] [1.3 数组与动态数组](./03-array.md)
- [ ] [1.4 链表：单链表 / 双向链表 / 循环链表](./04-linked-list.md)
- [ ] [1.5 栈（Stack）与队列（Queue）](./05-stack-queue.md)

## 模块 1.2 树结构

- [ ] [2.1 二叉树基础](./06-binary-tree.md)
- [ ] [2.2 二叉搜索树（BST）](./07-bst.md)
- [ ] [2.3 平衡二叉树：AVL 树](./08-avl.md)
- [ ] [2.4 红黑树（HashMap / TreeMap 底层）](./09-red-black-tree.md)
- [ ] [2.5 B 树 / B+ 树（数据库索引底层）](./10-b-tree.md)
- [ ] [2.6 堆（Heap）与优先队列](./11-heap.md)
- [ ] [2.7 字典树（Trie）](./12-trie.md)

## 模块 1.3 哈希结构

- [ ] [3.1 哈希表原理](./13-hash-table.md)
- [ ] [3.2 哈希冲突解决：链地址法 / 开放地址法](./14-hash-collision.md)
- [ ] [3.3 一致性哈希（分布式系统）](./15-consistent-hashing.md)
- [ ] [3.4 布隆过滤器（Bloom Filter）](./16-bloom-filter.md)

## 模块 1.4 高级结构

- [ ] [4.1 图基础：邻接表 / 邻接矩阵](./17-graph.md)
- [ ] [4.2 并查集（Union-Find）](./18-union-find.md)
- [ ] [4.3 跳表（SkipList，Redis ZSet 底层）](./19-skiplist.md)
- [ ] [4.4 LSM 树（LevelDB / RocksDB）](./20-lsm-tree.md)

## 🎯 对应 dify/ruoyi 仓库

- **dify**：Redis ZSet 用跳表（`api/extensions/ext_redis.py`）
- **ruoyi-vue-pro**：HashMap 在 Java 集合中大量使用，Redisson ZSet 底层也是跳表
