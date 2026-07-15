# 11.7.3 小程序发布流程

> 掌握 uni-app 项目的小程序发布流程：HBuilderX 构建、上传微信开发者工具、提交审核。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 uni-app 项目的小程序发布完整流程
- 配置 manifest.json 中的 AppID
- 在 HBuilderX 中构建并上传
- 提交审核与发布

## 📚 前置知识

- uni-app（详见 [uni-app](./30-uniapp.md)）
- 微信小程序账号申请

## 1. 核心概念

### 1.1 小程序发布流程总览

```
1. 注册小程序账号（微信公众平台）
   ↓ 获取 AppID
2. 在 manifest.json 配置 AppID
   ↓
3. HBuilderX 中点"发行 → 微信小程序"
   ↓ 自动编译为微信小程序代码
4. 在微信开发者工具中预览测试
   ↓
5. 上传代码（微信开发者工具）
   ↓
6. 微信公众平台提交审核
   ↓
7. 审核通过后发布上线
```

### 1.2 关键概念

| 概念 | 说明 |
|------|------|
| **AppID** | 小程序的唯一标识，wx + 16 位字符 |
| **AppSecret** | 小程序密钥，用于服务端 API |
| **小程序后台** | https://mp.weixin.qq.com 管理小程序 |
| **微信开发者工具** | 调试、上传代码的 IDE |

### 1.3 所需准备

| 准备项 | 说明 |
|--------|------|
| 小程序 AppID | 必须是已注册的小程序 |
| 邮箱（未注册过微信） | 用于注册小程序账号 |
| 主体认证 | 个人 / 企业（企业需要营业执照） |
| 服务器域名 | 小程序必须 HTTPS 后台 |
| 备案 | 国内必须 ICP 备案 |

## 2. 代码示例

### 2.1 manifest.json 配置

```json
{
  "name": "芋道管理",
  "appid": "__UNI__WM12345",    // uni-app 项目标识
  "description": "芋道管理系统移动端",
  "versionName": "1.0.0",
  "versionCode": "100",
  "transformPx": false,
  "app-plus": {
    "usingComponents": true,
    "nvueStyleCompiler": "uni-app",
    "compilerVersion": 3,
    "splashscreen": {
      "alwaysShowBeforeRender": true,
      "waiting": true,
      "autoclose": true,
      "delay": 0
    },
    "modules": {},
    "distribute": {
      "android": { "permissions": [...] },
      "ios": {},
      "sdkConfigs": {}
    }
  },
  "quickapp": {},
  "mp-weixin": {
    "appid": "wx1234567890abcdef",   // 微信小程序 AppID
    "setting": {
      "urlCheck": false,
      "es6": true,
      "minified": true
    },
    "usingComponents": true,
    "permission": {
      "scope.userLocation": {
        "desc": "你的位置信息将用于考勤打卡"
      }
    },
    "requiredPrivateInfos": [],
    "lazyCodeLoading": "requiredComponents"
  },
  "h5": {
    "router": { "mode": "hash" },
    "title": "芋道管理"
  },
  "vueVersion": "3"
}
```

### 2.2 后端域名白名单

小程序要求所有请求 URL 必须在 **request 合法域名** 中配置：

```
# 微信公众平台 → 开发 → 开发设置 → 服务器域名
request 合法域名：
  https://api.yudao.com
  https://api.yudao.cn

uploadFile 合法域名：
  https://api.yudao.com

downloadFile 合法域名：
  https://api.yudao.com
```

后端必须用 HTTPS。

### 2.3 编译配置：HBuilderX

```bash
# 1. 在 HBuilderX 中打开项目
# 2. 菜单：发行 → 小程序-微信 (仅适用于 uni-app)
# 3. 填写小程序名称和 AppID
# 4. 点击"发行"
# 5. 在 /unpackage/dist/dev/mp-weixin/ 生成微信小程序代码
```

### 2.4 自动化构建脚本

```json
// package.json
{
  "scripts": {
    "dev:mp-weixin": "uni -p mp-weixin",
    "build:mp-weixin": "uni build -p mp-weixin",
    "build:h5": "uni build",
    "build:app": "uni build -p app"
  }
}
```

```bash
# 命令行编译（不依赖 HBuilderX）
pnpm build:mp-weixin

# 输出目录：dist/build/mp-weixin/
```

### 2.5 CI/CD 自动发布（miniprogram-ci）

```bash
# 安装 miniprogram-ci
pnpm add -D miniprogram-ci

# 上传代码脚本
node scripts/upload-miniprogram.js
```

```js
// scripts/upload-miniprogram.js
const ci = require('miniprogram-ci')

const project = new ci.Project({
  appid: 'wx1234567890abcdef',
  type: 'miniProgram',
  projectPath: './dist/build/mp-weixin',
  privateKeyPath: './private.key',
  ignores: ['node_modules/**/*']
})

ci.upload({
  project,
  version: '1.0.0',
  desc: '自动化发布',
  setting: { es6: true, minify: true }
}).then(res => {
  console.log('上传成功:', res)
})
```

### 2.6 常见错误：AppID 配错

