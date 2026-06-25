"""Auto-split a scanned film strip into individual frames.

Designed for long-strip scans from Hasselblad/Imacon (Flextight) scanners and
similar, where one image holds a whole filmstrip. The frame layout is detected
from the image itself (format-agnostic: works for 135 and medium format) rather
than assuming a fixed frame size.

Detection pipeline (see split_strip / detect_frames):

  1. Short axis -> projection band. Average across the long axis to get a cross
     profile and locate the film (inside the dark scanner baffle). Gap detection
     projects over the film with the 135 sprocket columns excluded: sprocket
     perforations are a periodic bright signal along the strip that would
     otherwise read as frame gaps. We keep the band as wide as possible (a wide
     average dilutes a frame's own bright horizontal streaks) -- walking in from
     each edge only as far as the sprocket spike. 120 film has no perforations,
     so when no spike is found the full film width is used. This is the only
     place sprockets matter, and it never affects the crop.

  2. Long axis -> frame gaps. Per row of the projection band compute mean
     brightness and cross-band std. An inter-frame gap is the clear film base:
     bright AND smooth (low std). Bright *image* content (e.g. a smooth bright
     water/sky frame) is bright but textured, so score = brightness *
     (1 - std/std_p98) separates real gaps from bright frames. Otsu thresholds.

  3. Robust frame geometry. Take the strongest gap candidates, estimate the
     frame pitch from their median spacing, then run a RANSAC-style phase fit:
     keep only gaps that land on the regular grid (rejects mid-frame artifacts
     that survive step 2), and interpolate any gap the scan missed.

  4. Cut. Each frame is the span between consecutive gap centres -- a straight
     cut through the middle of each gap. The short-axis crop keeps the whole
     edge by default (trim_baffle drops the black border); it never depends on
     where the cuts land.
"""
import json
from pathlib import Path

import numpy as np
import tifffile

from cli.constants.image_formats import TIFF_FORMATS


_COMPRESSION_MAP = {"none": None, "deflate": "deflate", "lzw": "lzw"}
_BIGTIFF_THRESHOLD = 4_000_000_000

# Detection tuning. Validated against real Flextight 135 strips; exposed here as
# named constants rather than CLI flags to keep the interface small.
_BAFFLE_FRAC = 0.25        # cross level above film-vs-baffle split (of range)
_PROJ_INSET = 0.2          # central film fraction used to gauge image brightness
_SPROCKET_SPIKE = 1.06     # cross > this * central median => still in a sprocket
_STRONG_FRAC = 0.78        # gap candidate kept as "strong" if score >= frac*max
_PHASE_TOL = 0.12          # grid inlier tolerance, as fraction of pitch
_MIN_FRAME_FRAC = 0.55     # reject frames shorter than frac*pitch
_MIN_CAND_WIDTH = 15       # ignore gap runs thinner than this (pixel noise)
_STD_FLOOR = 1e-3          # floor for the texture scale (avoid eps/eps blowup)


def _otsu(v):
    """Otsu's threshold on a 1-D float array."""
    hist, edges = np.histogram(v, bins=256)
    hist = hist.astype(float)
    total = hist.sum()
    if total == 0:
        return float(v.mean())
    p = hist / total
    omega = np.cumsum(p)
    mids = (edges[:-1] + edges[1:]) / 2
    mu = np.cumsum(p * mids)
    mu_t = mu[-1]
    den = omega * (1 - omega)
    den[den == 0] = 1e-12
    return float(mids[np.argmax((mu_t * omega - mu) ** 2 / den)])


def _runs(mask):
    """Yield (start, end_inclusive) index ranges of contiguous True values."""
    out = []
    i, n = 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            out.append((i, j - 1))
            i = j
        else:
            i += 1
    return out


def _smooth(a, win):
    """Centered moving average with edge padding (window forced odd)."""
    win = max(1, int(win) | 1)
    pad = win // 2
    k = np.ones(win) / win
    return np.convolve(np.pad(a, (pad, pad), mode="edge"), k, mode="valid")[:len(a)]


def _to_gray01(arr):
    """Luminance in [0,1] from a uint8/uint16 gray or RGB array."""
    if arr.ndim == 3:
        g = arr[..., :3].astype(np.float64).mean(axis=2)
    else:
        g = arr.astype(np.float64)
    maxv = 65535.0 if arr.dtype == np.uint16 else 255.0
    return g / maxv


