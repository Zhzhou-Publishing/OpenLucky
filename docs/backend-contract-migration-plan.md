# 共享契约 + 双后端抽换：迁移 Tauri 前的落地计划

> 状态：待实施（规划完成，2026-08-10）
> 适用范围：OpenLucky Electron 应用（`app/`），面向未来 Rust + Tauri 迁移

---

## 1. Context（背景）

OpenLucky 当前是 Electron 应用：渲染进程（Vue 3 + Vite）通过 `window.require('electron').ipcRenderer` 直接调用主进程（41 处调用点）；主进程 21 个 IPC 处理器 spawn Python CLI sidecar（`cli/openlucky.py`，PyInstaller 打包）做胶片处理。

最终目标是迁移到 Rust + Tauri。此前已铺垫：`shared/cli-args.js` / `shared/formats.js` / `shared/version.js` 被刻意抽成纯函数 + 测试，注释明确写着「the planned Tauri/Rust shell ... must emit byte-identical argv」。

**本次改造（Tauri 迁移之前）**：搭建「共享契约 + 双后端实现、打包时全局抽换」的架构——

1. `backend-contract.js` 契约表 = 单一事实源，描述全部 IPC 命令（channel/kind/入参/spawn 规格/事件协议）；将来 Rust 用 `include_str!` + serde 读同一张表。
2. 主进程：共享引擎 `ipc/engine.js` 读契约表注册 handler；21 个 handler 文件变薄委托（**文件路径、`register()` 签名、channel 字符串、发射 payload 形状字节级不变**）。
3. 渲染进程：`services/backend/` facade，`electron.js` / `tauri.js` 两个实现，Vite `__BACKEND__` define 打包时抽换，tree-shaking 删掉未选中 adapter，**运行时零分叉**。
4. **硬约束：现有 82 个单元测试零改动、全绿**，且新增契约一致性测试让契约对 Rust 侧可信。

已确认范围：**完整铺开全部 21 个 handler + 渲染层一起改**。

---

## 2. 关键设计决策

- **契约表放 `app/shared/backend-contract.js`**（纯数据、无函数、双引号、无尾逗号），可被 `JSON.parse(JSON.stringify())` 无损往返 → 该往返成为一致性测试，证明 serde-ready。放 shared 是因为 electron-builder 已打包 `shared/**/*`，且可被 harness 测试 require。
- **引擎 self-require 依赖**：`engine.js` 自己 `require('electron'/'child_process'/'../shared/utils')`，这样 harness 的 `Module._load` mock 恰好拦截它们（mock 按 channel 字符串索引注册）。
- **两类实现拆分**（mandatory）：
  - `engine-driver`（7 个）：`compute-histogram`、`pick-color`（spawn-json）+ `apply-filmparam`、`apply-filmparambatch`、`apply-preset`、`check-openlucky`、`get-presets`（spawn-stream）。引擎按契约元数据构建 handler。
  - `custom-handler`（14 个）：`apply-preset-to-file`、`apply-preset-to-batch`、`confirm-close`、`copy-preset-json`、`get-full-res-image`、`get-images`、`open-external`、`prepare-working-directory`、`prepare-working-directory-from-selected`、`read-preset-json`、`refresh-image`、`reset-image`、`select-directory`、`set-theme`。**handler 体原样保留**，只改 `register()` 包一层 `engine.registerHandler(id, fn)`。
  - 原因：`confirm-close` 的模块级 `allowClose` 必须留在委托文件（`freshRequire` 重置语义）；`prepare-working-directory-from-selected` 在 handler 体内运行时注册 `once('cancel-processing')`；其余涉及 fs/dialog/sharp/tmp/`getWin()`/p-limit 的提取无移植价值（Rust 反正要原生重写），只会把引擎撑到 2000 行。
- **渲染层 facade 接口**：以契约方法名（id 的 camelCase）为契约，后端无关。`request()` helper 实现 send+订阅+settle 时自动清理。
- **两个现有 bug 借此修复**（已确认接受，因渲染层无测试、现状是 bug）：
  1. PhotoDirectory 的 `*-progress`/`window-title-*` 监听器泄漏 → facade `request()` settle 时自动清理。
  2. `apply-filmparam` 的 error 通道不带 `outputFile`，现有 renderer 的 error 匹配永不命中（`affectedImages` 永不清理）→ facade 用 FIFO 队列 + 仅当唯一 pending 时 reject + settle 超时兜底。

