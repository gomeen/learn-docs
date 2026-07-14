# 3.5.1 文件系统：inode / ext4 / xfs

> 文件系统是操作系统管理磁盘的方式。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 inode 的结构和作用
- 掌握 ext4 / xfs 等常见文件系统的特点
- 能在 dify 中识别文件系统的应用（文件存储）

## 📚 前置知识

- 计算机基础

## 1. 核心概念

### 1.1 文件系统的作用

**文件系统**（File System）管理磁盘上的数据：
- **组织**：文件如何存放
- **查找**：如何找到文件
- **保护**：权限和访问控制

### 1.2 inode 的概念

**inode**（index node）是 Unix/Linux 文件系统的核心数据结构。

```
文件 = 文件名 + inode
文件名：方便用户使用
inode：存储文件的元数据
```

**inode 存储的元数据**：
- 文件类型（普通/目录/链接）
- 权限（rwxrwxrwx）
- 所有者（UID/GID）
- 文件大小
- 时间戳（atime、mtime、ctime）
- **数据块指针**（指向实际数据）
- 链接数（硬链接计数）

**注意**：inode **不存储文件名**！

### 1.3 inode 与文件名的关系

```
/home/user/file.txt
       ↓
   目录项：file.txt → inode 12345
                          ↓
                       inode 12345
                          ↓
                       数据块
```

### 1.4 ext4 文件系统

**ext4**（Fourth Extended File System）是 Linux 最常用的文件系统。

**特点**：
- 最大文件 16 TB
- 最大卷 1 EB
- extents（块组）代替块映射
- 日志（journal）保证一致性
- 延迟分配

### 1.5 xfs 文件系统

**xfs** 是高性能 64 位日志文件系统。

**特点**：
- 大文件支持好（最大 8 EB）
- 高并发（基于分配组）
- 在线扩容（不需卸载）
- 高性能（日志 + B+ 树）

### 1.6 文件系统的层次

```
VFS（虚拟文件系统）层
  ↓
ext4 / xfs / ntfs 驱动
  ↓
通用块层（I/O 调度）
  ↓
磁盘驱动
```

### 1.7 文件存储的选择

| 场景 | 文件系统 |
|------|----------|
| 通用 Linux | ext4 / xfs |
| 大文件（视频） | xfs |
| 高并发数据库 | xfs |
| Windows | NTFS |
| macOS | APFS |
| 嵌入式 | SquashFS |

## 2. 代码示例

### 2.1 查看 inode 信息

```python
# 文件：inode_demo.py
import os
import stat

def show_inode_info(path: str) -> None:
    """显示文件的 inode 信息。"""
    st = os.stat(path)
    print(f"路径: {path}")
    print(f"inode: {st.st_ino}")
    print(f"大小: {st.st_size} bytes")
    print(f"权限: {oct(st.st_mode)}")
    print(f"硬链接数: {st.st_nlink}")
    print(f"所有者 UID: {st.st_uid}")
    print(f"所有者 GID: {st.st_gid}")
    print(f"atime: {st.st_atime}")
    print(f"mtime: {st.st_mtime}")
    print(f"ctime: {st.st_ctime}")

    # 文件类型
    if stat.S_ISREG(st.st_mode):
        print("类型: 普通文件")
    elif stat.S_ISDIR(st.st_mode):
        print("类型: 目录")

# 测试
show_inode_info(__file__)
```

### 2.2 硬链接 vs 软链接

```python
# 文件：link_demo.py
import os

# 硬链接：多个文件名指向同一 inode
os.link("original.txt", "hardlink.txt")
print(f"original inode: {os.stat('original.txt').st_ino}")
print(f"hardlink inode: {os.stat('hardlink.txt').st_ino}")  # 相同

# 软链接：自己的 inode，存的是路径
os.symlink("original.txt", "symlink.txt")
print(f"symlink inode: {os.stat('symlink.txt').st_ino}")  # 不同

# 硬链接数
print(f"硬链接数: {os.stat('original.txt').st_nlink}")  # 2（原始 + 硬链接）
```

### 2.3 文件 IO 模式

