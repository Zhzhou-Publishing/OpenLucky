# 先行使用（Early Use）—— 分批加载放行设计

> 用途：新对话窗口先加载本文件进上下文，了解「先行使用 / 分批加载」这块讨论到了哪里。
> 性质：产品方向与设计结论的记录，不是实现 PR。实现相关的事实（bug、代码位置）以当时代码为准。
> 最近更新：2026-08-18

---

## 0. 一句话结论

选定目录后，不再等**全部**图片 copy/resize 进 working directory 才进系统，而是当就绪数量达到目录总量的 **1/3**（编译期可配）就放行进入图库；剩余图片在后台 lazy load，未就绪的图用 loading 占位、不可进 Edit。**已就绪的图可直接进 Edit 使用完整功能；但 `applyPreset`（一键套用预设）与 `saveAll`（保存全部）锁死到全部加载完成。**

---

## 1. 现状瓶颈（事实）

加载分两段，「先行使用」针对第一段：

1. **prepare 阶段**（`PhotoDirectory` 按钮进度条）：`app/ipc/prepare-working-directory-from-selected.js` 在 `await Promise.all(imageProcessings)` 之后才 emit `working-directory-from-selected-prepared`。`PhotoDirectory.vue` 的 `await` 一直阻塞到全部文件 copy/resize 完成（RAW 走 CLI spawn resize，最慢）。
2. **get-images 阶段**（`PhotoGallery` 的 spinner）：`app/ipc/get-images.js` 扫 working dir + `Promise.all` 建缩略图。非 TIFF 只拼 `file://` URL（几乎免费），TIFF 才 sharp 转码。

要把「等待」从目录页的阻塞按钮，搬进 Gallery 网格（占位符），1/3 就放行。

---

## 2. 核心设计：清单落盘，磁盘仍是唯一真相

**原则**：不引入「main 进程内存态 = 第二真相源」。真相仍全部落在 working directory 这个自描述文件夹里，main 的 prepare job 退化成**只写文件 + 发通知**的瘦执行体。

- **清单（manifest）**：目录里所有图片的 `filename` 列表，`readdirSync` 即可得，**零成本、立刻可得**，job 开始时一次性写入 `.manifest.json`。
- **就绪状态（ready）**：**文件已在 working dir = ready**（磁盘扫描，和现在 `get-images` 一模一样）。
- **pending**：在 `.manifest.json` 里但不在盘上。
- **error**：失败时追加进 `.errors.json`（失败罕见，几乎零成本）。

这样 `get-images` / `refresh-image` **完全不认识 job**，只是「读 manifest + 扫盘」的纯磁盘读；main 的 job 内存态（p-limit 队列、cancelled、count）是**执行态**，不是**真相**。收益：不引入第二真相源、窗口 reload 天然正确、Rust 移植只需读文件。

---

## 3. 状态模型（每张图）

```
status: pending | ready | error
entry:  { name, isRaw, url (仅 ready), status, error (仅 error) }
```

`.manifest.json`：

```json
{ "total": 3, "files": [ { "name": "a.jpg", "isRaw": false }, { "name": "b.tif", "isRaw": true } ] }
```

> **`name` 是「工作目录里的实际文件名」，不是源文件名**。RAW 源（如 `scan.arw`）经 `tool resize` 会 `with_suffix('.tif')` 落成 `scan.tif`（见 `cli/lib/tool/resize.py`），manifest / `working-image-ready` / `.errors.json` 全用这个名字，`get-images` 才能靠 `fs.existsSync` 判对 ready。`isRaw` 仍记「源是否 RAW」，仅作信息。

`.errors.json`（仅失败时写）：

```json
{ "b.arw": "resize failed: ..." }
```

---

## 4. 事件 / IPC 契约

**prepare 阶段（`prepare-working-directory-from-selected`）改造成后台 job：**

| 事件 | payload | 说明 |
|---|---|---|
| `working-directory-partial-ready`（新） | `{ workingDirectory, outputDirectory, originalDirectory, readyCount, total }` | 就绪数 ≥ 阈值时 emit 一次；清单由 get-images 读盘获取，不随事件下发 |
| `working-image-ready`（新） | `{ workingDirectory, name }` | 每张完成即 emit（不携带缩略图，渲染层收到后调 `refreshImage` 补缩略图） |
| `working-image-error`（新） | `{ workingDirectory, name, error }` | 单张失败 |
| `working-directory-from-selected-prepared`（复用） | 加 `workingDirectory` | 全部完成的终态 |

