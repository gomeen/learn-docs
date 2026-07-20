# 小验证：pytest 核心与 dify 测试布局

> 覆盖：
> - [01-pytest-basics](./01-pytest-basics.md)
> - [02-pytest-fixture](./02-pytest-fixture.md)
> - [03-pytest-parametrize](./03-pytest-parametrize.md)
> - [04-pytest-mock](./04-pytest-mock.md)
> - [05-pytest-plugins](./05-pytest-plugins.md)
> - [06-pytest-in-dify](./06-pytest-in-dify.md)
>
> 预计：45～75 分钟 · 本地练习或改 dify 仓库

## 背景

pytest 是 dify 后端质量底盘。验证：写参数化+fixture+mock 测试，并对照仓库布局。

## 需求

1. 本地或仓库 `tests/` 风格下新增测试文件：对一个纯函数（可自写 `normalize_email`）做 parametrize ≥5 例。
2. 用 fixture 提供临时配置；用 monkeypatch/mock 屏蔽网络调用。
3. 阅读 dify `api/tests/` 布局与 `pyproject.toml`/`Makefile` 测试命令，`NOTES.md` 记录如何跑单文件。
4. （推荐）向仓库某纯逻辑补 1 个真正的单元测试并本地跑通。

## 提示

- `api/tests/`、`api/Makefile`
- 优先测纯函数，避免重依赖

## 验收标准

- [ ] parametrize 用例可收集执行
- [ ] mock 后无真实外网请求
- [ ] NOTES 含准确测试命令
- [ ] 至少 1 个测试失败信息是可读的（刻意造 1 次再修）

## 延伸（选做）

加上 `pytest-cov` 看该文件覆盖率。
