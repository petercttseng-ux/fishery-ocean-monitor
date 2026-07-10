# -*- coding: utf-8 -*-
"""
漁海況速報系統 - 資料擷取管線
農業部水產試驗所 漁海況研究小組

從 JMA (日本氣象廳) NEAR-GOOS 伺服器下載最新海況資料，解析後輸出為
網頁前端使用的緊湊二進位格式 (int16 little-endian, gzip) 與 index.json。

資料格式依據 JMA 官方 Readme:
  - Readme_him_sst_pac_D  : 601 記錄 (1 標頭 + 600 資料列), 800 值/列, 3 位數, 0.1°C
  - Readme_npr_subt_jpn_D : 1585 記錄, 4 深度區塊 (各 1 深度標頭 + 395 資料列), 550 值/列, 4 位數, 0.01°C
  - Readme_npr_subc_jpn_D : 795 記錄, 2 分量區塊 (各 1 方向標頭 + 396 資料列), 551 值/列, 4 位數, 1 cm/s

用法:
    python scripts/fetch_data.py --out site/data --days 10
"""

import argparse
import gzip
import io
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import requests

# ============================================================================
# 資料源設定
# ============================================================================
PRODUCTS = {
    "himsst": {
        "name": "海表水溫",
        "longName": "高解析度合成海表水溫 (HIMSST)",
        "base_url": "https://www.data.jma.go.jp/goos/data/pub/JMA-product/him_sst_pac_D/",
        "stem": "him_sst_pac_D",
        # 格點中心: 59.95N→0.05N, 100.05E→179.95E
        "lat0": 59.95, "lat1": 0.05,
        "lon0": 100.05, "lon1": 179.95,
        "n_rows": 600, "n_cols": 800,
        "cell_width": 3,
        "scale": 0.1,
        "missing": [999, 888],
        "unit": "°C",
    },
    "nprsubt": {
        "name": "水下水溫",
        "longName": "水下水溫分析 NPR-4DVAR (NPRSUBT)",
        "base_url": "https://www.data.jma.go.jp/goos/data/pub/JMA-product/npr_subt_jpn_D/",
        "stem": "npr_subt_jpn_D",
        "lat0": 56.2, "lat1": 16.8,
        "lon0": 113.545455, "lon1": 163.454545,
        "n_rows": 395, "n_cols": 550,
        "cell_width": 4,
        "scale": 0.01,
        "missing": [9999],
        "unit": "°C",
        "depths": [50, 100, 200, 400],
    },
    "nprsubc": {
        "name": "表層海流",
        "longName": "表層海流分析 NPR-4DVAR (NPRSUBC)",
        "base_url": "https://www.data.jma.go.jp/goos/data/pub/JMA-product/npr_subc_jpn_D/",
        "stem": "npr_subc_jpn_D",
        "lat0": 56.25, "lat1": 16.75,
        "lon0": 113.5, "lon1": 163.5,
        "n_rows": 396, "n_cols": 551,
        "cell_width": 4,
        "scale": 0.01,  # 1 cm/s -> m/s
        "missing": [9999],
        "unit": "m/s",
        "components": ["u", "v"],
    },
}

REQUEST_TIMEOUT = 60
RETRY_COUNT = 2
RETRY_DELAY = 2
LOOKBACK_DAYS = 45      # 由今日往回探測的最大天數
MISSING_I16 = -32768    # 輸出檔中的缺值代碼

session = requests.Session()
session.headers.update({"User-Agent": "TFRI-FisheryOceanMonitor/2.0 (research; contact via GitHub)"})


# ============================================================================
# 下載
# ============================================================================
def http_get(url: str):
    """GET，404 回傳 None，其他錯誤重試。"""
    last_err = None
    for attempt in range(RETRY_COUNT + 1):
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(RETRY_DELAY * (attempt + 1))
    print(f"  [警告] 下載失敗 {url}: {last_err}", file=sys.stderr)
    return None


