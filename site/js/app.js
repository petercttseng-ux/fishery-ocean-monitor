/* ============================================================
   漁海況速報系統 - 前端渲染引擎
   農業部水產試驗所 漁海況研究小組

   資料：int16 LE 網格 (gzip)，缺值 -32768
     himsst : [1, 600, 800]  scale 0.1  °C
     nprsubt: [4, 395, 550]  scale 0.01 °C (50/100/200/400 m)
     nprsubc: [2, 396, 551]  scale 0.01 m/s (u, v)
   ============================================================ */
"use strict";

const MISSING = -32768;
const DATA_ROOT = "data/";

/* ---------------- 全域狀態 ---------------- */
const state = {
  index: null,
  product: "himsst",
  date: null,
  depthIdx: 0,
  iso: true,
  isoInterval: 2,
  isoLabels: true,
  overlayCurrent: false,
  compare: false,
  compareDate: null,
  compareRange: 2,
  cmap: "jet",
  vmin: 0,
  vmax: 32,
  opacity: 0.9,
};

const fieldCache = new Map();   // url -> Int16Array
const contourCache = new Map(); // key -> segments Float32Array (lon,lat pairs)
let map, canvas, ctx;
let redrawPending = false;

/* ---------------- 工具 ---------------- */
const $ = id => document.getElementById(id);
const fmtDate = d => `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`;

function setStatus(text, cls) {
  $("statusText").textContent = text;
  const el = $("headerStatus");
  el.classList.remove("ok", "err");
  if (cls) el.classList.add(cls);
}
function showLoading(on, text) {
  $("loading").classList.toggle("hidden", !on);
  if (text) $("loadingText").textContent = text;
}
function showError(msg) {
  const b = $("errorBanner");
  b.innerHTML = msg;
  b.classList.remove("hidden");
}

/* ---------------- 色階 ---------------- */
function jetColor(t) {
  const r = Math.min(Math.max(1.5 - Math.abs(4 * t - 3), 0), 1);
  const g = Math.min(Math.max(1.5 - Math.abs(4 * t - 2), 0), 1);
  const b = Math.min(Math.max(1.5 - Math.abs(4 * t - 1), 0), 1);
  return [r * 255, g * 255, b * 255];
}
function turboColor(t) {
  // Google Turbo colormap 多項式近似
  const r = 34.61 + t * (1172.33 + t * (-10793.56 + t * (33300.12 + t * (-38394.49 + t * 14825.05))));
  const g = 23.31 + t * (557.33 + t * (1225.33 + t * (-3574.96 + t * (1073.77 + t * 707.56))));
  const b = 27.2 + t * (3211.1 + t * (-15327.97 + t * (27814.0 + t * (-22569.18 + t * 6838.66))));
  return [Math.min(Math.max(r, 0), 255), Math.min(Math.max(g, 0), 255), Math.min(Math.max(b, 0), 255)];
}
function divergingColor(t) {
  // 藍-白-紅 (負值藍、正值紅)
  if (t < 0.5) {
    const u = t / 0.5;
    return [30 + 225 * u, 60 + 195 * u, 255];
  }
  const u = (t - 0.5) / 0.5;
  return [255, 255 - 195 * u, 255 - 225 * u];
}
function buildLUT(kind) {
  const lut = new Uint8Array(256 * 3);
  const fn = kind === "turbo" ? turboColor : kind === "div" ? divergingColor : jetColor;
  for (let i = 0; i < 256; i++) {
    const [r, g, b] = fn(i / 255);
    lut[i * 3] = r; lut[i * 3 + 1] = g; lut[i * 3 + 2] = b;
  }
  return lut;
}
const LUTS = { jet: buildLUT("jet"), turbo: buildLUT("turbo"), div: buildLUT("div") };

