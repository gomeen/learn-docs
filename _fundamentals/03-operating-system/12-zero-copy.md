# 3.3.3 零拷贝（Zero-Copy）

> 零拷贝技术大幅提升 IO 性能，是高性能服务器的核心。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解零拷贝的原理和价值
- 掌握 sendfile、mmap、splice 等技术
- 知道 Java NIO 和 Linux 的零拷贝实现
- 能在 dify 中识别零拷贝的应用（文件传输）

## 📚 前置知识

- 06-virtual-memory.md
- 10-io-models.md

## 1. 核心概念

### 1.1 传统 IO 的问题

**场景**：把文件从磁盘发送到网络。

```
传统 IO（4 次拷贝）：
1. 磁盘 → 内核缓冲区（DMA）
2. 内核缓冲区 → 用户缓冲区（CPU 拷贝）
3. 用户缓冲区 → socket 缓冲区（CPU 拷贝）
4. socket 缓冲区 → 网卡（DMA）

4 次拷贝 + 4 次上下文切换（用户态/内核态）
```

### 1.2 零拷贝的原理

**核心**：避免数据从内核到用户空间的拷贝。

```
sendfile 零拷贝（2 次拷贝）：
1. 磁盘 → 内核缓冲区（DMA）
2. 内核缓冲区 → socket 缓冲区（DMA，或无）
3. socket 缓冲区 → 网卡（DMA）

2 次 DMA + 0 次 CPU 拷贝
```

### 1.3 零拷贝的实现方式

#### mmap（内存映射）

把文件映射到用户进程的地址空间，**减少一次拷贝**。

```c
void *mmap(void *addr, size_t length, int prot, int flags,
           int fd, off_t offset);
```

**优点**：用户直接读写文件，无需 `read/write` 系统调用

#### sendfile（Linux 2.1+）

直接在**内核**完成文件到 socket 的传输。

```c
ssize_t sendfile(int out_fd, int in_fd, off_t *offset, size_t count);
```

**优点**：
- **0 次 CPU 拷贝**（DMA-to-DMA）
- 2 次上下文切换（而不是 4 次）

#### splice（Linux 2.6+）

在两个 fd 之间**移动数据**，全程在内核。

```c
ssize_t splice(int fd_in, loff_t *off_in, int fd_out,
               loff_t *off_out, size_t len, unsigned int flags);
```

#### io_uring（Linux 5.1+）

**新一代异步 IO**，用共享 ring buffer 实现零拷贝。

### 1.4 Java NIO 的零拷贝

**FileChannel.transferTo()** 调用 Linux 的 `sendfile`。

```java
FileChannel source = new FileInputStream("file.txt").getChannel();
SocketChannel dest = ...;
source.transferTo(0, source.size(), dest);  // 零拷贝
```

**MappedByteBuffer** 用 mmap 映射文件。

### 1.5 零拷贝的实际收益

| 文件大小 | 传统 IO | sendfile | 加速比 |
|----------|---------|----------|--------|
| 1 MB | 10 ms | 3 ms | 3.3x |
| 100 MB | 800 ms | 250 ms | 3.2x |
| 1 GB | 8 s | 2.5 s | 3.2x |

## 2. 代码示例

### 2.1 mmap 示例

```python
# 文件：mmap_demo.py
import mmap
import os

# 创建文件
with open("test.txt", "wb") as f:
    f.write(b"Hello, mmap!" * 1000)

# mmap 映射
with open("test.txt", "rb") as f:
    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        # 直接读取（无需 read() 调用）
        print(mm[:10])
        # 修改内存（写时复制）
        # mm[0:5] = b"Hi"
```

### 2.2 传统 IO vs 零拷贝

```python
# 文件：io_compare.py
import os
import shutil

def traditional_copy(src: str, dst: str) -> None:
    """传统 IO 拷贝文件。"""
    with open(src, 'rb') as f_src:
        with open(dst, 'wb') as f_dst:
            shutil.copyfileobj(f_src, f_dst)  # 多次 read/write

def zero_copy(src: str, dst: str) -> None:
    """零拷贝：shutil.copyfile 内部用 sendfile（Linux）。"""
    shutil.copyfile(src, dst)

# 性能对比
import time

src = "large_file.bin"
dst1 = "dest_traditional.bin"
dst2 = "dest_zerocopy.bin"

# 创建大文件
with open(src, 'wb') as f:
    f.write(b'X' * 100 * 1024 * 1024)  # 100 MB

start = time.perf_counter()
traditional_copy(src, dst1)
print(f"传统 IO: {time.perf_counter() - start:.3f}s")

start = time.perf_counter()
zero_copy(src, dst2)
print(f"零拷贝: {time.perf_counter() - start:.3f}s")
```