```json
// ❌ 错误：填成 uni-app 的 appid（__UNI__xxx）
{
  "mp-weixin": {
    "appid": "__UNI__WM12345"  // 错！这是 uni-app 项目标识
  }
}

// ✅ 正确：填微信小程序 AppID（wx 开头）
{
  "mp-weixin": {
    "appid": "wx1234567890abcdef"
  }
}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 uni-app 项目位置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-uniapp/`

虽然本仓库只有 README，但根据公开约定，发布流程如下：

```
yudao-ui-admin-uniapp/
├── src/                              # 源码
├── manifest.json                     # 小程序 AppID 配置
├── pages.json                        # 路由配置
└── unpackage/dist/dev/mp-weixin/     # 编译产物（编译后生成）
```

### 3.2 后端域名配置约定

ruoyi 后端部署在：
- 开发：`http://localhost:48080`（本地，HBuilderX 调试模式可绕过）
- 测试：`https://test-api.yudao.com`
- 生产：`https://api.yudao.com`

需要在微信公众平台把以上域名加白。

### 3.3 多平台发布矩阵

| 平台 | 命令 | 注意事项 |
|------|------|---------|
| 微信小程序 | `uni build -p mp-weixin` | 需要 AppID |
| 支付宝小程序 | `uni build -p mp-alipay` | 需要小程序公钥私钥 |
| 抖音小程序 | `uni build -p mp-toutiao` | 需要 AppID |
| H5 | `uni build` | 无需 AppID |
| Android App | `uni build -p app` | 需要证书 |
| iOS App | `uni build -p app` | 需要 Apple 证书 |

### 3.4 与 PC 端接口的复用

```ts
// yudao-ui-admin-uniapp/src/api/mes/wm/sn/index.ts（约定）
import request from '@/utils/request'  // 封装了 uni.request

export const getSnPage = (params: any) => {
  return request({
    url: '/mes/wm/sn/page',
    method: 'GET',
    data: params
  })
}
```

**URL 完全和 PC 端一致**（`/mes/wm/sn/page`），所以同一套后端可以同时服务 PC + 移动端。

## 4. 发布流程详解

### 4.1 第一步：注册小程序账号

```
1. 访问 https://mp.weixin.qq.com
2. 立即注册 → 选择"小程序"
3. 填写邮箱（未注册过微信）、密码
4. 邮箱激活
5. 填写主体信息：
   - 个人：身份证
   - 企业：营业执照 + 对公账户验证
6. 获取 AppID（个人版）
```

### 4.2 第二步：配置 manifest.json

```json
{
  "mp-weixin": {
    "appid": "wx1234567890abcdef",
    "setting": {
      "urlCheck": false,           // 调试期可关闭，正式版开启
      "es6": true,
      "minified": true,
      "postcss": true
    }
  }
}
```

### 4.3 第三步：HBuilderX 发行

```
1. HBuilderX 打开项目
2. 菜单：发行 → 小程序-微信
3. 弹出配置：
   - 小程序名称：自动读取 manifest.json
   - AppID：自动读取
4. 点击"发行"
5. 自动编译并打开微信开发者工具
```

### 4.4 第四步：微信开发者工具上传

```
1. 微信开发者工具自动打开预览
2. 测试功能正常后，点右上角"上传"
3. 填写版本号和项目备注
4. 点击"上传"
5. 上传成功 → 微信公众平台会看到新版本
```

### 4.5 第五步：提交审核

```
1. 登录 https://mp.weixin.qq.com
2. 版本管理 → 开发版本
3. 点击"提交审核"
4. 填写：
   - 服务类目（如：工具 → 企业管理）
   - 标签
   - 测试账号（如果有登录功能）
5. 提交审核 → 等待 1-3 天
```

### 4.6 第六步：发布上线

```
审核通过后：
1. 版本管理 → 审核版本
2. 点击"发布"
3. 全网用户即可访问
```

## 5. 关键要点总结

- **AppID**：微信小程序的唯一标识（wx 开头）
- **manifest.json**：uni-app 的核心配置文件，含各平台 AppID
- **服务器域名**：必须在微信公众平台加白，必须 HTTPS
- **HBuilderX**：最简发布工具（菜单：发行 → 小程序-微信）
- **miniprogram-ci**：命令行发布工具，可接入 CI/CD
- **后端 URL 一致**：uni-app 与 PC 端调同一个后端接口
- **多平台构建**：mp-weixin / mp-alipay / h5 / app 通过 `uni build -p xxx` 切换

## 6. 练习题

### 练习 1：基础（必做）

为 SN 码 uni-app 项目配置 `manifest.json`，填入：
- 微信小程序 AppID
- 服务器域名
- 应用名称、版本号

### 练习 2：进阶

实现"版本检查更新"：每次启动小程序，调用 `wx.getUpdateManager` 检查更新，有新版本提示用户重启。

### 练习 3：挑战（选做）

把小程序发布流程接入 CI/CD：
- GitHub Actions 监听 tag 推送
- 自动构建 `mp-weixin` 产物
- 用 miniprogram-ci 自动上传到微信公众平台

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-uniapp/`
- uni-app 微信小程序发布文档：https://uniapp.dcloud.net.cn/quickstart-app.html
- 微信小程序官方文档：https://developers.weixin.qq.com/miniprogram/dev/framework/
- miniprogram-ci：https://developers.weixin.qq.com/miniprogram/dev/devtools/ci.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13