/* ---------------- 資料載入 ---------------- */
async function loadIndex() {
  const r = await fetch(DATA_ROOT + "index.json", { cache: "no-cache" });
  if (!r.ok) throw new Error("index.json 載入失敗");
  return r.json();
}
async function loadField(product, date) {
  const url = `${DATA_ROOT}${product}/${date}.bin.gz`;
  if (fieldCache.has(url)) return fieldCache.get(url);
  const r = await fetch(url);
  if (!r.ok) throw new Error(`資料檔載入失敗: ${url}`);
  let buf = new Uint8Array(await r.arrayBuffer());
  if (buf[0] === 0x1f && buf[1] === 0x8b) buf = pako.inflate(buf);
  const arr = new Int16Array(buf.buffer, buf.byteOffset, buf.byteLength / 2);
  if (fieldCache.size > 14) fieldCache.delete(fieldCache.keys().next().value);
  fieldCache.set(url, arr);
  return arr;
}

/* ---------------- 目前欄位組合 ---------------- */
function productMeta() { return state.index.products[state.product]; }
function blockOffset(meta) {
  const g = meta.grid;
  return state.product === "nprsubt" ? state.depthIdx * g.nRows * g.nCols : 0;
}

/** 取得目前要渲染的純量場 {data, offset, grid, scale, vmin, vmax, lut, unit, diverging} */
async function currentScalarField() {
  const meta = productMeta();
  const g = meta.grid;
  const raw = await loadField(state.product, state.date);

  if (state.product === "nprsubc") {
    // 流速場（衍生）
    const key = `spd|${state.date}`;
    let spd = fieldCache.get(key);
    if (!spd) {
      const n = g.nRows * g.nCols;
      spd = new Int16Array(n);
      for (let i = 0; i < n; i++) {
        const u = raw[i], v = raw[n + i];
        spd[i] = (u === MISSING || v === MISSING) ? MISSING : Math.round(Math.sqrt(u * u + v * v));
      }
      fieldCache.set(key, spd);
    }
    return { data: spd, offset: 0, grid: g, scale: meta.scale,
             vmin: 0, vmax: 2, lut: LUTS[state.cmap], unit: "m/s", uv: raw };
  }

  if (state.compare && state.compareDate && state.compareDate !== state.date) {
    const rawB = await loadField(state.product, state.compareDate);
    const off = blockOffset(meta);
    const key = `diff|${state.product}|${state.depthIdx}|${state.date}|${state.compareDate}`;
    let diff = fieldCache.get(key);
    if (!diff) {
      const n = g.nRows * g.nCols;
      diff = new Int16Array(n);
      for (let i = 0; i < n; i++) {
        const a = raw[off + i], b = rawB[off + i];
        diff[i] = (a === MISSING || b === MISSING) ? MISSING : a - b;
      }
      fieldCache.set(key, diff);
    }
    const R = state.compareRange;
    return { data: diff, offset: 0, grid: g, scale: meta.scale,
             vmin: -R, vmax: R, lut: LUTS.div, unit: "°C", diverging: true };
  }

  return { data: raw, offset: blockOffset(meta), grid: g, scale: meta.scale,
           vmin: state.vmin, vmax: state.vmax, lut: LUTS[state.cmap], unit: meta.unit };
}

/* ---------------- 投影輔助 ---------------- */
function makeProjector() {
  const size = map.getSize();
  const tl = map.containerPointToLatLng([0, 0]);
  const br = map.containerPointToLatLng([size.x, size.y]);
  const mercY = lat => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
  const ax = size.x / (br.lng - tl.lng);
  const bx = -tl.lng * ax;
  const my0 = mercY(tl.lat);
  const ay = size.y / (mercY(br.lat) - my0);
  return {
    project(lat, lon) { return [ax * lon + bx, ay * (mercY(lat) - my0)]; },
    size,
  };
}

/* ---------------- 主渲染 ---------------- */
function scheduleRedraw() {
  if (redrawPending) return;
  redrawPending = true;
  requestAnimationFrame(async () => {
    redrawPending = false;
    try { await redraw(); } catch (e) { console.error(e); }
  });
}

