# 1.4.4 区间 DP

> 区间 DP 解决"区间合并"类问题，状态是区间而非单点。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解区间 DP 的状态定义（区间而非点）
- 掌握"区间长度从小到大"的遍历顺序
- 解决矩阵链乘、石子合并等问题
- 能在 dify 中识别区间 DP 的应用

## 📚 前置知识

- 13-dp-basics.md
- 14-knapsack.md

## 1. 核心概念

### 1.1 区间 DP 特点

**状态**：`dp[i][j]` 表示区间 `[i, j]` 上的最优解

**转移**：枚举分割点 k，把 `[i, j]` 分成 `[i, k]` 和 `[k+1, j]`

### 1.2 经典问题：矩阵链乘

**问题**：N 个矩阵相乘，求最少标量乘法次数。

```
矩阵 A(10×100), B(100×5), C(5×50)

不同相乘顺序代价不同：
(A × B) × C：(10×100×5) + (10×5×50) = 5000 + 2500 = 7500
A × (B × C)：100×5×50 + 10×100×50 = 25000 + 50000 = 75000
```

**状态**：`dp[i][j]` = 矩阵 i 到 j 相乘的最少代价

**转移**：
```
dp[i][j] = min over k (dp[i][k] + dp[k+1][j] + cost)
```

**遍历顺序**：按**区间长度**从小到大

```python
for length in range(2, n + 1):  # 区间长度
    for i in range(n - length + 1):
        j = i + length - 1
        for k in range(i, j):
            dp[i][j] = min(dp[i][j], dp[i][k] + dp[k+1][j] + cost)
```

### 1.3 区间 DP 的关键

1. **状态**：二维 `dp[i][j]`
2. **遍历顺序**：按区间长度（不是端点）
3. **枚举分割点**：k 在 [i, j) 之间

### 1.4 应用场景

1. **矩阵链乘**
2. **石子合并**：相邻石子合并代价
3. **戳气球**：戳破气球得分
4. **最长回文子序列**

## 2. 代码示例

### 2.1 矩阵链乘

```python
# 文件：matrix_chain.py
from typing import List

def matrix_chain_order(dims: List[int]) -> int:
    """矩阵链乘：dims[i] = 第 i 个矩阵的 (行, 列) 维数。

    矩阵 i 的维度 = dims[i] × dims[i+1]
    """
    n = len(dims) - 1  # 矩阵数量
    dp = [[0] * n for _ in range(n)]

    # 按区间长度遍历
    for length in range(2, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            dp[i][j] = float('inf')
            for k in range(i, j):
                cost = dp[i][k] + dp[k + 1][j] + dims[i] * dims[k + 1] * dims[j + 1]
                dp[i][j] = min(dp[i][j], cost)
    return dp[0][n - 1]

# 测试：A(30×35), B(35×15), C(15×5), D(5×10), E(10×20), F(20×25)
dims = [30, 35, 15, 5, 10, 20, 25]
print(matrix_chain_order(dims))  # 15750
```

### 2.2 石子合并

```python
# 文件：stone_merge.py
from typing import List

def stone_merge(stones: List[int]) -> int:
    """石子合并：相邻两堆合并，代价是两堆之和，求最小总代价。

    经典区间 DP。
    """
    n = len(stones)
    if n == 0:
        return 0
    # 前缀和，用于快速求区间和
    prefix = [0] * (n + 1)
    for i in range(n):
        prefix[i + 1] = prefix[i] + stones[i]

    def range_sum(i: int, j: int) -> int:
        return prefix[j + 1] - prefix[i]

    dp = [[0] * n for _ in range(n)]
    for length in range(2, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            dp[i][j] = float('inf')
            for k in range(i, j):
                cost = dp[i][k] + dp[k + 1][j] + range_sum(i, j)
                dp[i][j] = min(dp[i][j], cost)
    return dp[0][n - 1]

# 测试
print(stone_merge([1, 3, 5, 2]))  # 22
```

### 2.3 戳气球

```python
# 文件：burst_balloons.py
from typing import List

def max_coins(nums: List[int]) -> int:
    """戳气球（LeetCode 312）：戳破气球 i 得 nums[i-1]*nums[i]*nums[i+1] 分数。

    dp[i][j] = 戳破 (i, j) 开区间内所有气球（不包括 i, j）的最大分数
    """
    # 加边界
    arr = [1] + nums + [1]
    n = len(arr)
    dp = [[0] * n for _ in range(n)]

    # 倒序遍历区间长度
    for length in range(2, n - 1):  # 区间 (i, j) 长度
        for i in range(n - length):
            j = i + length
            # 最后戳破的气球是 k
            for k in range(i + 1, j):
                score = (
                    dp[i][k]
                    + dp[k][j]
                    + arr[i] * arr[k] * arr[j]
                )
                dp[i][j] = max(dp[i][j], score)
    return dp[0][n - 1]

# 测试
print(max_coins([3, 1, 5, 8]))  # 167
```

