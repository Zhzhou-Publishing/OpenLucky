# 胶片色彩 v2 —— 密度域去色罩实施计划

> 用途：OpenLucky 反相/去色罩管线 v2 的落地路线。目标是把密度域科学去色罩（Status M 去串扰 + 逐通道 D-min/D-max 归一化）落地到 Python 管线，同时保留 OpenLucky 已有的好设计（吸管采片基、gamma 对齐、宽容度 tone、film_profile）。
> 性质：实施计划（roadmap + 决策清单）。各阶段按顺序做，每阶段有独立验收。
> 配套：`film-color.md`（产品方向 + 已知 WB bug）。

## 实现进度（2026-08-21，后端脚本已落地）

已实现并通过测试（`python -m pytest tests/test_film_v2.py` + 全量回归 176 passed）：
- **Phase 0-5**：`cli/lib/process_film_functions/density.py` 纯函数；`process_film.py` 的 `algo="v1"|"v2"` 分支与 `_process_film_v2_bytestream`；CLI `--algo` 穿透 4 个命令；`tests/test_film_v2.py`（22 个用例：纯函数 + 反相单调 + 中性灰保持 + 方向 pin + 自动片基兜底 + 曝光）。
- **Phase 8（部分）**：`scripts/compare_v1_v2.py` A/B 脚本。
- **决策 1-3、5 已按本文件 §4 落地**；**决策 4（非 RAW de-gamma）已写好 `srgb_to_linear` 纯函数但默认不接线**（见 §4 决策 4，待单独里程碑）。
- **前端平迁（2026-08-21）**：`app/shared/cli-args.js` 的 `buildFilmparamArgs`/`buildFilmbatchArgs` 默认拼 `--algo v2`（可传 `algo:'v1'` 覆盖），契约 `backend-contract.js` 加 `algo` 字段，app 测试 112 全绿。前端所有处理路径默认走 v2；饱和度暂为 v2 默认 1.0（单张编辑路径，预设批量仍读 preset 饱和度）。
- 未做：Phase 6（film_profile 升级）、Phase 7（黑白负片）、Phase 8 剩余（引擎切换 UI、饱和度控件）。

实现说明：v1 代码路径**未动**（仅在入口加 `algo` 分支），v1 行为字节不变；v2 单独一个函数，解码/编码假设与 v1 相同。

---

## 0. 目标与总验收

**目标**：v2 引擎让「自动反相」输出颜色更准——三个来源（按收益排序）：

1. **密度域反相**：`D_net = -log10(T) − D_mask`，而不是线性域 `1 - x`；
2. **Status M 去串扰矩阵**：补偿三层染料光谱重叠；
3. **逐通道 D-min/D-max 归一化**：各自拉满动态范围（密度域自动色阶）。

**总验收**：同一张负片，v2 与 v1 相比——中性灰更灰、肤色不偏紫、无发灰/死黑、WB 方向正确；全量 v1 回归测试不破坏。

**不破坏原则**：v1 引擎与 CLI 默认行为**完全不动**；v2 通过 `algo="v2"` 显式启用，可随时回退。

---

## 1. 核心架构：v1/v2 并存，flag 切换

```
process_film_bytestream_with_params(..., algo="v1")
                                   │
                    ┌──────────────┴───────────────┐
                    │ algo=="v1"                    │ algo=="v2"
                    ▼                               ▼
           [现有全管线不变]              _process_film_v2(...)
        linearize → 线性域反相...        linearize → density → 减mask
                                         → decrosstalk → 归一化 → gamma
                                         → gamma对齐 → 后gamma调色 → tone
```

- 新参数 `algo`（默认 `"v1"`）贯穿 `process_film_with_params` / `process_film_bytestream_with_params` / CLI `openlucky.py` / app IPC。
- v2 核心函数集中到**新模块**，主流程文件只加一个分支调用，尽量不重构 v1 代码。
- 参数表面保持：`preset_mask_*`、`preset_gamma`、`preset_contrast*`、`white_balance`、`tone_pivot/tone_curve`、`exposure_ev`、`color_mode`、`dust` 等在 v2 里都**继续接收**（语义映射见 Phase 5）。

---

## 2. 新模块：`cli/lib/process_film_functions/density.py`

纯函数，全部可单测、可向量化（numpy），不碰 I/O：