def _bands(cross):
    """From the short-axis cross profile, return (film0, film1, proj0, proj1).

    film = the strip inside the dark scanner baffle. proj = the band gap
    detection projects over: the film with the 135 sprocket columns excluded.

    Sprocket perforations are a periodic bright signal *along* the strip that
    would otherwise read as frame gaps, so they must be kept out of the
    projection -- but we want as much picture width as possible (a wide average
    dilutes a frame's own bright horizontal streaks, e.g. a water/sky horizon).
    So we don't narrow to the centre; we walk in from each film edge only as far
    as the sprocket spike, and no further. 120 film has no perforations: when no
    spike is found we keep the full film width. This is the only place sprockets
    are considered, and it never affects the crop -- only where we measure.
    """
    cmax, cmin = float(cross.max()), float(cross.min())
    film = np.where(cross > cmin + _BAFFLE_FRAC * (cmax - cmin))[0]
    if len(film) == 0:
        return 0, len(cross) - 1, 0, len(cross) - 1
    fx0, fx1 = int(film[0]), int(film[-1])
    fw = fx1 - fx0 + 1
    lo = fx0 + int(_PROJ_INSET * fw)
    hi = fx1 - int(_PROJ_INSET * fw)
    central_med = float(np.median(cross[lo:hi])) if hi > lo else float(np.median(cross))
    spike = _SPROCKET_SPIKE * central_med

    def skip_spike(seq, edge):
        """Walk inward from a film edge; if a bright sprocket spike is found,
        return the point just past it (135). If none exists (120), return the
        edge unchanged -- never collapse the band."""
        seen = False
        for i in seq:
            if cross[i] > spike:
                seen = True
            elif seen:
                return i
        return edge

    p0 = skip_spike(range(fx0, fx0 + fw // 2), fx0)
    p1 = skip_spike(range(fx1, fx0 + fw // 2, -1), fx1)
    if p1 <= p0:                         # degenerate; project over full film
        p0, p1 = fx0, fx1
    return fx0, fx1, p0, p1


def _filter_kelp(spans, content, thr, min_content, bridge, pad):
    """Drop pure-kelp regions and keep only the textured (content) parts.

    For each detected frame span, find runs where the texture profile `content`
    exceeds `thr`, bridge runs separated by less than `bridge` (a smooth band
    inside one frame is not a frame break), drop runs shorter than `min_content`
    (these are uniform kelp -- blank or fully exposed -- with no image), and keep
    the rest padded by `pad`. A large uniform margin at a span edge is trimmed
    away; a small one (a frame's own smooth border) is kept.
    """
    mask = content > thr
    out = []
    for a, b in spans:
        runs = [(a + s, a + e) for s, e in _runs(mask[a:b])]
        merged = []
        for s, e in runs:
            if merged and s - merged[-1][1] <= bridge:
                merged[-1] = (merged[-1][0], e)
            else:
                merged.append((s, e))
        for s, e in merged:
            if e - s < min_content:
                continue
            ns = a if (s - a) <= pad else max(a, s - pad)
            ne = b if (b - e) <= pad else min(b, e + pad)
            out.append((ns, ne))
    return out


def detect_frames(arr, orientation="auto", trim_baffle=False, frames=None,
                  drop_kelp=False):
    """Detect frame boxes in a strip scan.

    Cuts are made straight through the middle of each inter-frame gap, so the
    short-axis crop is independent of where the cuts land. By default each frame
    keeps the entire short edge (sprockets and baffle included); trim_baffle=True
    crops off the dark scanner baffle (keeping the sprockets/film border).

    Gap detection projects over the central band of the film -- this sidesteps
    the sprockets entirely, so no sprocket detection is performed.

    frames: when set, bypass detection and divide the long axis into that many
    equal parts. Use for "kelp" strips -- large unexposed (clear) or fully
    exposed regions whose frame layout cannot be inferred from content.

    drop_kelp: discard pure-kelp regions (large uniform, blank or fully exposed)
    and keep only the textured/content parts within each detected frame.

    Returns a dict: {long_axis, film_band, proj_band, pitch, boxes, forced,
    low_confidence}; boxes is a list of (x0, y0, x1, y1) in pixel coordinates.
    """
    g = _to_gray01(arr)
    H, W = g.shape[:2]
    if orientation == "auto":
        long_y = H >= W
    else:
        long_y = orientation == "vertical"

    # 1. short-axis bands: film (inside baffle) + central projection band
    cross = g.mean(axis=0) if long_y else g.mean(axis=1)
    fx0, fx1, p0, p1 = _bands(cross)
    cmin = float(cross.min())

    N = H if long_y else W
    short_full = W if long_y else H
    cx0, cx1 = (fx0, fx1) if trim_baffle else (0, short_full)

    def _boxes(spans):
        if long_y:
            return [(cx0, a, cx1, b) for a, b in spans]
        return [(a, cx0, b, cx1) for a, b in spans]

    def _result(boxes, pitch, forced=False, low_confidence=False):
        return {"long_axis": "y" if long_y else "x",
                "film_band": [fx0, fx1], "proj_band": [p0, p1],
                "pitch": int(pitch), "boxes": boxes,
                "forced": forced, "low_confidence": low_confidence}

    # Manual override: divide the long axis into `frames` equal parts.
    if frames and frames > 0:
        cuts = [round(i * N / frames) for i in range(frames + 1)]
        spans = list(zip(cuts[:-1], cuts[1:]))
        return _result(_boxes(spans), round(N / frames), forced=True)

    # 2. long-axis gap score on the central projection band
    band = g[:, p0:p1] if long_y else g[p0:p1, :]
    row_mean = band.mean(axis=1) if long_y else band.mean(axis=0)
    row_std = band.std(axis=1) if long_y else band.std(axis=0)
    # Floor the texture scale: a perfectly uniform band (clean or very
    # high-contrast film) yields row_std ~1e-16, and dividing that epsilon by an
    # equally tiny percentile would wrongly zero the smoothness term and crush
    # every bright row's score. The floor keeps uniform rows scored as smooth.
    std_p98 = max(float(np.percentile(row_std, 98)), _STD_FLOOR)
    score = row_mean * (1.0 - np.clip(row_std / std_p98, 0, 1))
    thr = max(_otsu(score),
              np.median(score) + 0.4 * (score.max() - np.median(score)))
    is_gap = score > thr

    # Texture (content) profile for drop_kelp: smoothed horizontal variation.
    # Real image content has texture; kelp -- blank (clear) or fully exposed
    # (dense) -- and inter-frame gaps are uniform (near-zero).
    NL = len(row_std)
    content = _smooth(row_std, max(15, int(0.01 * NL)))
    baffle = row_mean < (cmin + 0.45 * (np.median(row_mean) - cmin))

    # image extent along the long axis (between the end baffles)
    nonb = np.where(~baffle)[0]
    if len(nonb) == 0:
        return _result([], 0, low_confidence=True)
    y0, y1 = int(nonb[0]), int(nonb[-1])

    # 3. candidates -> narrow gaps -> pitch -> phase grid
    cand = [((a + b) // 2, (b - a + 1), float(score[a:b + 1].max()))
            for a, b in _runs(is_gap) if (b - a + 1) >= _MIN_CAND_WIDTH]
    if cand:
        smax = max(s for _, _, s in cand)
        strong = [(c, w, s) for c, w, s in cand if s >= _STRONG_FRAC * smax]
    else:
        strong = []
    strong_c = sorted(c for c, _, _ in strong)

    # Typical inter-frame gap width; median is robust to a gap that merged with
    # adjacent bright content into one wide run. "narrow" gaps are the real
    # inter-frame gaps -- a blank/unexposed frame merges with its neighbouring
    # gaps into one WIDE bright block, which we must keep out of the geometry.
    gap_w = int(np.median([w for _, w, _ in strong])) if strong else _MIN_CAND_WIDTH
    narrow_c = sorted(c for c, w, _ in strong if w <= 1.6 * gap_w)

    # Frame pitch from the narrow gaps: the smallest spacing the others are
    # ~multiples of. Robust to gaps the scan missed (e.g. on both sides of a
    # blank frame, which otherwise halves a naive median).
    if len(narrow_c) >= 2:
        diffs = np.diff(narrow_c)
        med = float(np.median(diffs))
        base = [int(d) for d in diffs if d >= 0.3 * med]
        pitch = min(base) if base else int(med)
    elif len(strong_c) >= 2:
        pitch = int(np.median(np.diff(strong_c)))
    else:
        pitch = (y1 - y0)

    # Phase: the regular grid the narrow gaps sit on (consensus over all of them,
    # so one shifted/merged candidate can't drag a boundary into bright content).
    ph = narrow_c[0] % pitch if narrow_c else (strong_c[0] % pitch if strong_c else 0)
    if len(narrow_c) >= 2 and pitch > 0:
        tol = _PHASE_TOL * pitch
        best = (-1, ph)
        for c0 in narrow_c:
            cph = c0 % pitch
            cnt = sum(1 for c in narrow_c
                      if abs(((c - cph + pitch / 2) % pitch) - pitch / 2) <= tol)
            if cnt > best[0]:
                best = (cnt, cph)
        ph = best[1]

    # Gap positions from the fitted grid, snapped to a narrow clean candidate
    # when one sits nearby (sub-pixel accuracy), else the pure grid line (this
    # interpolates gaps the scan missed, e.g. on both sides of a blank frame).
    # Near the strip ends we only accept a real (snapped) gap, never a phantom.
    gaps, n_interp = [], 0
    if pitch > 0:
        snap_tol = _PHASE_TOL * pitch
        k0 = int(np.floor((y0 - ph) / pitch))
        k1 = int(np.ceil((y1 - ph) / pitch))
        for k in range(k0, k1 + 1):
            line = ph + k * pitch
            if line <= y0 or line >= y1:
                continue
            near = [(abs(c - line), c) for c in narrow_c if abs(c - line) <= snap_tol]
            at_end = line <= y0 + 0.3 * pitch or line >= y1 - 0.3 * pitch
            if near:
                gaps.append(min(near)[1])
            elif not at_end:
                gaps.append(int(line))
                n_interp += 1
    else:
        gaps = list(narrow_c)
    gaps = sorted(set(gaps))

    # 4. Cut straight through the middle of each inter-frame gap: a frame is the
    #    span between consecutive gap centres. By design we do NOT crop tightly
    #    to content -- keeping a thin film-base border is fine and removes any
    #    risk of shaving real image (e.g. bright sky/water against a gap).
    bounds = [y0] + gaps + [y1]
    min_frame = int(_MIN_FRAME_FRAC * pitch) if pitch > 0 else 0
    spans = [(a, b) for a, b in zip(bounds[:-1], bounds[1:]) if b - a >= min_frame]

    # Don't trim the head/tail: the first and last frames keep their outward
    # edge all the way to the image border (no cut facing the strip ends).
    if spans:
        spans[0] = (0, spans[0][1])
        spans[-1] = (spans[-1][0], N)

    if drop_kelp:
        # Discard pure-kelp regions, keeping only textured parts -- but ONLY for
        # spans that lack a reliable surrounding gap structure. A smooth but real
        # frame (e.g. water/sky) is bounded by real inter-frame gaps and must be
        # kept; kelp has no such structure. So a span is "kelp-suspect" only when
        # there are no reliable gaps at all, or the span is oversized (it spans a
        # gapless kelp stretch). Otsu splits the texture profile content/uniform.
        c_thr = max(_otsu(content), 0.12 * float(content.max()))
        reliable = len(narrow_c) >= 2
        kp = dict(thr=c_thr,
                  min_content=max(2 * (max(15, int(0.01 * NL)) | 1), int(0.04 * NL)),
                  bridge=int(0.04 * NL),
                  pad=max(15, int(0.02 * NL)))
        filtered = []
        for a, b in spans:
            suspect = (not reliable) or (pitch > 0 and (b - a) > 1.5 * pitch)
            filtered.extend(_filter_kelp([(a, b)], content, **kp) if suspect
                            else [(a, b)])
        spans = filtered

    # Low confidence: too few observed gaps to trust the pitch, a collapse to a
    # single frame, or mostly-interpolated cut lines -- hallmarks of a "kelp"
    # strip (large blank/over-exposed regions). The caller suggests --frames.
    low_conf = (len(narrow_c) < 2 or len(spans) <= 1
                or (len(gaps) > 0 and n_interp > 0.5 * len(gaps)))

    return _result(_boxes(spans), pitch, low_confidence=bool(low_conf))


def _rot90_cw(img, degrees):
    """Rotate an array clockwise by 0/90/180/270 degrees."""
    k = (-(degrees // 90)) % 4   # np.rot90 is CCW for positive k
    return np.rot90(img, k=k) if k else img


def _write_preview(arr, det, preview_path):
    """Write a downscaled overlay PNG with detected frame boxes drawn."""
    from PIL import Image, ImageDraw

    g = _to_gray01(arr)
    H, W = g.shape[:2]
    scale = max(H, W) / 1600.0 or 1.0
    pw, ph = max(1, int(W / scale)), max(1, int(H / scale))
    im = Image.fromarray((np.clip(g, 0, 1) * 255).astype(np.uint8))
    im = im.resize((pw, ph)).convert("RGB")
    d = ImageDraw.Draw(im)
    for i, (x0, y0, x1, y1) in enumerate(det["boxes"], 1):
        box = [int(x0 / scale), int(y0 / scale), int(x1 / scale), int(y1 / scale)]
        d.rectangle(box, outline=(255, 0, 0), width=2)
        d.text((box[0] + 3, box[1] + 3), str(i), fill=(255, 255, 0))
    preview_path = Path(preview_path)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(str(preview_path))


def split_strip(input_path, output_dir, orientation="auto", rotate=0,
                trim_baffle=False, frames=None, drop_kelp=False,
                compression="deflate", prefix="frame", preview=None,
                dry_run=False):
    """Split a strip scan into per-frame TIFFs.

    Args:
        input_path: strip image readable by tifffile (.tif/.tiff/.fff).
        output_dir: directory to write frame_NNN.tif files into.
        orientation: 'auto' | 'horizontal' | 'vertical' (strip long axis).
        rotate: per-frame output rotation, clockwise degrees (0/90/180/270).
        trim_baffle: crop off the dark scanner baffle (keeps sprockets/film).
            Default keeps the entire short edge.
        frames: force this many equal-size frames (manual override for "kelp"
            strips with large blank/over-exposed regions). Default auto-detects.
        drop_kelp: discard pure-kelp regions (uniform blank/over-exposed) and
            keep only the parts with real image content.
        compression: 'deflate' (default) | 'lzw' | 'none'.
        prefix: output filename prefix.
        preview: optional path to write an annotated overlay PNG.
        dry_run: detect and report (and write preview) but write no frames.

    Returns:
        bool: True on success. A JSON manifest of detected frames is printed
        to stdout.
    """
    try:
        input_path = Path(input_path)
        output_dir = Path(output_dir)

        if compression not in _COMPRESSION_MAP:
            print(f"Error: Unknown compression '{compression}'. "
                  f"Expected one of: {', '.join(_COMPRESSION_MAP)}")
            return False
        if rotate not in (0, 90, 180, 270):
            print(f"Error: --rotate must be 0/90/180/270, got {rotate}")
            return False
        if not input_path.exists():
            print(f"Error: Input file does not exist: {input_path}")
            return False

        with tifffile.TiffFile(str(input_path)) as tif:
            page = max(tif.pages, key=lambda p: int(p.shape[0]) * int(p.shape[1]))
            arr = page.asarray()

        # 丢弃第4个(IR)通道，仅保留RGB（TODO(IR): 以后暂存+回填）
        if arr.ndim == 3 and arr.shape[2] > 3:
            arr = arr[:, :, :3]

        det = detect_frames(arr, orientation=orientation,
                            trim_baffle=trim_baffle, frames=frames,
                            drop_kelp=drop_kelp)
        boxes = det["boxes"]

        if preview:
            _write_preview(arr, det, preview)
            print(f"Preview written: {preview}")

        manifest = {
            "input": str(input_path),
            "long_axis": det["long_axis"],
            "pitch": det["pitch"],
            "film_band": det["film_band"],
            "proj_band": det["proj_band"],
            "forced": det.get("forced", False),
            "low_confidence": det.get("low_confidence", False),
            "frame_count": len(boxes),
            "frames": [],
        }

        if not boxes:
            print("Warning: no frames detected. This looks like a 'kelp' strip "
                  "(largely blank or fully exposed); pass --frames N to split it "
                  "into N equal parts.")
            print(json.dumps(manifest, ensure_ascii=False))
            return False

        if det.get("low_confidence") and not det.get("forced"):
            print(f"Warning: low-confidence detection ({len(boxes)} frame(s)); "
                  "if this looks wrong (e.g. a blank/over-exposed 'kelp' strip), "
                  "re-run with --frames N to force the count.")

        cmp = _COMPRESSION_MAP[compression]
        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
        width = max(3, len(str(len(boxes))))
        for i, (x0, y0, x1, y1) in enumerate(boxes, 1):
            crop = arr[y0:y1, x0:x1]
            if rotate:
                crop = _rot90_cw(crop, rotate)
            name = f"{prefix}_{str(i).zfill(width)}.tif"
            out_file = output_dir / name
            photometric = "rgb" if crop.ndim == 3 and crop.shape[2] >= 3 else "minisblack"
            entry = {"index": i, "box": [int(x0), int(y0), int(x1), int(y1)],
                     "size": [int(crop.shape[1]), int(crop.shape[0])],
                     "output": str(out_file).replace("\\", "/")}
            manifest["frames"].append(entry)
            if dry_run:
                continue
            tifffile.imwrite(
                str(out_file), crop,
                photometric=photometric,
                compression=cmp,
                bigtiff=crop.nbytes >= _BIGTIFF_THRESHOLD,
            )
            print(f"[{i}/{len(boxes)}] {name} "
                  f"({crop.shape[1]}x{crop.shape[0]})")

        if dry_run:
            print(f"Dry run: detected {len(boxes)} frame(s), wrote nothing.")
        else:
            print(f"Done: {len(boxes)} frame(s) -> {output_dir}")
        print(json.dumps(manifest, ensure_ascii=False))
        return True

    except Exception as e:
        print(f"Error splitting strip: {e}")
        import traceback
        traceback.print_exc()
        return False