---

## 3. 契约表 schema

```js
// app/shared/backend-contract.js —— 纯 JSON 数据
module.exports = [
  {
    id: 'compute-histogram',          // 匹配 ipc/<id>.js 文件名（测试强制）
    kind: 'spawn-json',               // 'spawn-json' | 'spawn-stream' | 'custom'
    registration: 'handle',           // ipcMain: 'handle' | 'on' | 'once'
    channel: 'compute-histogram',
    label: 'ComputeHistogram',        // logger scope
    payload: { type: 'object', props: { directoryPath: 'string', filename: 'string', downsampling: 'number?=256', area: 'null|{x1,y1,x2,y2:number}?=null' } },
    return: { type: 'object', note: 'JSON.parse(stdout); rejects on non-zero/spawn/parse' },
    emit: {},                         // spawn-json 直接返回
    spawn: { cliBuilder: 'buildHistogramArgs', command: 'tool histogram', stdio: ['pipe','pipe','pipe'], windowsHide: true, note: 'input=resolveImagePath(dir,filename,readPresetJson(dir))' },
    implementation: 'engine-driver',  // 'engine-driver' | 'custom-handler'
    capabilities: ['spawn', 'fs-read']
  },
  {
    id: 'apply-filmparam',
    kind: 'spawn-stream',
    registration: 'on',
    channel: 'apply-filmparam',
    label: 'ApplyFilmparam',
    payload: { type: 'object', props: { inputPath:'string', outputPath:'string', filename:'string', params:'string', rotateClockwise:'number?=0', area:'null|obj?', areaBasis:'null|obj?', exposure:'number?', whiteBalance:'string?', tone:'string?', colorMode:'string?' } },
    emit: {
      started:  { channel: 'filmparam-apply-started',  payload: { message:'string' } },
      progress: { channel: 'filmparam-apply-progress', payload: { data:'string' } },
      success:  { channel: 'filmparam-apply-success',  payload: { message:'string', outputFile:'string' } },
      error:    { channel: 'filmparam-apply-error',    payload: { message:'string', error:'string' } }
    },
    protocol: 'started -> progress* -> success | error',
    spawn: { cliBuilder: 'buildFilmparamArgs', command: 'filmparam', stdio: ['pipe','pipe','pipe'], windowsHide: true, note: 'rotateClockwise 默认 0 恒转发' },
    implementation: 'engine-driver',
    capabilities: ['spawn']
  }
  // ... 全部 21 个 id 的完整条目
]
```

### 全部 21 个 id + 分类

| id | kind | registration | 实现 | 备注 |
|---|---|---|---|---|
| compute-histogram | spawn-json | handle | driver | resolveImagePath+readPresetJson |
| pick-color | spawn-json | handle | driver | |
| apply-filmparam | spawn-stream | on | driver | rotateClockwise 默认 0 恒转发 |
| apply-filmparambatch | spawn-stream | on | driver | |
| apply-preset | spawn-stream | on | driver | buildFilmbatchArgs → filmbatch |
| check-openlucky | spawn-stream | on | driver(finalize) | 单通道 {success,error}，无 started/progress |
| get-presets | spawn-stream | on | driver(finalize) | spawn-json 但用 on |
| apply-preset-to-file | spawn-stream | on | custom | fs 预检 + resolvePresetKey + 仅转发 colorMode + 省略 rotate |
| apply-preset-to-batch | spawn-stream | on | custom | 顺序 await 循环 + 合成 progress + 返回 Promise |
| confirm-close | custom | on | custom | +setupWindow(win)；模块态 allowClose；push confirm-close |
| copy-preset-json | custom | on | custom | fs 拷贝 |
| get-full-res-image | custom | on | custom | sharp TIFF 转码 best-effort |
| get-images | custom | on | custom | sharp 缩略图 + Promise.all + getWin()；images-error 裸字符串 |
| open-external | custom | on | custom | shell，校验 https? 前缀 |
| prepare-working-directory | custom | on | custom | p-limit 并发 + resize 管线 |
| prepare-working-directory-from-selected | custom | on | custom | 同左 + once('cancel-processing') 可取消 |
| read-preset-json | custom | on | custom | |
| refresh-image | custom | on | custom | 单张 sharp 缩略图 |
| reset-image | custom | on | custom | 改 .preset.json + 删输出 |
| select-directory | custom | on | custom | dialog + getWin()；directory-error 裸字符串 |
| set-theme | custom | on | custom | nativeTheme setter |