async function redraw() {
  if (!state.index || !state.date) return;
  const fld = await currentScalarField();
  const size = map.getSize();
  if (canvas.width !== size.x || canvas.height !== size.y) {
    canvas.width = size.x; canvas.height = size.y;
  }
  ctx.clearRect(0, 0, size.x, size.y);

  drawRaster(fld, size);
  if (state.iso && state.product !== "nprsubc" && !fld.diverging) drawIsotherms(fld);
  if (state.product === "nprsubc") await drawVectors(state.date, fld.grid, productMeta());
  else if (state.overlayCurrent && state.product === "himsst") await drawCurrentOverlay();
  drawColorbar(fld);
  updateMetaPanel(fld);
}

/* 柵格填色（雙線性內插、分離座標軸投影） */
function drawRaster(fld, size) {
  const { data, offset, grid, scale, vmin, vmax, lut } = fld;
  const { nRows, nCols, lat0, dlat, lon0, dlon } = grid;
  const w = size.x, h = size.y;
  const img = ctx.createImageData(w, h);
  const px = img.data;
  const alpha = Math.round(state.opacity * 255);
  const invRange = 255 / ((vmax - vmin) / scale);   // raw 值 -> LUT 索引比例
  const vminRaw = vmin / scale;

  // 每欄經度 / 每列緯度（分離）
  const colF = new Float32Array(w);
  for (let x = 0; x < w; x++) {
    colF[x] = (map.containerPointToLatLng([x, 0]).lng - lon0) / dlon;
  }
  const rowF = new Float32Array(h);
  for (let y = 0; y < h; y++) {
    rowF[y] = (map.containerPointToLatLng([0, y]).lat - lat0) / dlat;
  }

  for (let y = 0; y < h; y++) {
    const rf = rowF[y];
    if (rf < 0 || rf > nRows - 1) continue;
    const r0 = Math.min(Math.floor(rf), nRows - 2);
    const fr = rf - r0;
    const base0 = offset + r0 * nCols;
    const base1 = base0 + nCols;
    let rowPtr = y * w * 4;
    for (let x = 0; x < w; x++) {
      const cf = colF[x];
      if (cf < 0 || cf > nCols - 1) continue;
      const c0 = Math.min(Math.floor(cf), nCols - 2);
      const fc = cf - c0;
      const v00 = data[base0 + c0], v01 = data[base0 + c0 + 1];
      const v10 = data[base1 + c0], v11 = data[base1 + c0 + 1];
      let val;
      if (v00 === MISSING || v01 === MISSING || v10 === MISSING || v11 === MISSING) {
        // 鄰近取值（海岸帶）
        val = data[offset + Math.round(rf) * nCols + Math.round(cf)];
        if (val === MISSING) continue;
      } else {
        val = v00 * (1 - fr) * (1 - fc) + v01 * (1 - fr) * fc + v10 * fr * (1 - fc) + v11 * fr * fc;
      }
      let t = (val - vminRaw) * invRange;
      t = t < 0 ? 0 : t > 255 ? 255 : t | 0;
      const p = rowPtr + x * 4, l = t * 3;
      px[p] = lut[l]; px[p + 1] = lut[l + 1]; px[p + 2] = lut[l + 2]; px[p + 3] = alpha;
    }
  }
  ctx.putImageData(img, 0, 0);
}

