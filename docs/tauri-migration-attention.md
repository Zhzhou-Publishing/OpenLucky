# Tauri 迁移注意点（薄映射清单）

> 用途：将来把 Electron 换到 Rust + Tauri 时，**先将本文件加载进上下文**，逐条对照执行。
> 本文档记录所有「未抽象、但迁移时不能漏」的 Electron 专属触点，以及相关的契约约束。
> 背景架构见 `docs/backend-contract-migration-plan.md`。

---

## 0. 迁移前必须理解的三层架构

```
Vue 页面 ──→ backend facade ──→ IPC 处理器（ipc/*.js）──→ shared 纯逻辑 ──→ Python CLI
                (swap point)      (21 命令，薄委托/自定义)    (引擎无关)         (sidecar)
```

- **契约表** `app/shared/backend-contract.js` = 21 个命令的单一事实源（channel/kind/payload/emit/spawn/capabilities）。
- **引擎** `app/ipc/engine.js` = 读契约表注册 ipcMain，驱动 spawn 生命周期。
- **facade** `app/src/services/backend/index.js` = 渲染层唯一抽换点，当前只有 `electron.js`。
- **硬约束**：现有 `npm test` 的 91 个测试（82 原有 + 9 契约一致性）**必须零改动全绿**。

---

## 1. 契约表里的 capabilities 字段 = 迁移清单

契约表每条命令的 `capabilities` 数组，明确标出 **Rust 侧必须原生重写的能力**。迁移时逐条扫：

| capability | 含义 | 涉及的命令 | Tauri/Rust 替代 |
|---|---|---|---|
| `spawn` | spawn Python CLI | 几乎所有 | Rust `std::process::Command` + sidecar |
| `fs` / `fs-read` | 读写文件 | copy-preset-json、read-preset-json、reset-image 等 | Rust `std::fs` |
| `sharp` | TIFF→JPEG 转码 | get-full-res-image、get-images、refresh-image | **见 §3，优先沉到 Python CLI** |
| `tmp` | 临时目录 | get-full-res-image、get-images、refresh-image、prepare-* | `std::env::temp_dir()` |
| `getWin` | 通过主窗口发事件 | confirm-close（关闭拦截应答，已仅剩这一个） | Tauri `AppHandle` / window 事件 |
| `dialog` | 原生目录选择框 | select-directory | `tauri-plugin-dialog` |
| `shell` | 打开外部 URL | open-external | `tauri-plugin-opener`（或 `tauri-plugin-shell`） |
| `nativeTheme` | 主题状态 | set-theme | `tauri-plugin-theme` / window API |
| `window-close-intercept` | 关闭窗口拦截 | confirm-close | Tauri window `onCloseRequested` |
| `p-limit` | 并发控制 | prepare-* | Rust 并发（`rayon` / async） |
| `cancel` | 取消处理 | prepare-working-directory-from-selected | Tauri 事件 + 取消标志 |
| `preset-translate` | preset→CLI 参数翻译 | apply-preset-to-file、apply-preset-to-batch | Rust 复刻 `buildParamString`/`resolvePresetKey` 逻辑 |

---

## 2. 逐条 Electron 专属触点（薄映射点）

这些是「换引擎时写 Tauri 等价物」的点，channel 和 payload 已被契约表钉死，**渲染层一行不改**。

### 2.1 `dialog` — 仅 select-directory
- **文件**：`app/ipc/select-directory.js`
- **Electron 用法**：`dialog.showOpenDialog(BrowserWindow.fromWebContents(event.sender), { properties: ['openDirectory'] })`
- **Tauri**：`tauri-plugin-dialog` 的 `open({ directory: true })`（自然挂在调用窗）
- **⚠️ 注意**：
  - 对话框父窗 = `BrowserWindow.fromWebContents(event.sender)`（调用窗；为 null 时非模态），结果回发 `event.sender` ——与其它 handler 一致，**Rust 侧直接拿到调用 `Window`**。
  - 三个发射通道：`directory-cancelled`（无 payload）、`directory-selected {path, files}`、`directory-error`（**BARE STRING**，不是对象）。
  - `files` 是 `fs.readdirSync(selectedPath)` 的**原始结果**（含非图片文件）。

### 2.2 `shell` — 仅 open-external
- **文件**：`app/ipc/open-external.js`
- **Electron**：`shell.openExternal(url)`
- **Tauri**：`tauri-plugin-opener`
- **⚠️ 注意**：有 URL 白名单校验 `/^https?:\/\//i`，**必须保留**（安全）。