**payload 形态**（facade 必须同 arity）：`object`（compute-histogram/pick-color/所有 apply-*/reset/get-full-res/refresh）、`single`（open-external url、set-theme、get-images dir）、`positional 2 参`（prepare-*: `(dir, options)`）、`positional 1 参`（read-preset-json）、`none`（check-openlucky/get-presets/select-directory）。

---

## 4. 引擎：`app/ipc/engine.js`

```js
const CONTRACT = require('../shared/backend-contract')
const { ipcMain } = require('electron')
const { spawn } = require('child_process')
const { buildOpenLuckyCommand } = require('../shared/utils')
const { createLogger } = require('../shared/logger')

function registerEntry(id, runtime) {  // engine-driver
  // e.kind==='spawn-json' → spawnJsonHandler(e, rt)；spawn-stream → spawnStreamHandler(e, rt)
  // ipcMain[e.registration](e.channel, fn)
}
function registerHandler(id, fn) {     // custom-handler：校验后 ipcMain[e.registration](e.channel, fn)
}
module.exports = { registerEntry, registerHandler, CONTRACT }
```

- **spawnJsonHandler**：spawn + 收 stdout/stderr + close(code≠0 → reject) + JSON.parse(resolve)。与现 compute-histogram/pick-color 消息一致。
- **spawnStreamHandler**：两种模式——
  - terminal（有 started/progress/success/error）：逐 stdout chunk 发 progress，close(0)→successPayload，非 0→error `{message:'Process exited with code X', error}`，spawn error→error。
  - finalize（check-openlucky/get-presets）：close 时调 `rt.finalize({code, stdout, stderr, send})`，spawn error 调 `rt.onSpawnError`。
  - 所有 `send` 前 guard `event.sender.isDestroyed()`。

### 薄委托示例（compute-histogram：43 行 → 6 行）

```js
// app/ipc/compute-histogram.js
const { registerEntry } = require('../ipc/engine')
const { readPresetJson, resolveImagePath } = require('../shared/utils')
const { buildHistogramArgs } = require('../shared/cli-args')
module.exports = {
  register: () => registerEntry('compute-histogram', {
    buildArgs: ({ directoryPath, filename, downsampling = 256, area = null }) =>
      buildHistogramArgs({ input: resolveImagePath(directoryPath, filename, readPresetJson(directoryPath)), downsampling, area })
  })
}
```

### custom 委托示例（confirm-close：体保留，register 包一层）

```js
// app/ipc/confirm-close.js —— 模块级 allowClose 留在本文件（freshRequire 重置）
const { registerHandler } = require('../ipc/engine')
let allowClose = false
function register() {
  registerHandler('confirm-close', (_, allow) => { /* 原体不变 */ })
}
function setupWindow(win) { /* 原体不变 */ }
module.exports = { register, setupWindow }
```

**为何 82 测试全绿**：`h.loadHandler('../../ipc/<file>')` → `mod.register()` → 引擎调 `ipcMain[registration](channel, fn)` → harness 记入 `h.ipc[registration][channel]`。spawn 仍走 child_process proxy → spawnCalls 记录。buildOpenLuckyCommand 仍在 handler 调用时读 `app.isPackaged`。7 个 driver 发相同 channel/payload/argv（buildArgs 映射到同一批已测 cli-args builder）。

---

## 5. 渲染层 facade：`app/src/services/backend/`

```
backend/
  index.js            // __BACKEND__==='electron' ? electron : tauri
  electron.js         // ipcRenderer adapter
  tauri.js            // @tauri-apps/api invoke/listen adapter
  path.js             // 纯 JS join/basename/extname（Tauri 无 node:path）
  logger.js           // __BACKEND__ 选 logger adapter
  logger.electron.js  // import log from 'electron-log'
  logger.tauri.js     // @tauri-apps/plugin-log
```