**配套改动：**

- **`.manifest.json` 提前写**（job 开始一次）；**`.preset.json` 提前 copy**（现在 `Promise.all` 之后才 copy，懒加载下必须提前）；**output 目录提前建**。
- **进度/标题只在 partial-ready 之前发**：partial-ready 时发 `processing-progress-clear` + `window-title-restore`，之后尾巴只发 `working-image-ready` / `working-image-error`，保持安静。
- **取消改单飞（single-flight）**：module 级 `activeJob` 单例；新 job 开始时若旧 job 未结束，标记其 `cancelled` 并清理其 temp dir。取消通道仍用 `once('cancel-processing')`（全局、无 payload），因为它永远指向「当前唯一活跃 job」，`cancelProcessing()` 门面签名不变。
- **事件全部携带 `workingDirectory`**：全局 channel，渲染层按自己的 `workingDirectory` 过滤，天然免疫孤儿 job 的事件串扰。
- **`get-images` 改为 manifest 优先**：有 `.manifest.json` → 逐项 `fs.existsSync` 判 ready/pending/error；无 manifest → 回退现在扫盘逻辑（向后兼容）。

**门面层**：`prepareWorkingDirectoryFromSelected` 的 `successCh` 从 `working-directory-from-selected-prepared` 改成 `working-directory-partial-ready`（`request()` 在此 settle 并清理进度监听，正合适）。新增三个订阅 helper 供 Gallery 收长流：`onImageReady` / `onImageError` / `onWorkingDirectoryComplete`。

---

## 5. gating 矩阵（已锁定）

核心区分：**单文件操作 vs 全量批处理**。ready 图的单文件链路（`resolveImagePath` → workingDir 文件）自洽，Edit 完整功能可开；只有需要「整个目录都就位」的操作才锁。

| 操作 | job 未完成（ready 图） | job 完成 |
|---|---|---|
| 从 Gallery 点进 Edit（ready 图） | ✅ | ✅ |
| Edit 内完整功能：histogram / filmparam / dust / WB / rotate / reset / pick-color / 全分辨率图 | ✅（单文件，只依赖本图就位） | ✅ |
| Gallery 缩略图 + 右键大图 | ✅ 仅 ready | ✅ |
| Edit 底部 strip 切换 / prev / next | ⛔ 只切到 ready 图，跳过 pending | ✅ 全部 |
| **保存全部 saveAll** | ⛔ 锁死 | ✅ |
| **一键套用预设 applyPreset** | ⛔ 锁死 | ✅ |

**注意**：Edit 页不是只吃 route query 的单页，它有自己的缩略图 strip 和 `selectImage / nextImage / previousImage`（`PhotoEdit.vue`），切换后 watch 触发 `loadFullResImage`。所以 readiness 要同时挡 **Gallery 的 `openPhotoEdit`** 和 **Edit 页的 strip + 上下切换**，否则用户一按就会对还没进 workingDir 的图调 `getFullResImage` 拿到空文件。两边走 `get-images` 同一条读路径，改一次模板/导航判断即可。

---

## 6. 编译期配置

阈值收敛到单一常量模块 `app/shared/config.js`（与 `utils.js`/`formats.js` 同级，main 直接 `require`）：

```js
// 先行使用：working dir 就绪比例达到该值即放行进入系统。
// 编译期改这里即可；dev 也可用 OPENLUCKY_EARLY_USE_RATIO 覆盖（免重编译）。
const EARLY_USE_READY_RATIO = parseFloat(process.env.OPENLUCKY_EARLY_USE_RATIO) || (1 / 3)
```

阈值计数 = `Math.max(1, Math.ceil(totalImages * EARLY_USE_READY_RATIO))`（地板 1，目录非空必能进）。该值**只在 main 算**，渲染层只响应 `partial-ready` 事件，不关心具体数字，故天然只落 main 一侧，无需 IPC 下发——除非日后想在图库显示「已就绪 x / 需 y」。

---

## 7. 边界情况

1. **重选目录 / 放弃 job**：Gallery `goBack()` 回目录页再选新目录，旧 job 仍在后台跑。单飞取消 + 渲染层按 `workingDirectory` 过滤事件，旧 job 既停又不会串扰。
2. **错误文件计账**：`hasUnappliedImages` 只统计 `ready` 图；`error` 图不进账（本就无法编辑/保存），避免 SaveAll 在缺图时把不完整 `.preset.json` 落盘。
3. **重进 / 刷新**：`get-images` 读 `.manifest.json` + 扫盘，Edit 与 Gallery 重挂载都能拿到带 `status` 的清单，不因磁盘 lag 丢失占位信息。
4. **尾巴失败不悬挂**：partial-ready 之后若发生全局异常，catch 仍发 `working-directory-from-selected-error`，Gallery 订阅它把 job 标记为 failed（而非永久 loading）。