/* ---------------- 等溫線 (marching squares, 跳過缺值格) ---------------- */
function computeContourSegments(fld, levels) {
  const { data, offset, grid, scale } = fld;
  const { nRows, nCols, lat0, dlat, lon0, dlon } = grid;
  const out = [];
  for (const levC of levels) {
    const lev = levC / scale; // raw 單位
    const segs = [];
    for (let i = 0; i < nRows - 1; i++) {
      const b0 = offset + i * nCols, b1 = b0 + nCols;
      for (let j = 0; j < nCols - 1; j++) {
        const v00 = data[b0 + j], v01 = data[b0 + j + 1];
        const v10 = data[b1 + j], v11 = data[b1 + j + 1];
        if (v00 === MISSING || v01 === MISSING || v10 === MISSING || v11 === MISSING) continue;
        let idx = 0;
        if (v00 > lev) idx |= 1;
        if (v01 > lev) idx |= 2;
        if (v11 > lev) idx |= 4;
        if (v10 > lev) idx |= 8;
        if (idx === 0 || idx === 15) continue;
        // 邊上交點 (grid 座標: col=x, row=y)
        const top    = [j + (lev - v00) / (v01 - v00), i];
        const right  = [j + 1, i + (lev - v01) / (v11 - v01)];
        const bottom = [j + (lev - v10) / (v11 - v10), i + 1];
        const left   = [j, i + (lev - v00) / (v10 - v00)];
        const CASES = {
          1: [[left, top]], 2: [[top, right]], 3: [[left, right]], 4: [[right, bottom]],
          5: [[left, top], [right, bottom]], 6: [[top, bottom]], 7: [[left, bottom]],
          8: [[bottom, left]], 9: [[bottom, top]], 10: [[top, right], [bottom, left]],
          11: [[bottom, right]], 12: [[right, left]], 13: [[right, top]], 14: [[top, left]],
        };
        for (const [a, b] of CASES[idx]) {
          segs.push(lon0 + a[0] * dlon, lat0 + a[1] * dlat, lon0 + b[0] * dlon, lat0 + b[1] * dlat);
        }
      }
    }
    out.push({ level: levC, segs: new Float32Array(segs) });
  }
  return out;
}

function isoLevels(fld) {
  const step = state.isoInterval;
  const levels = [];
  const lo = Math.ceil(fld.vmin / step) * step;
  for (let v = lo; v <= fld.vmax + 1e-9; v += step) levels.push(+v.toFixed(2));
  return levels;
}

function drawIsotherms(fld) {
  const levels = isoLevels(fld);
  const key = [state.product, state.date, state.depthIdx, state.compare ? state.compareDate : "", levels.join(",")].join("|");
  let contours = contourCache.get(key);
  if (!contours) {
    contours = computeContourSegments(fld, levels);
    if (contourCache.size > 6) contourCache.delete(contourCache.keys().next().value);
    contourCache.set(key, contours);
  }
  const proj = makeProjector();
  const { size } = proj;
  ctx.save();
  ctx.strokeStyle = "rgba(0,0,0,0.85)";
  ctx.lineWidth = 0.9;
  const labels = [];
  for (const { level, segs } of contours) {
    ctx.beginPath();
    let accum = 0;
    for (let k = 0; k < segs.length; k += 4) {
      const [x1, y1] = proj.project(segs[k + 1], segs[k]);
      const [x2, y2] = proj.project(segs[k + 3], segs[k + 2]);
      if ((x1 < 0 && x2 < 0) || (x1 > size.x && x2 > size.x) ||
          (y1 < 0 && y2 < 0) || (y1 > size.y && y2 > size.y)) continue;
      ctx.moveTo(x1, y1); ctx.lineTo(x2, y2);
      if (state.isoLabels) {
        accum += Math.hypot(x2 - x1, y2 - y1);
        if (accum > 260) {
          accum = 0;
          labels.push([(x1 + x2) / 2, (y1 + y2) / 2, Math.atan2(y2 - y1, x2 - x1), level]);
        }
      }
    }
    ctx.stroke();
  }
  // 標籤（避免重疊：粗略網格去重）
  if (state.isoLabels) {
    ctx.font = "700 10px 'Noto Sans TC', sans-serif";
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    const taken = new Set();
    for (const [x, y, ang, level] of labels) {
      const cell = `${Math.round(x / 90)},${Math.round(y / 60)}`;
      if (taken.has(cell)) continue;
      taken.add(cell);
      let a = ang;
      if (a > Math.PI / 2) a -= Math.PI;
      if (a < -Math.PI / 2) a += Math.PI;
      ctx.save();
      ctx.translate(x, y); ctx.rotate(a);
      const txt = String(level);
      ctx.lineWidth = 3; ctx.strokeStyle = "rgba(255,255,255,0.9)";
      ctx.strokeText(txt, 0, 0);
      ctx.fillStyle = "#000";
      ctx.fillText(txt, 0, 0);
      ctx.restore();
    }
  }
  ctx.restore();
}

