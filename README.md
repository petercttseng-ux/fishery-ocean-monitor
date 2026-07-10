# 漁海況速報系統 (Fishery Ocean Conditions Monitor)

## 農業部水產試驗所 漁海況研究小組

以衛星遙測與海洋資料同化產品為基礎的**專業網頁版漁海況速報系統**，
每日自動擷取日本氣象廳 (JMA) NEAR-GOOS 海況分析資料，
透過互動式地圖呈現海表水溫、水下水溫與表層海流。

**線上系統：以 GitHub Pages 部署，每日 06:30 (台灣時間) 自動更新。**

---

## 🌊 資料產品

| 產品 | 內容 | 解析度 | 深度 |
|------|------|--------|------|
| **HIMSST** | 高解析度合成海表水溫（衛星紅外／微波＋現場觀測） | 0.1° × 0.1° | 表層 |
| **NPRSUBT** | NPR-4DVAR 水下水溫分析 | 0.1° × 1/11° | 50 / 100 / 200 / 400 m |
| **NPRSUBC** | NPR-4DVAR 表層海流分析 | 0.1° × 1/11° | 表層 |

系統保留最新 10 筆每日分析。

## 🖥️ 網頁功能

- **互動地圖**：縮放、平移、深色／淺色底圖切換
- **海表水溫／水下水溫**：Jet／Turbo 色階、可調範圍與透明度
- **等溫線**：間距 0.5–5°C 可調、數值標籤
- **表層海流**：流向箭頭（隨縮放自動調整密度）＋流速色階
- **海流疊加**：於海表水溫圖上疊加海流向量
- **溫差比較**：任兩日溫差圖（藍紅發散色階），輔助判識水溫鋒面變動
- **即時讀值**：滑鼠懸停顯示經緯度、水溫、流速（m/s 與節）、流向

## 📁 專案結構

```
├── scripts/
│   └── fetch_data.py            # 資料擷取管線（下載→解析→輸出網頁格式）
├── site/                        # 網頁（GitHub Pages 發布目錄）
│   ├── index.html
│   ├── css/style.css
│   ├── js/app.js                # 前端渲染引擎（Canvas 柵格、等溫線、向量）
│   └── data/                    # 產生的資料（不入版控，由 CI 產生）
├── .github/workflows/
│   └── update-and-deploy.yml    # 每日自動更新＋部署
├── config.py                    # （桌面版）設定
├── data_parser.py               # （桌面版）解析器
└── README.md
```

## 🚀 本地開發

```bash
pip install numpy requests

# 抓取資料（輸出至 site/data/）
python scripts/fetch_data.py --out site/data --days 10

# 啟動本地伺服器預覽
cd site
python -m http.server 8000
# 瀏覽 http://localhost:8000
```

## ⚙️ 自動化部署

GitHub Actions（`.github/workflows/update-and-deploy.yml`）：

1. 每日 22:30 UTC（台灣 06:30）排程執行，亦可手動觸發（workflow_dispatch）
2. 執行 `scripts/fetch_data.py` 下載最新 10 筆 JMA 資料並轉為緊湊二進位格式
3. 以 `actions/deploy-pages` 部署 `site/` 至 GitHub Pages（資料不寫入 repo，不佔版庫空間）
4. 資料快取（actions/cache）避免重複下載

## 📊 資料格式（site/data/）

- `index.json`：產品後設資料（網格定義、可用日期、單位、比例）
- `{product}/{YYYYMMDD}.bin.gz`：int16 little-endian、gzip 壓縮
  - `himsst`：[1, 600, 800]，單位 0.1°C，缺值 -32768
  - `nprsubt`：[4, 395, 550]（50/100/200/400 m），單位 0.01°C
  - `nprsubc`：[2, 396, 551]（u, v），單位 0.01 m/s

## 📚 資料來源

- [JMA HIMSST](https://www.data.jma.go.jp/goos/data/pub/JMA-product/him_sst_pac_D/)（[格式說明](https://www.data.jma.go.jp/goos/data/pub/JMA-product/him_sst_pac_D/Readme_him_sst_pac_D)）
- [JMA NPRSUBT](https://www.data.jma.go.jp/goos/data/pub/JMA-product/npr_subt_jpn_D/)（[格式說明](https://www.data.jma.go.jp/goos/data/pub/JMA-product/npr_subt_jpn_D/Readme_npr_subt_jpn_D)）
- [JMA NPRSUBC](https://www.data.jma.go.jp/goos/data/pub/JMA-product/npr_subc_jpn_D/)（[格式說明](https://www.data.jma.go.jp/goos/data/pub/JMA-product/npr_subc_jpn_D/Readme_npr_subc_jpn_D)）

引用：Hirose et al. (2019), *Ocean Dynamics* 69, 1333–1357（NPR-4DVAR / MOVE/MRI.COM-JPN）

---

© 2026 農業部水產試驗所 漁海況研究小組