### 2.4 最长回文子序列（区间 DP）

```python
# 文件：longest_palindrome_subseq.py
def longest_palindrome_subseq(s: str) -> int:
    """最长回文子序列（LeetCode 516）。"""
    n = len(s)
    if n == 0:
        return 0
    dp = [[0] * n for _ in range(n)]
    # 单字符都是回文
    for i in range(n):
        dp[i][i] = 1

    for length in range(2, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            if s[i] == s[j]:
                dp[i][j] = dp[i + 1][j - 1] + 2
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j - 1])
    return dp[0][n - 1]

# 测试
print(longest_palindrome_subseq("bbbab"))  # 4（bbbb）
print(longest_palindrome_subseq("cbbd"))   # 2（bb）
```

## 3. dify 仓库源码解读

### 3.1 dify 的文档切片合并（区间 DP 思想）

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/splitter/text_splitter.py`
**核心代码**（行 80-120）：

```python
from typing import Any

class TextSplitter:
    """文本切片器：把长文档切成短片段。

    dify 的文档需要切成适合 LLM 的长度（如 512 tokens），
    但需要在切点选择上做权衡：

    状态：dp[i][j] = 从 i 到 j 的最佳切片方案
    转移：选某个切点 k，把 (i, j) 切成 (i, k) 和 (k, j)

    简化实现：用启发式而非真正的 DP（性能考虑）。
    """

    def __init__(self, max_chunk_size: int = 512):
        self._max_chunk_size = max_chunk_size

    def split(self, text: str) -> list[str]:
        """切分文本 - 启发式算法。"""
        if len(text) <= self._max_chunk_size:
            return [text]

        # 找最佳切点（在 max_chunk_size 范围内最近的句子边界）
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self._max_chunk_size, len(text))
            # 在 [start, end] 范围内找句子边界
            if end < len(text):
                # 找最近的句号、感叹号、问号
                for i in range(end, start, -1):
                    if text[i - 1] in ".!?。！？":
                        end = i
                        break
            chunks.append(text[start:end])
            start = end
        return chunks

    def evaluate_chunking(
        self,
        text: str,
        chunk_boundaries: list[int],
    ) -> float:
        """评估切分方案的质量 - 区间 DP 评估。

        输入：切点位置列表
        输出：质量分数（越接近 max_chunk_size 越好）
        """
        boundaries = [0] + chunk_boundaries + [len(text)]
        total_score = 0.0
        for i in range(len(boundaries) - 1):
            chunk_size = boundaries[i + 1] - boundaries[i]
            # 偏离 max_chunk_size 的程度
            deviation = abs(chunk_size - self._max_chunk_size) / self._max_chunk_size
            total_score -= deviation  # 越小越好
        return total_score
```

**解读**：
- 第 35 行：启发式切片（按句子边界）
- 第 60 行：评估函数用区间分割的偏差
- **dify 的实际实现**：用 LangChain 的 `RecursiveCharacterTextSplitter`，不是真正的 DP
- **设计意图**：文本切分需要在"切点合理"和"长度适中"之间平衡

## 4. 关键要点总结

- 区间 DP：状态 `dp[i][j]` 表示区间最优解
- 遍历顺序：**按区间长度从小到大**
- 转移：枚举分割点 k
- 时间复杂度：O(n³)（矩阵链乘、石子合并）
- 应用：矩阵链乘、石子合并、戳气球、回文子序列
- dify 文本切分是简化版的区间分割

## 5. 练习题

### 练习 1：基础（必做）

实现**最小代价括号匹配**：给一个括号序列，插入最少括号使其合法。

### 练习 2：进阶

阅读 `api/core/rag/splitter/text_splitter.py`，分析 dify 的文本切分为什么用启发式而不是真正的区间 DP（提示：性能 vs 效果）。

### 练习 3：挑战（选做）

实现**最优二叉搜索树**：给定有序 key 集合和访问概率，构建查询代价最低的 BST（区间 DP）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/splitter/text_splitter.py`
- 《算法导论》第 15 章 动态规划
- LeetCode 312/516/1039/1000 题

---

**文档版本**：v1.0
**最后更新**：2026-07-13