/* ---------------- 海流向量 ---------------- */
function nearestDate(product, target) {
  const dates = state.index.products[product]?.dates || [];
  if (!dates.length) return null;
  if (dates.includes(target)) return target;
  const older = dates.filter(d => d <= target);
  return older.length ? older[0] : dates[dates.length - 1];
}

async function drawCurrentOverlay() {
  const meta = state.index.products.nprsubc;
  if (!meta || !meta.dates.length) return;
  const d = nearestDate("nprsubc", state.date);
  $("currentHint").textContent = d === state.date ? `海流日期：${fmtDate(d)}`
      : `海流日期：${fmtDate(d)}（該日無海流資料，取最近日）`;
  const raw = await loadField("nprsubc", d);
  await drawVectors(d, meta.grid, meta, raw);
}

async function drawVectors(date, grid, meta, raw) {
  raw = raw || await loadField("nprsubc", date);
  const { nRows, nCols, lat0, dlat, lon0, dlon } = grid;
  const n = nRows * nCols;
  const proj = makeProjector();
  const { size } = proj;

  // 依縮放決定取樣間距：目標箭頭間距 ~30px
  const [xA] = proj.project(lat0, lon0);
  const [xB] = proj.project(lat0, lon0 + dlon * 10);
  const pxPerCell = Math.abs(xB - xA) / 10;
  const step = Math.max(1, Math.round(30 / Math.max(pxPerCell, 0.01)));
  const scalePx = 22 / 0.5; // 0.5 m/s → 22px
  const maxLen = 46;

  ctx.save();
  ctx.lineWidth = 1.1;
  for (let i = 0; i < nRows; i += step) {
    const lat = lat0 + i * dlat;
    for (let j = 0; j < nCols; j += step) {
      const u = raw[i * nCols + j], v = raw[n + i * nCols + j];
      if (u === MISSING || v === MISSING) continue;
      const um = u * meta.scale, vm = v * meta.scale;
      const spd = Math.hypot(um, vm);
      if (spd < 0.02) continue;
      const lon = lon0 + j * dlon;
      const [x, y] = proj.project(lat, lon);
      if (x < -20 || x > size.x + 20 || y < -20 || y > size.y + 20) continue;
      let len = spd * scalePx;
      if (len > maxLen) len = maxLen;
      if (len < 4) len = 4;
      const dx = (um / spd) * len, dy = (-vm / spd) * len; // 螢幕 y 向下
      const x2 = x + dx, y2 = y + dy;
      // 顏色依流速
      const t = Math.min(spd / 1.6, 1);
      const color = state.product === "nprsubc"
        ? "rgba(10,10,10,0.85)"
        : `rgba(${Math.round(40 + 215 * t)},${Math.round(30 * (1 - t))},${Math.round(90 * (1 - t) + 20)},0.9)`;
      ctx.strokeStyle = color; ctx.fillStyle = color;
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x2, y2); ctx.stroke();
      // 箭頭頭部
      const ah = Math.min(5, len * 0.45), ang = Math.atan2(dy, dx);
      ctx.beginPath();
      ctx.moveTo(x2, y2);
      ctx.lineTo(x2 - ah * Math.cos(ang - 0.45), y2 - ah * Math.sin(ang - 0.45));
      ctx.lineTo(x2 - ah * Math.cos(ang + 0.45), y2 - ah * Math.sin(ang + 0.45));
      ctx.closePath(); ctx.fill();
    }
  }
  ctx.restore();
}