---

## 8. 待办 / 实现步骤

- [x] `app/shared/config.js`：`EARLY_USE_READY_RATIO` 常量。
- [x] `app/shared/manifest.js`：`.manifest.json` / `.errors.json` 读写 helper。
- [x] main：`prepare-working-directory-from-selected.js` 改成 job（manifest 提前写 + `.preset.json`/output 提前 + partial-ready/image-ready/image-error + 单飞取消）。
- [x] `get-images.js`：manifest 优先 + 磁盘回退 + 每项 `status`。
- [x] 门面：`successCh` 改 partial-ready + 三个订阅 helper。
- [x] `PhotoDirectory.vue`：无改动（`await` 已在 partial-ready settle 后跳转）。
- [x] `PhotoGallery.vue`：占位渲染 + gating + 订阅增量 + 锁 `applyPreset`/`saveAll`。
- [x] `PhotoEdit.vue`：strip 占位 + 导航跳过 pending。
- [x] 测试：manifest / 阈值 / 增量事件 / get-images status，全绿。

## 9. 开放问题

- **阈值触达顺序**：按文件数算没问题，但 `readdirSync` 自然序下前 1/3 可能全是慢 RAW。可选「两段调度」——先 copy 所有无需 resize 的小图（快达阈值），重的 resize 后置。（未定）
- **缩略图懒生成**：`get-images` 现在 `Promise.all` 全量 sharp 转码 TIFF，几千张胶卷扫描是既有炸弹。本功能把「ready」与「缩略图」解耦了（pending 直接 `url:null`），但 ready 集的 TIFF 转码仍是全量。后续应改成可见窗口懒生成。（未做，仅记录）
- **applyPreset 与 saveAll 的解锁 UI**：锁到 job 完成后要不要给个明确的「仍在加载 x/y」提示，而非单纯 disabled。

---

## 10. Tauri/Rust 迁移注意（本功能新增的触点）

> 将来换 Rust + Tauri 时，除 `docs/tauri-migration-attention.md` 已有清单外，本功能额外引入以下必须原生重写的能力。

### 10.1 契约表新增 capabilities

本功能让 `prepare-working-directory-from-selected` 与 `get-images` 的 `capabilities` 各多一项：

| 新 capability | 含义 | Rust 替代 |
|---|---|---|
| `manifest` | 读写 working dir 里的 `.manifest.json` / `.errors.json` | `serde_json` + `std::fs`（trivial） |

`get-images` 从 `['sharp','fs','tmp']` 变 `['sharp','fs','tmp','manifest']`；`prepare-working-directory-from-selected` 从 `['fs','tmp','p-limit','spawn','cancel']` 变 `['fs','tmp','p-limit','spawn','cancel','manifest']`。

### 10.2 后台 job + 增量事件（不是一次 request/response）

- Rust 侧要复刻：一个后台任务，① 先列全量清单写 `.manifest.json`，② spawn CLI copy/resize，③ 按阈值发 `partial-ready`、逐张发 `image-ready`/`image-error`、结束发 `complete`，④ 单飞取消（一个 `AtomicBool` / `AbortHandle` 单例，等价 module 级 `activeJob`）。
- **所有事件 payload 必须携带 `workingDirectory`**——渲染层靠它过滤全局事件。
- 进度/标题事件（`processing-progress-update` 等）只在 partial-ready 之前发，之后尾巴只发增量事件。

### 10.3 `cancel-processing` 不在契约表里

`cancel-processing` 现在仍是「handler 体内 `ipcMain.once` 注册」的隐式通道，不在契约表。Rust 侧要有一个等价的「取消当前活跃 job」信号，接到那个单例 cancel 标志上。语义是**单飞**：永远只取消当前活跃 job。

### 10.4 `get-images` 保持纯磁盘读

Rust 侧 `get-images` = 读 `.manifest.json`（有则用，无则扫盘回退）+ 对 ready 图建缩略图。**不要**依赖任何内存 job 状态。`buildThumbnailEntry` 的 TIFF 转码仍按 `docs/tauri-migration-attention.md` §3 优先沉到 Python CLI（本功能不改变这一点）。