```python
EPSILON = 1e-6

# 3×3 去串扰矩阵：目前为对角（先不做串扰修正），保留每通道密度缩放。
# 完整矩阵（含交叉项）如下，待串扰标定后再恢复：
#   [[1.0197, 0.0317, 0.0091],
#    [-0.0052, 0.8933, 0.0521],
#    [0.0131, -0.0011, 0.9712]]
STATUS_M = np.array([
    [1.0197, 0.0,     0.0],
    [0.0,     0.8933, 0.0],
    [0.0,     0.0,    0.9712],
])
DENSITY_LUMA = np.array([0.2126, 0.7152, 0.0722])  # Rec.709

def to_density(linear_rgb):            # -log10(max(T, ε))，逐通道
def mask_to_density(mask_0_255):       # -log10(max(mask/255, ε))
def subtract_mask(density, mask_density):
def decrosstalk(density, matrix=STATUS_M, enabled=True):
def estimate_density_limits(density, roi=None,
                            spike_threshold=0.10, tail=0.01, spike_guard=0.20):
    """密度直方图极值。跳过 > spike_threshold 总像素的尖峰（累积< spike_guard 时），
       再取 tail / (1-tail) 分位。返回 (d_min, d_max)。"""
def normalize_density(density, d_min, d_max):   # (d - d_min)/(d_max - d_min)
def auto_base_mask(linear_rgb):                  # 每通道 99 分位 → mask（兜底）
def density_luma(density):                       # 黑白模式合并用
```

要点：
- `to_density` 输入是**线性透射率 0-1**；`estimate_density_limits` 的 ROI 复用现有 `wp_roi_*`。
- `decrosstalk` 的矩阵参数可空，**默认开但可配置**（该矩阵是经验估计，为后续设备标定留口）。

---

## 3. 阶段划分（按序执行）

### Phase 0 —— 基线 + 测试脚手架
- **目标**：先钉住 v1 行为，再动工。
- **动作**：
  - 确认 `tests/test_film.py`、`tests/test_filmparam.py` 在 v1 全绿（跑一遍，留基线）；
  - 用 `tests/fixtures` 现有负片存 3~5 张 v1 输出 golden（数值断言，不只像素）；
  - 加 `tests/test_film_v2.py` 空壳：`algo="v2"` 当前抛「未实现」，打通参数穿透链路（CLI → process_film → 分支）。
- **验收**：基线全绿；`algo="v2"` 参数能传到分支。

### Phase 1 —— 密度域核心纯函数
- **目标**：`density.py` 全部纯函数单测 pin 死。
- **动作**：实现 §2 各函数；单测覆盖：
  - `to_density([1.0,0.1,0.01])` 的精确值（= `[0, 1, 2]`）；
  - 等价性：`10 ** -(to_density(a) - to_density(b)) == a/b`；
  - `decrosstalk` 对纯中性灰 `[0.18,0.18,0.18]` 输出仍中性（矩阵行和≈1）；
  - `estimate_density_limits` 对合成直方图（含 30% 死白尖峰）端点不被带偏。
- **验收**：纯函数全 pin。

### Phase 2 —— v2 主流程（最小可用）
- **目标**：v2 跑通「linearize → density → 减 mask → decrosstalk → 归一化」，先不管参数映射。
- **动作**：
  - `_process_film_v2(...)`：以上核心 + 默认 gamma=1、temp/tint=0；
  - mask 来源：`preset_mask_*`（吸管现采值）仍是主输入；新增 `auto_base_mask` 兜底（batch/未吸管时）；
  - 归一化端点先用全图（Phase 3 才切 ROI）。
- **验收**：同一张负片 v2 输出反相方向正确、不再发灰；v1 完全不受影响。

### Phase 3 —— 逐通道 D-min/D-max 归一化（ROI + 尖峰保护）
- **目标**：端点估计鲁棒。
- **动作**：
  - 在 `wp_roi_*`（或 fallback 全图）内采样密度直方图，走 `estimate_density_limits`；
  - **v2 里移除线性 auto levels**（v1 的 `process_film.py:424-437` 不动，v2 不调用）；
  - 归一化后再做 clamp 和（可选）exposure。
- **验收**：死白/死黑区（底座、扫描边）不影响端点；暗部可抬起；中间调不塌。

### Phase 4 —— WB 顺序修复 + 后 gamma 调色
- **目标**：修 `film-color.md` §2 的方向 bug，且 v2 里根除「偏移被后续步骤反咬」。
- **动作**：
  - v2 里手动 (x,y) 偏移**不再**做线性增益（v1 `:343`），改成**归一化后**的 temperature/tint 乘法：
    - `temp 正 → R×1.2 / B×0.8`，`tint 正 → R,B ×1.1 / G ×0.8`（方向：temp 正 = 暖，tint 正 = 品红）；
  - AWB `auto`：v2 下由「逐通道归一化 + gamma 对齐」承接，`awb_gains` 仅作可选粗校正（默认关）；
  - **写方向 pin 测试**：temp 正 → 输出 R>B；tint 正 → R,B>G（一条测试钉死这个 bug）。
- **验收**：方向测试绿；色温/色调滑杆方向与 UI 标注一致。

### Phase 5 —— 参数映射兼容（需要拍板，见 §4）
- **目标**：v1 用户参数在 v2 里语义清楚、可迁移。
- **动作**：给每个参数写「v1 vs v2 语义对照表」+ 迁移测试。
  - `preset_gamma`：v2 = 归一化后 `pow(norm, 1/gamma)`（语义不变）；
  - `exposure_ev`：v2 = 归一化前的密度域**加性偏移**（`D += ev_shift`），或归一化后乘——二选一，建议前者；
  - `tone_pivot/tone_curve`（宽容度曲线）：**保留不变**，仍在管线后段；
  - `preset_contrast*`（含 per-channel）：见 §4 决策 1；
  - `color_mode`（skin_protect/balanced/...）：控制 gamma 对齐强度 + 肤色保护，语义保留。