/* ---------------- 色階條 ---------------- */
function drawColorbar(fld) {
  const cb = $("colorbar");
  const c = cb.getContext("2d");
  const w = cb.width, h = cb.height;
  const img = c.createImageData(w, h);
  for (let x = 0; x < w; x++) {
    const l = Math.round((x / (w - 1)) * 255) * 3;
    for (let y = 0; y < h; y++) {
      const p = (y * w + x) * 4;
      img.data[p] = fld.lut[l]; img.data[p + 1] = fld.lut[l + 1]; img.data[p + 2] = fld.lut[l + 2]; img.data[p + 3] = 255;
    }
  }
  c.putImageData(img, 0, 0);
  const ticks = $("colorbarTicks");
  ticks.innerHTML = "";
  const n = 5;
  for (let i = 0; i <= n; i++) {
    const v = fld.vmin + ((fld.vmax - fld.vmin) * i) / n;
    const s = document.createElement("span");
    s.textContent = (fld.diverging && v > 0 ? "+" : "") + (+v.toFixed(1));
    ticks.appendChild(s);
  }
  const meta = productMeta();
  let title;
  if (fld.diverging) title = `溫差 (${fmtDate(state.date)} − ${fmtDate(state.compareDate)}) °C`;
  else if (state.product === "nprsubc") title = "表層流速 (m/s)";
  else if (state.product === "nprsubt") title = `${meta.depths[state.depthIdx]}m 水溫 (°C)`;
  else title = "海表水溫 (°C)";
  $("colorbarTitle").textContent = title;
}

/* ---------------- 資訊面板 ---------------- */
function updateMetaPanel() {
  const meta = productMeta();
  const g = meta.grid;
  $("dataMeta").innerHTML =
    `<b>${meta.longName}</b><br>` +
    `網格：${g.nRows} × ${g.nCols}（${Math.abs(g.dlat).toFixed(2)}° × ${g.dlon.toFixed(3)}°）<br>` +
    `範圍：${Math.min(g.lat0, g.lat0 + g.dlat * (g.nRows - 1)).toFixed(1)}–${Math.max(g.lat0, g.lat0 + g.dlat * (g.nRows - 1)).toFixed(1)}°N, ` +
    `${g.lon0.toFixed(1)}–${(g.lon0 + g.dlon * (g.nCols - 1)).toFixed(1)}°E<br>` +
    `可用日期：${meta.dates.length} 筆<br>` +
    `更新時間：${new Date(state.index.generated).toLocaleString("zh-TW")}`;
}