def url_candidates(cfg, datestr):
    """該日期所有可能的檔案 URL（優先 re_ 再分析資料，再近即時資料）。"""
    y, m = datestr[:4], datestr[4:6]
    subs = ["", f"{y}/", f"{y}/{m}/"]
    urls = []
    for prefix in ("re_", ""):
        for sub in subs:
            for ext in (".txt", ".txt.gz"):
                urls.append(cfg["base_url"] + sub + prefix + cfg["stem"] + datestr + ext)
    return urls


def fetch_date(cfg, datestr, hint=None):
    """下載指定日期資料，回傳 (text, url_pattern_hint) 或 (None, hint)。"""
    urls = url_candidates(cfg, datestr)
    if hint:
        # 先試上次成功的樣式
        hinted = hint.replace("{date}", datestr).replace("{y}", datestr[:4]).replace("{m}", datestr[4:6])
        urls = [hinted] + [u for u in urls if u != hinted]
    for url in urls:
        r = http_get(url)
        if r is None:
            continue
        content = r.content
        if url.endswith(".gz") or content[:2] == b"\x1f\x8b":
            try:
                content = gzip.decompress(content)
            except OSError:
                pass
        text = content.decode("ascii", errors="replace")
        # 簡單健全性檢查：至少要有預期的列數
        if text.count("\n") < cfg["n_rows"]:
            continue
        pattern = (url
                   .replace(datestr, "{date}")
                   .replace(f"/{datestr[:4]}/", "/{y}/")
                   )
        return text, pattern
    return None, hint


# ============================================================================
# 解析（依官方 Readme 之固定記錄位置，附自動偵測備援）
# ============================================================================
def parse_fixed_width(lines, n_rows, n_cols, width) -> np.ndarray:
    """向量化解析固定寬度整數網格。"""
    total = n_cols * width
    buf = bytearray()
    for i in range(n_rows):
        raw = lines[i].rstrip("\r\n").ljust(total)[:total]
        buf.extend(raw.encode("ascii", errors="replace"))
    arr = np.frombuffer(bytes(buf), dtype="S1").reshape(n_rows, n_cols, width)
    cells = arr.view(f"S{width}").reshape(n_rows, n_cols)
    flat = np.char.strip(cells.astype(f"U{width}"))
    try:
        return flat.astype(np.int32)
    except ValueError:
        out = np.full((n_rows, n_cols), MISSING_I16, dtype=np.int32)
        for i in range(n_rows):
            for j in range(n_cols):
                try:
                    out[i, j] = int(flat[i, j])
                except ValueError:
                    out[i, j] = MISSING_I16
        return out


def normalize(grid: np.ndarray, missing_codes) -> np.ndarray:
    g = grid.astype(np.int32)
    for code in missing_codes:
        g[g == code] = MISSING_I16
    return np.clip(g, -32768, 32767).astype("<i2")


def parse_header_date(line: str):
    m = re.match(r"\s*(\d{4})\s+(\d{1,2})\s+(\d{1,2})", line.strip())
    if m:
        return f"{int(m.group(1)):04d}{int(m.group(2)):02d}{int(m.group(3)):02d}"
    digits = re.sub(r"\D", "", line)[:8]
    return digits if len(digits) == 8 else None


def is_data_row(line, n_cols, width):
    raw = line.rstrip("\r\n")
    return len(raw) >= n_cols * width * 0.9 and re.fullmatch(r"[\d\s\-]+", raw or "x")


def find_data_start(lines, width, n_cols, from_line, search=6):
    for k in range(from_line, min(from_line + search, len(lines))):
        if is_data_row(lines[k], n_cols, width):
            return k
    return from_line


def process_himsst(text, cfg):
    lines = text.splitlines()
    date = parse_header_date(lines[0])
    start = find_data_start(lines, cfg["cell_width"], cfg["n_cols"], 1)
    grid = parse_fixed_width(lines[start:], cfg["n_rows"], cfg["n_cols"], cfg["cell_width"])
    return date, normalize(grid, cfg["missing"])[np.newaxis, :, :]