### 选择逻辑（index.js）

```js
import * as electronBackend from './electron'
import * as tauriBackend from './tauri'
const backend = __BACKEND__ === 'electron' ? electronBackend : tauriBackend
export default backend
```

`__BACKEND__` 被 Vite define 静态替换 → Rollup 求值三元、标记死分支、DCE 删其 import。运行时零分支。

> ⚠️ 两个 adapter 都被静态 import，所以 **electron 构建也必须能 resolve `@tauri-apps/api`/`@tauri-apps/plugin-log`** → 现在就把这两个装进 dependencies。若 DCE 验证发现 tauri 符号残留在 electron bundle，回退到 `resolve.alias` 把非活跃 adapter 指向 stub（仍是构建期抽换）。

### API 面（两个 adapter 共享，方法名 = id 的 camelCase）

- 底层原语：`isAvailable()`、`subscribe(ch, h)`→返回退订函数、`subscribeOnce`、`unsubscribe`、`send(ch,...args)`、`invoke(ch,payload)`
- 操作方法（每个对应一个契约条目）：
  - `computeHistogram`/`pickColor`（invoke Promise）
  - `getPresets`/`checkOpenlucky`/`selectDirectory`/`getImages`/`readPresetJson`/`resetImage`/`getFullResImage`/`prepareWorkingDirectory(dir,opts)`/`prepareWorkingDirectoryFromSelected`/`applyPreset`/`applyFilmparambatch`/`applyPresetToBatch`（send+匹配响应 Promise）
  - `applyFilmparam`/`refreshImage`（filename 匹配 Promise，见下）
  - `cancelProcessing`/`confirmCloseResponse`/`setTheme`/`openExternal`（fire-and-forget）
  - `onConfirmClose`/`offConfirmClose`（main-push 事件）
- `path`：`import { path } from './path'`，替换 2 处 `window.require('path')`
- `createRendererLogger`：`utils/rendererLogger.js` 改为从 facade 转发，现有 import 点全不破

### `request()` helper（send+订阅+settle 自动清理）

```js
function request(sendCh, sendArgs, { successCh, errorCh, match, progress = {} } = {}) {
  return new Promise((resolve, reject) => {
    // on success: match?匹配才 resolve，cleanup()（removeListener 所有通道）
    // on error: 同，reject(payload)（保持裸字符串语义）
    // progress: 逐通道 on，cleanup 时一并移除 ← 修复泄漏
  })
}
```

### filename 匹配操作（正确性陷阱）

- `refreshImage`：success/error 都带 `{filename}` → `match: p => p.filename === filename`。
- `applyFilmparam`：success 带 outputFile（按 basename 匹配）；**error 不带 filename**（现状 bug）→ FIFO 队列 + 仅当唯一 pending 时 reject + settle 超时兜底。行为变更仅限 error 路径（从不 settle → 现在会 settle），页面已有 try/catch。

### tauri.js 骨架（写 stub，Tauri 迁移细节由 facade 隔离）

```js
import { invoke } from '@tauri-apps/api/core'
import { listen, emit } from '@tauri-apps/api/event'
export const isAvailable = () => '__TAURI_INTERNALS__' in window
// send → emit；subscribe → listen；computeHistogram → invoke('compute_histogram', ...)
```

---

## 6. 打包时抽换

```js
// vite.config.js —— 追加 define
define: { __APP_VERSION__: JSON.stringify(packageJson.version), __BACKEND__: JSON.stringify(process.env.BACKEND || 'electron') }
```

Windows-safe（cmd/PowerShell 不能 `BACKEND=electron vite`）：加 `app/scripts/run-vite.js` node wrapper 设 env + spawn vite。package.json：

```json
"dev": "node scripts/run-vite.js electron",
"build": "node scripts/run-vite.js electron build && npm run update-emoji",
"build:tauri": "node scripts/run-vite.js tauri build",
"dev:tauri": "node scripts/run-vite.js tauri"
```

`main.js` 不被 Vite 打包（electron-builder 原样打包），所以 `__BACKEND__` 只影响渲染 bundle。

---

## 7. 迁移顺序（每个检查点 npm test 全绿）

### Phase A — 主进程（契约+引擎+薄委托）