/* ---------------- 滑鼠讀值 ---------------- */
async function onHover(e) {
  if (!state.index || !state.date) return;
  const { lat, lng } = e.latlng;
  const meta = productMeta();
  const g = meta.grid;
  const rf = (lat - g.lat0) / g.dlat, cf = (lng - g.lon0) / g.dlon;
  const title = `${lat.toFixed(2)}°N, ${lng.toFixed(2)}°E`;
  const bodyEl = $("readoutBody");
  $("readoutTitle").textContent = title;
  if (rf < 0 || rf > g.nRows - 1 || cf < 0 || cf > g.nCols - 1) { bodyEl.textContent = "（超出資料範圍）"; return; }
  const i = Math.round(rf), j = Math.round(cf);
  try {
    const raw = await loadField(state.product, state.date);
    if (state.product === "nprsubc") {
      const n = g.nRows * g.nCols;
      const u = raw[i * g.nCols + j], v = raw[n + i * g.nCols + j];
      if (u === MISSING || v === MISSING) { bodyEl.textContent = "陸地／無資料"; return; }
      const um = u * meta.scale, vm = v * meta.scale;
      const spd = Math.hypot(um, vm);
      const dir = (Math.atan2(um, vm) * 180 / Math.PI + 360) % 360;
      bodyEl.innerHTML = `<span class="big">${spd.toFixed(2)}</span> m/s（${(spd * 1.9438).toFixed(1)} 節）<br>流向 ${dir.toFixed(0)}°｜u ${um.toFixed(2)}, v ${vm.toFixed(2)} m/s`;
    } else {
      const off = blockOffset(meta);
      const val = raw[off + i * g.nCols + j];
      if (val === MISSING) { bodyEl.textContent = "陸地／海冰／無資料"; return; }
      let html = `<span class="big">${(val * meta.scale).toFixed(state.product === "himsst" ? 1 : 2)}</span> °C`;
      if (state.compare && state.compareDate && state.compareDate !== state.date) {
        const rawB = await loadField(state.product, state.compareDate);
        const vb = rawB[off + i * g.nCols + j];
        if (vb !== MISSING) {
          const d = (val - vb) * meta.scale;
          html += `<br>較基準日 ${d >= 0 ? "+" : ""}${d.toFixed(2)} °C`;
        }
      }
      if (state.product === "nprsubt") html += `<br>深度 ${meta.depths[state.depthIdx]} m`;
      bodyEl.innerHTML = html;
    }
  } catch { /* 資料尚未載入 */ }
}

/* ---------------- UI 綁定 ---------------- */
function populateDates() {
  const meta = productMeta();
  const sel = $("dateSelect");
  sel.innerHTML = "";
  for (const d of meta.dates) {
    const o = document.createElement("option");
    o.value = d; o.textContent = fmtDate(d);
    sel.appendChild(o);
  }
  if (!meta.dates.includes(state.date)) state.date = meta.dates[0] || null;
  sel.value = state.date || "";

  const selB = $("compareDate");
  selB.innerHTML = "";
  for (const d of meta.dates) {
    const o = document.createElement("option");
    o.value = d; o.textContent = fmtDate(d);
    selB.appendChild(o);
  }
  // 預設基準日：往前 7 筆或最舊
  if (!meta.dates.includes(state.compareDate)) {
    state.compareDate = meta.dates[Math.min(7, meta.dates.length - 1)] || null;
  }
  selB.value = state.compareDate || "";
}

function applyProductUI() {
  const isSubT = state.product === "nprsubt";
  const isCur = state.product === "nprsubc";
  $("depthRow").classList.toggle("hidden", !isSubT);
  $("isoPanel").classList.toggle("hidden", isCur);
  $("currentPanel").classList.toggle("hidden", state.product !== "himsst");
  document.querySelectorAll(".ptab").forEach(b =>
    b.classList.toggle("active", b.dataset.product === state.product));
  const desc = {
    himsst: "高解析度合成海表水溫 (HIMSST)，衛星紅外／微波與現場觀測合成，0.1°×0.1° 每日分析。",
    nprsubt: "NPR-4DVAR 海洋資料同化系統之水下水溫分析（50 / 100 / 200 / 400 m）。",
    nprsubc: "NPR-4DVAR 表層海流分析，箭頭示流向、色階示流速。",
  };
  $("productDesc").textContent = desc[state.product];
  // 預設色階範圍
  if (isCur) { $("vminInput").value = 0; $("vmaxInput").value = 2; state.vmin = 0; state.vmax = 2; }
  else if (state.vmax === 2) { $("vminInput").value = 0; $("vmaxInput").value = 32; state.vmin = 0; state.vmax = 32; }
  // 深度 chips
  if (isSubT) {
    const chips = $("depthChips");
    chips.innerHTML = "";
    productMeta().depths.forEach((d, idx) => {
      const b = document.createElement("button");
      b.className = "chip" + (idx === state.depthIdx ? " active" : "");
      b.textContent = d + "m";
      b.onclick = () => { state.depthIdx = idx; applyProductUI(); update(); };
      chips.appendChild(b);
    });
  }
}