def process_blocks(text, cfg, n_blocks):
    """NPRSUBT/NPRSUBC 共用：標頭 + n 個(區塊標頭+資料列)區塊。"""
    lines = text.splitlines()
    date = parse_header_date(lines[0])
    blocks, cursor = [], 1
    for _ in range(n_blocks):
        start = find_data_start(lines, cfg["cell_width"], cfg["n_cols"], cursor)
        grid = parse_fixed_width(lines[start:], cfg["n_rows"], cfg["n_cols"], cfg["cell_width"])
        blocks.append(normalize(grid, cfg["missing"]))
        cursor = start + cfg["n_rows"]
    return date, np.stack(blocks, axis=0)


def process(key, text, cfg):
    if key == "himsst":
        return process_himsst(text, cfg)
    if key == "nprsubt":
        return process_blocks(text, cfg, len(cfg["depths"]))
    return process_blocks(text, cfg, 2)


def grid_meta(cfg):
    return {
        "lat0": round(cfg["lat0"], 6),
        "dlat": round((cfg["lat1"] - cfg["lat0"]) / (cfg["n_rows"] - 1), 8),
        "lon0": round(cfg["lon0"], 6),
        "dlon": round((cfg["lon1"] - cfg["lon0"]) / (cfg["n_cols"] - 1), 8),
        "nRows": cfg["n_rows"],
        "nCols": cfg["n_cols"],
    }


# ============================================================================
# 主流程
# ============================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site/data")
    ap.add_argument("--days", type=int, default=10, help="每項產品保留最新筆數")
    ap.add_argument("--products", default="himsst,nprsubt,nprsubc")
    args = ap.parse_args()

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    wanted = [p.strip() for p in args.products.split(",") if p.strip()]
    today = datetime.now(timezone.utc).date()

    index = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "products": {},
    }

    for key in wanted:
        cfg = PRODUCTS[key]
        pdir = out_root / key
        pdir.mkdir(parents=True, exist_ok=True)
        print(f"\n=== {cfg['longName']} ===")

        dates_ok, hint, misses = [], None, 0
        for back in range(LOOKBACK_DAYS + 1):
            if len(dates_ok) >= args.days:
                break
            d = today - timedelta(days=back)
            datestr = d.strftime("%Y%m%d")
            gz_path = pdir / f"{datestr}.bin.gz"
            if gz_path.exists() and gz_path.stat().st_size > 0:
                print(f"  {datestr} 已存在，略過")
                dates_ok.append(datestr)
                continue
            text, hint = fetch_date(cfg, datestr, hint)
            if text is None:
                misses += 1
                # 找到第一筆後，連續多日缺檔即停止（資料尾端）
                if dates_ok and misses >= 5:
                    break
                continue
            misses = 0
            try:
                hdr_date, data = process(key, text, cfg)
                use_date = hdr_date or datestr
                valid = int(np.sum(data != MISSING_I16))
                if valid == 0:
                    print(f"  [警告] {datestr} 無有效格點，略過")
                    continue
                gz_path = pdir / f"{use_date}.bin.gz"
                with gzip.open(gz_path, "wb", compresslevel=6) as f:
                    f.write(data.tobytes())
                print(f"  ✓ {use_date}: 區塊{data.shape}, 有效格點 {valid:,}, "
                      f"{gz_path.stat().st_size/1024:.0f} KB")
                dates_ok.append(use_date)
            except Exception as e:  # noqa: BLE001
                print(f"  [錯誤] {datestr}: {e}", file=sys.stderr)

        dates_ok = sorted(set(dates_ok), reverse=True)[: args.days]
        keep = {f"{d}.bin.gz" for d in dates_ok}
        for f in pdir.glob("*.bin.gz"):
            if f.name not in keep:
                f.unlink()

        meta = {
            "name": cfg["name"],
            "longName": cfg["longName"],
            "dates": dates_ok,
            "grid": grid_meta(cfg),
            "scale": cfg["scale"],
            "missing": MISSING_I16,
            "unit": cfg["unit"],
            "source": cfg["base_url"],
        }
        if "depths" in cfg:
            meta["depths"] = cfg["depths"]
        if "components" in cfg:
            meta["components"] = cfg["components"]
        index["products"][key] = meta

    (out_root / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n完成。index.json 已寫入 {out_root}")

    if not any(index["products"].get(k, {}).get("dates") for k in wanted):
        print("[錯誤] 所有產品皆無資料", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