```python
# 文件：file_io_demo.py
import os
import time

def benchmark_write_mode(filename, mode, size_mb=10):
    """对比不同写模式的性能。"""
    size = size_mb * 1024 * 1024
    chunk = b'X' * 1024

    start = time.perf_counter()
    with open(filename, mode) as f:
        for _ in range(size // len(chunk)):
            f.write(chunk)
        if 'b' not in mode:
            f.flush()
            os.fsync(f.fileno())  # 刷盘

    elapsed = time.perf_counter() - start
    print(f"{mode}: {elapsed:.3f}s ({size_mb/elapsed:.1f} MB/s)")

# 对比
benchmark_write_mode("test1.txt", "w")   # 文本模式
benchmark_write_mode("test2.txt", "wb")  # 二进制模式（更快）
```

## 3. dify 仓库源码解读

### 3.1 dify 的文件存储

**文件位置**：`/Users/xu/code/github/dify/api/core/file/file_manager.py`
**核心代码**（行 50-90）：

```python
import os
import shutil
from pathlib import Path

class FileStorage:
    """dify 的文件存储。

    dify 用本地文件系统存储上传的文件：
    - 用户上传文件 → 保存到 /path/to/storage/
    - 文件名 = UUID（避免冲突）
    - 元数据存数据库（filename, size, mime_type）

    文件系统选择：
    - 开发：本地 ext4
    - 生产：xfs（高并发、大文件）
    - 分布式：S3 / OSS（不是本地文件系统）
    """

    def __init__(self, storage_path: str = "/tmp/dify-storage"):
        self._storage = Path(storage_path)
        self._storage.mkdir(parents=True, exist_ok=True)

    def save_file(self, file_obj, filename: str) -> dict:
        """保存文件。"""
        import uuid
        # 生成 UUID 避免冲突
        file_id = str(uuid.uuid4())
        # 真实文件名（用户原始名）
        ext = os.path.splitext(filename)[1]
        # 存储文件名（UUID）
        storage_name = f"{file_id}{ext}"
        storage_path = self._storage / storage_name

        # 写入文件
        with open(storage_path, 'wb') as f:
            shutil.copyfileobj(file_obj, f)

        # 返回元数据
        stat = os.stat(storage_path)
        return {
            "id": file_id,
            "filename": filename,
            "storage_path": str(storage_path),
            "size": stat.st_size,
            "inode": stat.st_ino,  # inode 号
        }

    def read_file(self, file_id: str) -> bytes:
        """读取文件。"""
        files = list(self._storage.glob(f"{file_id}.*"))
        if not files:
            raise FileNotFoundError(file_id)
        with open(files[0], 'rb') as f:
            return f.read()

    def delete_file(self, file_id: str) -> None:
        """删除文件。"""
        for file in self._storage.glob(f"{file_id}.*"):
            file.unlink()


# 生产环境考虑：
# 1. 文件分片（>100MB）：避免单文件过大
# 2. 定期清理：删除超过 7 天的临时文件
# 3. 备份：重要文件用 rsync 备份
# 4. 监控：磁盘使用率、inode 使用率
```

**解读**：
- 第 24 行：UUID 避免文件名冲突
- 第 32 行：`shutil.copyfileobj` 流式写入（内存友好）
- 第 39 行：保存 inode 号（用于调试）
- **设计意图**：用本地文件系统 + UUID 命名，简单可靠

## 4. 关键要点总结

- **inode**：Unix 文件系统的核心，存储元数据
- **文件名**与 inode 分离
- **硬链接**：多个文件名同 inode
- **软链接**：独立 inode，存路径
- ext4：通用 Linux；xfs：大文件、高性能
- dify 用本地文件系统存储上传文件

## 5. 练习题

### 练习 1：基础（必做）

写一个 Python 脚本，遍历目录并打印每个文件的 inode 号、文件名、大小。

### 练习 2：进阶

阅读 `api/core/file/file_manager.py`，说明 dify 为何用 UUID 作为存储文件名。

### 练习 3：挑战（选做）

实现一个简单的文件系统模拟：创建 inode 表、数据块管理，支持创建、删除文件。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/file/file_manager.py`
- ext4 文档：https://ext4.wiki.kernel.org/
- 《操作系统概念》第 11 章 文件系统

---

**文档版本**：v1.0
**最后更新**：2026-07-13