async function update() {
  showLoading(true, "資料載入中…");
  try {
    await redraw();
    setStatus(`${productMeta().name}｜${fmtDate(state.date)}`, "ok");
  } catch (e) {
    console.error(e);
    setStatus("資料載入失敗", "err");
  } finally {
    showLoading(false);
  }
}

function bindUI() {
  document.querySelectorAll(".ptab").forEach(btn => {
    btn.onclick = () => {
      state.product = btn.dataset.product;
      populateDates();
      applyProductUI();
      update();
    };
  });
  $("dateSelect").onchange = e => { state.date = e.target.value; update(); };
  $("isoToggle").onchange = e => { state.iso = e.target.checked; scheduleRedraw(); };
  $("isoInterval").onchange = e => { state.isoInterval = +e.target.value; scheduleRedraw(); };
  $("isoLabels").onchange = e => { state.isoLabels = e.target.checked; scheduleRedraw(); };
  $("currentToggle").onchange = e => { state.overlayCurrent = e.target.checked; scheduleRedraw(); };
  $("compareToggle").onchange = e => { state.compare = e.target.checked; update(); };
  $("compareDate").onchange = e => { state.compareDate = e.target.value; if (state.compare) update(); };
  $("compareRange").onchange = e => { state.compareRange = +e.target.value; if (state.compare) update(); };
  $("cmapSelect").onchange = e => { state.cmap = e.target.value; scheduleRedraw(); };
  $("vminInput").onchange = e => { state.vmin = +e.target.value; scheduleRedraw(); };
  $("vmaxInput").onchange = e => { state.vmax = +e.target.value; scheduleRedraw(); };
  $("opacitySlider").oninput = e => { state.opacity = +e.target.value / 100; scheduleRedraw(); };
  $("sidebarToggle").onclick = () => {
    const sb = $("sidebar");
    sb.classList.toggle("collapsed");
    $("sidebarToggle").textContent = sb.classList.contains("collapsed") ? "▶" : "◀";
    setTimeout(() => map.invalidateSize(), 300);
  };
}

/* ---------------- 初始化 ---------------- */
async function init() {
  canvas = $("fieldCanvas");
  ctx = canvas.getContext("2d");

  map = L.map("map", { center: [30, 135], zoom: 5, zoomControl: true, worldCopyJump: false });
  const dark = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
    subdomains: "abcd", maxZoom: 12,
  }).addTo(map);
  const voyager = L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; OSM &copy; CARTO', subdomains: "abcd", maxZoom: 12,
  });
  const labels = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png", {
    subdomains: "abcd", maxZoom: 12, pane: "shadowPane",
  }).addTo(map);
  L.control.layers({ "深色底圖": dark, "淺色底圖": voyager }, { "地名標籤": labels },
    { position: "topleft", collapsed: true }).addTo(map);
  L.control.scale({ imperial: false, position: "bottomleft" }).addTo(map);

  map.fitBounds([[17, 114], [45, 155]]);
  map.on("move zoom viewreset resize", scheduleRedraw);
  map.on("zoomstart", () => ctx.clearRect(0, 0, canvas.width, canvas.height));
  map.on("mousemove", onHover);

  bindUI();

  try {
    state.index = await loadIndex();
  } catch (e) {
    setStatus("無資料", "err");
    showError("找不到 <b>data/index.json</b>。請先執行資料管線：<code>python scripts/fetch_data.py --out site/data</code>，或等待 GitHub Actions 首次自動更新完成。");
    return;
  }
  const available = Object.entries(state.index.products).filter(([, m]) => m.dates.length);
  if (!available.length) {
    setStatus("無資料", "err");
    showError("資料目錄為空，請確認資料管線執行結果。");
    return;
  }
  if (!state.index.products.himsst?.dates.length) state.product = available[0][0];

  populateDates();
  applyProductUI();
  await update();
}

document.addEventListener("DOMContentLoaded", init);