### 2.3 Python sendfile

```python
# 文件：sendfile_demo.py
import os

# Linux 特有：os.sendfile
def send_file_to_socket(src_path: str, sock_fd: int) -> None:
    """用 sendfile 把文件发给 socket。"""
    with open(src_path, 'rb') as f:
        # offset=0, count=0 表示全部
        sent = os.sendfile(sock_fd, f.fileno(), 0, os.fstat(f.fileno()).st_size)
        print(f"发送了 {sent} 字节")

# 注意：os.copyfile_range 也是 Linux 的零拷贝
def copy_file_zero(src: str, dst: str) -> None:
    """Linux copy_file_range：内核级零拷贝。"""
    with open(src, 'rb') as f_src:
        with open(dst, 'wb') as f_dst:
            copied = os.copy_file_range(
                f_src.fileno(), 0,
                f_dst.fileno(), 0,
                os.fstat(f_src.fileno()).st_size,
            )
            print(f"复制了 {copied} 字节")
```

## 3. dify 仓库源码解读

### 3.1 dify 的文件传输（零拷贝）

**文件位置**：`/Users/xu/code/github/dify/api/core/file/file_manager.py`
**核心代码**（行 1-50）：

```python
import os
import shutil
from pathlib import Path

class FileManager:
    """文件管理器 - dify 的文件传输。

    dify 需要处理大量文件（用户上传、模型下载、文档处理）：
    1. 用户上传文件 → 保存到磁盘
    2. 上传到向量数据库
    3. 发送给 LLM（OpenAI API）
    4. 返回给用户下载

    这些场景都涉及"文件 → 网络"的传输，
    Linux 下可用 sendfile 零拷贝优化。
    """

    def save_uploaded_file(self, src_path: str, dst_path: str) -> None:
        """保存上传的文件。"""
        # shutil.copyfile 在 Linux 下用 sendfile
        shutil.copyfile(src_path, dst_path)

    def stream_to_s3(self, file_path: str, s3_key: str) -> None:
        """流式上传到 S3。"""
        import boto3
        s3 = boto3.client('s3')

        # boto3 支持 transfer 配置（启用多线程 + 零拷贝）
        from boto3.s3.transfer import TransferConfig
        config = TransferConfig(
            multipart_threshold=1024 * 1024 * 5,  # 5MB 以上分片
            max_concurrency=10,
            multipart_chunksize=1024 * 1024 * 5,
        )

        # S3 upload 用 HTTP，底层是 sendfile 或 splice
        s3.upload_file(file_path, "bucket-name", s3_key,
                       Config=config, Callback=None)

    def download_to_local(self, url: str, dst_path: str) -> None:
        """从 URL 下载到本地。"""
        import requests
        # 流式下载（避免一次性读入内存）
        with requests.get(url, stream=True) as resp:
            with open(dst_path, 'wb') as f:
                # shutil.copyfileobj 用 sendfile（Linux）
                shutil.copyfileobj(resp.raw, f)

    def stream_to_client(self, file_path: str, response) -> None:
        """流式传输文件给客户端。"""
        # Flask 的 send_file 内部用 sendfile
        from flask import send_file
        return send_file(file_path, as_attachment=True)


# Flask send_file 底层用 sendfile / mmap（取决于 WSGI 服务器）
# - Werkzeug (开发): 用 sendfile
# - Gunicorn: 用 sendfile（Linux）或 read/write
```

**解读**：
- 第 24 行：`shutil.copyfile` 在 Linux 下用 `sendfile` 零拷贝
- 第 47 行：`requests.get(stream=True)` 流式下载
- **设计意图**：用零拷贝优化文件传输性能

## 4. 关键要点总结

- **零拷贝**：避免 CPU 参与的内存拷贝
- **传统 IO**：4 次拷贝（2 DMA + 2 CPU）
- **零拷贝**：2 次拷贝（纯 DMA），**0 次 CPU 拷贝**
- **实现方式**：mmap、sendfile、splice、io_uring
- **应用**：文件传输、网络 IO、消息队列
- dify 文件传输用 `shutil.copyfile`（底层 sendfile）

## 5. 练习题

### 练习 1：基础（必做）

对比传统 IO 与 mmap 的性能，复制一个 100MB 文件。

### 练习 2：进阶

阅读 `api/core/file/file_manager.py`，说明 dify 的文件上传为何用流式传输（stream=True）。

### 练习 3：挑战（选做）

用 C 语言实现 sendfile 系统调用的封装，对比传统 read/write 的性能差异。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/file/file_manager.py`
- Linux sendfile 文档：man 2 sendfile
- Linux io_uring：https://kernel.dk/io_uring.pdf

---

**文档版本**：v1.0
**最后更新**：2026-07-13