### 2.3 `nativeTheme` — 仅 set-theme
- **文件**：`app/ipc/set-theme.js`
- **Electron**：`nativeTheme.themeSource = themeName === 'dark' ? 'dark' : 'light'`
- **Tauri**：主题插件或 window API
- **⚠️ 注意**：**任何非 "dark" 值都映射到 light**。无发射、无 spawn。

### 2.4 ~~`getWin()` 发事件~~ — 已统一为 `event.sender`
- **文件**：`app/ipc/get-images.js`、`app/ipc/select-directory.js`
- **现状**：这两个 handler 已改为 `event.sender.send(...)`，与其余 19 个 handler 一致——**不再有"发主窗口而不是调用者"的特殊情况**。`getWin()` 现仅剩 `confirm-close` 使用（见 §2.8）。
- **Tauri**：无需特殊处理——Rust command 的 `Window` 参数天然是调用窗。

### 2.5 `ipcMain.once` + `ipcMain.removeListener` — 取消处理
- **文件**：`app/ipc/prepare-working-directory-from-selected.js`
- **Electron**：handler 内 `ipcMain.once('cancel-processing', onCancel)`，取消/错误路径 `ipcMain.removeListener(...)`
- **Tauri**：需要等价的取消事件订阅（`once` 语义）
- **⚠️ 注意**：这是唯一用 `once` 注册的 channel，且**在 handler 体内运行时注册**（不在 register() 里）。契约一致性测试断言 `h.ipc.once['cancel-processing']` 存在。

### 2.6 `app`（Electron 应用对象）
- **文件**：`shared/utils.js`（`app.isPackaged`）、`shared/logger.js`（`app.getPath`）、`main.js`
- **用途**：
  - `app.isPackaged` → 决定 spawn 用生产二进制还是 dev `python -m cli.openlucky`
  - `app.getPath('userData')` → 日志/存储路径
- **Tauri**：用 `tauri.conf.json` 的 `bundle` 配置 + `app.path().appDataDir()`
- **⚠️ 注意**：`resolveOpenLuckyCommand`（cli-args.js）根据 `isPackaged` 分支选择命令——**这个逻辑契约测试已覆盖**，Rust 侧要复刻同样的分支。

### 2.7 `BrowserWindow` / 窗口生命周期 — 仅 main.js
- **文件**：`app/main.js`
- **用途**：创建窗口、`win.loadFile('dist/index.html')`、`ready-to-show`、`window-all-closed`、`activate`、`nativeTheme.themeSource = 'dark'`
- **Tauri**：`tauri.conf.json` window 配置 + Rust builder
- **⚠️ 注意**：`main.js` **不被 Vite 打包**（electron-builder 原样打包），Tauri 侧是全新的 `src-tauri/`，main.js 整个被 Rust 替代，不算「薄映射」而是完整重写。

### 2.8 `confirm-close` 窗口关闭拦截
- **文件**：`app/ipc/confirm-close.js`
- **Electron**：`setupWindow(win)` 里 `win.on('close')` 拦截 + `win.webContents.send('confirm-close')`；模块级 `allowClose` 状态
- **Tauri**：window `onCloseRequested` 事件 + `api.prevent_close()` 语义
- **⚠️ 注意**：
  - 模块级 `allowClose` 必须留在委托文件（测试 `freshRequire` 重置依赖它）。
  - 导出 `setupWindow(win)`（main.js 对每个新窗口调用）。契约测试断言 `setupWindow` 存在。
  - 发射 `confirm-close`（push，无 payload）→ 渲染层回 `confirm-close-response {allow}`。

---

## 3. ⚠️ 最重要的迁移前置：把 `sharp` 沉到 Python CLI

**这是唯一不该留给 Tauri 迁移时做的去耦，现在就该做。**

- **现状**：`shared/utils.js` 的 `buildThumbnailEntry`（get-images / refresh-image 用）和 `get-full-res-image.js` **直接调用 sharp**，处理 16-bit RGB+IR 扫描 TIFF、BigTIFF、`failOn:'none'`、`removeAlpha()`、`limitInputPixels:false` 等细节。
- **问题**：这是真实业务逻辑，不是薄映射。将来 Rust 侧要么用 Rust 图像库重写整套 TIFF 转码，要么……
- **方案**：仓库已有 `cli/lib/tiff_to_jpeg.py`，把它接成 CLI 的 `tool` 命令，让 `buildThumbnailEntry` / `get-full-res-image` **改为 spawn CLI 而不是调 sharp**。
- **收益**：
  - `get-images` / `get-full-res-image` / `refresh-image` 塌缩成普通 spawn 命令，与 `compute-histogram` 同类。
  - 两个引擎都只是「spawn Python」，sharp 这个 Node 依赖从共享层彻底消失。
  - 契约表这三条 `capabilities` 从 `['sharp','fs','tmp','getWin']` 简化为 `['spawn']`。
