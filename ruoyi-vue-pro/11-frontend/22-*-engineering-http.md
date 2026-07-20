# 小验证：Vite / Lint / pnpm / CSS 工程化

> 覆盖：
- [Vite](./18-vite.md)
- [ESLint/Prettier](./19-lint.md)
- [pnpm](./20-pnpm.md)
- [UnoCSS/Tailwind](./21-css.md)
>
> 预计：30～45 分钟 · 改 yudao-ui 仓库

## 背景

先摸清前端工程骨架：构建、包管理、规范与样式方案。

## 需求

在 yudao-ui-admin-vue3（路径以仓库实际为准）：

1. 阅读 `vite.config`：说明 dev server、alias、代理相关配置位置。
2. 配好或确认本地代理指向后端的方式（可先不发起真实请求）。
3. 运行 lint（或 IDE 检查）修复自己改动引入的问题。
4. 说明 pnpm workspace/monorepo 是否使用及常用命令（`pnpm i` / `pnpm dev` 等）。
5. 指出项目 CSS 方案（UnoCSS / SCSS / 其它）并改一处无害样式验证热更新。

## 提示

- `.env.local` 不要提交密钥。
- 代理路径要与 `admin-api` 前缀一致。
- 只改自己的练习文件，避免大范围 format。

## 验收标准

- [ ] vite 关键配置位置说明正确
- [ ] 包管理命令记录
- [ ] lint 通过（自己改动范围）
- [ ] CSS 方案说明 + 一处样式验证
- [ ] 环境文件安全注意点说明

## 延伸（选做）

- 配 UnoCSS 原子类改一处样式。
- 对比 `pnpm` 与 `npm` 在该仓库的 lockfile 差异原因。
