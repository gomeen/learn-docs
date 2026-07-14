# 03 - 操作系统

> 理解操作系统才能理解后端程序的运行环境：高并发、内存管理、IO 模型。

## 模块 3.1 进程与线程

- [ ] [1.1 进程基础与进程控制块（PCB）](./01-process.md)
- [ ] [1.2 线程基础：用户线程 vs 内核线程](./02-thread.md)
- [ ] [1.3 进程间通信（IPC）：管道 / 消息队列 / 共享内存 / 信号量 / Socket](./03-ipc.md)
- [ ] [1.4 协程（Coroutine）：用户态线程](./04-coroutine.md)
- [ ] [1.5 进程调度算法：FCFS / SJF / 时间片轮转](./05-scheduling.md)

## 模块 3.2 内存管理

- [ ] [2.1 虚拟内存与分页](./06-virtual-memory.md)
- [ ] [2.2 内存分配：malloc / 伙伴系统 / slab](./07-memory-allocation.md)
- [ ] [2.3 内存分页 vs 分段](./08-paging-segmentation.md)
- [ ] [2.4 页面置换算法：LRU / FIFO / Clock](./09-page-replacement.md)

## 模块 3.3 IO 模型

- [ ] [3.1 五种 IO 模型：阻塞 / 非阻塞 / IO 复用 / 信号驱动 / 异步](./10-io-models.md)
- [ ] [3.2 select / poll / epoll 详解](./11-io-multiplexing.md)
- [ ] [3.3 零拷贝（Zero-Copy）](./12-zero-copy.md)
- [ ] [3.4 同步 / 异步 / 阻塞 / 非阻塞 区别](./13-sync-async.md)

## 模块 3.4 并发与锁

- [ ] [4.1 死锁：四个必要条件 / 银行家算法](./14-deadlock.md)
- [ ] [4.2 乐观锁 vs 悲观锁](./15-lock-types.md)
- [ ] [4.3 CAS（Compare-And-Swap）](./16-cas.md)
- [ ] [4.4 内存模型与可见性（Java / Python GIL）](./17-memory-model.md)
- [ ] [4.5 volatile 与 happens-before](./18-volatile.md)

## 模块 3.5 其他

- [ ] [5.1 文件系统：inode / ext4 / xfs](./19-file-system.md)
- [ ] [5.2 中断与系统调用](./20-interrupt-syscall.md)

## 🎯 与后端开发的关联

- **高并发**：IO 多路复用 → asyncio / Netty / Nginx
- **内存管理**：JVM GC → Java 应用
- **锁机制**：数据库事务 → 乐观锁 / 悲观锁
- **协程**：Python asyncio / Go goroutine