- **⚠️ 注意**：如果迁移时 sharp 还没沉掉，Rust 侧要原生重写 `buildThumbnailEntry` 的 TIFF 转码——成本高，且容易在 16-bit 多通道 TIFF 上出色彩 bug。

---

## 4. 渲染层 facade（换引擎时如何改）

- **现状**：`app/src/services/backend/index.js` 直接 `import * as electronBackend from './electron'`，`backend = electronBackend`。
- **Tauri 迁移**：
  1. 新增 `tauri.js`（用 `@tauri-apps/api` 的 `invoke`/`listen` 实现**同一组方法**：`computeHistogram`/`getImages`/`applyFilmparam`/...）。
  2. 在 `index.js` 切换选择（可引入 `__BACKEND__` Vite define 做打包时抽换，或直接改一行）。
  3. 渲染层页面代码**一行不改**——它们只依赖 facade 的方法名和 resolved/rejected payload。
- **⚠️ 注意**：`electron.js` 里几个关键行为，Tauri 版必须保持：
  - **filename 匹配**：`applyFilmparam`、`refreshImage` 广播在全局 channel，靠 `outputFile` basename / `filename` 区分多个并发请求。
  - **bare string error**：`images-error`、`directory-error` 是裸字符串，不要包成对象。
  - **progress 自动清理**：facade 的 `request()` settle 时移除 progress 监听（修复了原有泄漏）。
  - **`selectDirectory` 返回 `{canceled:true}`**（不是 reject）。
  - **`path`**：用 `src/services/backend/path.js`（纯 JS），Tauri 没有 `window.require('path')`。

---

## 5. 测试约束（迁移时必须保持全绿）

- `npm test` 跑 `node --test "shared/__tests__/**/*.test.js"` = **91 个测试**。
- **harness**（`shared/__tests__/harness.js`）mock 掉 `electron`/`electron-log`/`sharp`/`image-size`/`child_process`/`p-limit`，按 channel 字符串驱动。
- 契约一致性测试（`contract-conformance.test.js`）强制：
  - 每个契约 id 映射到 `ipc/<id>.js` 且有 `register()`。
  - 每个 engine-driver 条目注册后 `h.ipc[registration][channel]` 存在。
  - `confirm-close` 导出 `setupWindow`；`from-selected` 调用后 `once('cancel-processing')` 存在。
  - 每个 `spawn.cliBuilder` 存在于 cli-args.js（Rust argv 规格常测）。
- **⚠️ 注意**：这些测试测的是**行为契约**（channel/argv/payload），不是 Electron 本身。Rust 侧要有**镜像测试**验证 byte-identical argv（对照 cli-args.test.js 的 22 个用例）。

---

## 6. 迁移顺序建议

1. **先把 sharp 沉到 Python CLI**（§3）——不依赖迁移决策，纯收益。
2. 建 `src-tauri/` 骨架，跑通 `compute-histogram`（最简单 spawn-json）全链路。
3. 按契约表 capabilities 逐类迁移：spawn 类 → fs 类 → dialog/shell/theme → getWin → window-close。
4. facade 加 `tauri.js` + 切换 `index.js`。
5. Rust 镜像测试对照 cli-args.test.js / ipc-*.test.js / contract-conformance.test.js。

---

## 7. 关键文件索引

| 文件 | 作用 |
|---|---|
| `app/shared/backend-contract.js` | 契约表（单一事实源，JSON 可序列化，serde-ready） |
| `app/ipc/engine.js` | 读契约表注册 ipcMain + spawn 驱动 |
| `app/src/services/backend/index.js` | 渲染层抽换点（当前 electron） |
| `app/src/services/backend/electron.js` | Electron 适配器（含 filename 匹配 / request() / bare string 语义） |
| `app/src/services/backend/path.js` | 纯 JS path（Tauri 无 node:path） |
| `app/shared/cli-args.js` | argv 契约（Rust 必须 byte-identical 复刻） |
| `app/shared/utils.js` | buildOpenLuckyCommand / sharp 缩略图 / resizeImage |
| `app/shared/__tests__/harness.js` | 测试 mock 基础设施（**只读约束**） |