- **验收**：每个参数迁移测试绿；`--algo v2` 带齐参数跑通。

### Phase 6 —— film_profile 升级（衔接 film-color.md §5）
- **目标**：preset → film_profile，每通道曲线应用在片基归一化**之后**。
- **动作**：
  - `config.yaml` 结构升级（`presets` → `film_profiles` + `curve` 字段）；
  - `preset_mask_r/g/b` 语义调整为「兜底默认」，吸管现采优先；
  - 每通道曲线（LUT/分位点）作用于归一化后信号。
- **验收**：profile 曲线生效；无 profile 时行为与 Phase 5 一致。

### Phase 7 —— 黑白负片（可选）
- **目标**：显式 BW 模式（密度域按 `DENSITY_LUMA` 合并单通道）。
- **动作**：旁路 temp/tint，只留 exposure。
- **验收**：BW 输出为中性灰，无通道偏色。

### Phase 8 —— A/B 验证 + 全量回归 + 灰度
- **目标**：数据说话，安全上线。
- **动作**：
  - `scripts/` 加 `compare_v1_v2.py`：同一图分别 v1/v2 输出，报告：ROI 中性灰通道极差、肤色区色相偏移、直方图端点；
  - 全量回归（v1 所有 test_*.py 绿）；
  - app 端：IPC 穿透 `algo`，UI 加「引擎 v1/v2」切换，默认 v1，灰度观察后翻默认。
- **验收**：A/B 报告中性灰/肤色改善；全量回归绿；可一键回退 v1。

---

## 4. 关键设计决策（需要你拍板）

| # | 决策点 | 选项 | 我的倾向 |
|---|---|---|---|
| 1 | `contrast_r/g/b`（per-channel 对比度）在 v2 的映射 | A. 改为 d_min/d_max **端点偏移**（端点滑块式）；B. 保留线性增益但移到归一化后；C. 移除、并入每通道曲线 | **A**——端点偏移与密度归一化语义一致，且能覆盖「分通道拉动态」的真实需求 |
| 2 | `gamma_alignment`（中间调对齐）去留 | A. 保留，挪到归一化**之后**；B. 移除，靠 temp/tint | **A 保留**——归一化只设端点不设中点，中间调对齐是 OpenLucky 独有优势 |
| 3 | Status M 默认开关 | 开 / 关 | **默认开 + 可配置矩阵**（后续设备标定替换） |
| 4 | 非 RAW（JPEG/TIFF）输入是否先 de-gamma | A. v2 里按 sRGB 解码线性；B. 维持现状（当线性用） | **A**，但单独 PR、单独验收（影响面大） |
| 5 | v1/v2 并存期 | 长期 / 短（对齐后删 v1） | 长期并存，`algo` 显式选择 |

---

## 5. 测试清单（新增/改动）

| 文件 | 测什么 |
|---|---|
| `tests/test_film_v2.py` | 新增：density 纯函数、v2 主流程、方向 pin、中性灰、反相单调 |
| `tests/test_filmparam.py` | 不改（v1 兼容），必要时加 v2 参数穿透 case |
| `tests/test_film.py` | 不改（v1 基线） |
| 新 `scripts/compare_v1_v2.py` | A/B 报告 |

**必须 pin 的断言**：
- 反相：纯灰阶合成负片 → v2 输出灰度单调递增；
- 方向：`temp>0 → R>B`，`tint>0 → R,B>G`（钉死 WB bug）；
- 中性：`decrosstalk([0.18,0.18,0.18])` 输出仍中性；
- 鲁棒：合成图 + 30% 白块，`estimate_density_limits` 端点不被带偏。

---

## 6. 风险与回滚

- **参数语义变化**：v2 输出与 v1 必然不同（这正是目的），但**不要**改变 `--algo v1` 的任何行为；回退 = 默认值仍是 `v1`。
- **非 RAW 输入 de-gamma**（决策 4）会改变现有 TIFF/JPEG 用户观感 → 必须独立里程碑、独立 A/B。
- **Status M 是经验矩阵**：对某些卷可能过冲 → 提供开关 + 强度（强度旋钮与 film_profile 衔接）。
- **ROI 依赖**：`estimate_density_limits` 依赖 `wp_roi_*`；无 ROI 时 fallback 全图并**显式降级提示**（和 v1 现有行为一致）。

---

## 7. 下一步（最先做）

1. 跑一遍 `tests/` 确认 v1 基线全绿；
2. 建 `density.py` + Phase 1 纯函数与单测；
3. 给 `process_film_*` 加 `algo` 参数（v2 分支先抛「未实现」）；
4. 拍板 §4 的 5 个决策。