- **A1**：新增 `backend-contract.js` + `engine.js` + 契约一致性测试（暂无 wiring，全绿）。
- **A2**：转换 7 个 driver 文件 → npm test 全绿。**最高风险步**（driver 必须精确复现 argv+emit），用 ipc-spawn 测试验证。
- **A3**：14 个 custom 文件改 `registerHandler`（体不动）→ npm test 全绿。
- **A4**：`npm run dev:hot` 冒烟（开目录/画廊/套预设/套参数/旋转/保存全部/取消/全分辨率/直方图/取色）。
- 检查点：npm test = 82 + 新增一致性测试。

### Phase B — 渲染层 facade（零主进程风险）

- **B1**：建 backend/ 全套文件 + 装 tauri 依赖 + wire `__BACKEND__` + 构建验证 electron bundle 无 tauri 符号。
- **B2**：低风险点：theme.js、About.vue、presetCache.js、App.vue。
- **B3**：PhotoDirectory.vue（select-directory 流 + 进度 + 取消 + check-openlucky，修泄漏）。
- **B4**：PhotoGallery.vue。
- **B5**：PhotoEdit.vue（最大：invoke + 全部 apply/reset/refresh）。
- **B6**：rendererLogger.js 指向 facade logger；`grep -rn "window.require" src` = 空。
- 检查点：grep 空 + `yarn build` 干净 + 手动冒烟 + npm test 仍绿。

### Phase C — 新增测试

1. **契约一致性**（`shared/__tests__/contract-conformance.test.js`，harness 驱动）：
   - JSON 往返；id 唯一且每个 id 解析到 `../../ipc/<id>.js` 且有 register；
   - 每个 engine-driver 条目 `loadHandler` 后 `h.ipc[registration][channel]` 存在（契约↔委托同步）；
   - confirm-close 断言 `setupWindow` 是函数；from-selected 调用后 `h.ipc.once['cancel-processing']` 存在；
   - 每个 spawn 条目的 `spawn.cliBuilder` 存在于 cli-args（Rust argv 规格常测）。
2. **facade adapter 测试**（vitest + `"test:renderer": "vitest run"`）：
   - electron adapter 注入假 ipcRenderer（EventEmitter）驱动精确 channel 序列；tauri adapter mock `@tauri-apps/api`。
   - **共享行为套件断言两个 adapter 对每个操作产出相同的 resolved/rejected payload**（parity 保证），含 applyFilmparam/refreshImage 的 filename 匹配 + images-error 裸字符串。
3. **DCE guard**（可选）：构建后 electron bundle 无 `__TAURI_INTERNALS__`、tauri bundle 无 `ipcRenderer`。

---

## 8. 验证

- `cd app && npm test` → 82 现有 + 新增契约测试全绿（零改动现有测试）。
- `npm run build` → 产物干净；`grep -rn "__TAURI_INTERNALS__" dist/assets` = 空（electron bundle）。
- `npm run dev:hot` 冒烟全部流程。
- `grep -rn "window.require" src` = 空。
- Phase C 后：`npm run test:renderer`（vitest facade parity）全绿。

---

## 9. 关键文件

**新建**：
- `app/shared/backend-contract.js`
- `app/ipc/engine.js`
- `app/src/services/backend/{index,electron,tauri,path,logger,logger.electron,logger.tauri}.js`
- `app/scripts/run-vite.js`
- `app/shared/__tests__/contract-conformance.test.js`
- `app/src/services/backend/__tests__/*.test.js`

**修改**：
- 21 个 `app/ipc/*.js`（薄委托）
- `app/vite.config.js`
- `app/package.json`（scripts + deps + vitest）
- `app/src/utils/rendererLogger.js`（转发 facade）
- 渲染文件：`theme.js`、`About.vue`、`presetCache.js`、`App.vue`、`PhotoDirectory.vue`、`PhotoGallery.vue`、`PhotoEdit.vue`

**只读约束**：`app/shared/__tests__/harness.js`（channel 字符串驱动所有注册，不可改）。

**复用（绝不重写）**：`app/shared/cli-args.js`、`app/shared/utils.js`、`app/shared/formats.js`、`app/shared/version.js`、`app/shared/logger.js`、`app/shared/main-window.js`。
