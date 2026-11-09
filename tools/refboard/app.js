'use strict';

// ---------- constants ----------
const VERSION = '0.0.1';
const W = 1980, H = 1020, M = 60;
// Sheet colours: bg and ink come from the project, the rest are mixed from them in updateTheme().
const COL = { bg: '#f1efea', ink: '#1e1e1e', grey: '#8a8780', light: '#cdc9c1', paper: '#e4e1da', veil: 'rgba(241,239,234,0.18)' };
const SANS = 'Bahnschrift, "DIN Alternate", "Arial Narrow", Arial, sans-serif';
const TEXT = '"Segoe UI", Roboto, Arial, sans-serif';
const MONO = 'Consolas, "JetBrains Mono", Menlo, monospace';
const F = {
  title: `64px ${SANS}`, h: `22px ${SANS}`, code: `26px ${SANS}`,
  txt: `16px ${TEXT}`, mono: `15px ${MONO}`, monoS: `13px ${MONO}`,
};
const MAX_IMAGE = 1600;     // imported photos are downscaled to this size
const SIZE_PRESETS = [[3, 3], [3, 4]];

const sheet = document.getElementById('sheet');
const ctx = sheet.getContext('2d');

// ---------- state ----------
const today = new Date().toISOString().slice(0, 10);

function defaultState() {
  return {
    title: 'SEIMY18',
    subtitle: 'Facade module kit',
    note: 'Reference board for game asset production',
    author: '',
    date: today,
    accent: '#b4553a',
    bg: '#f1efea',
    ink: '#1e1e1e',
    sheetLang: 'en',
    grid: 3,
    groundH: 4,
    upperH: 3,
    upperFloors: 1,
    bays: 7,
    roof: true,
    overview: null,        // { src, crop }
    modules: [],           // { id, code, name, sub, w, h, src, crop }
    layout: {},            // "floor_bay" -> module id, floor 0 = ground
    filler: '',            // module id used for empty cells and gaps
    palette: [],           // { hex, label }
  };
}

let state = defaultState();
let brush = '';            // module id painted on the facade grid
let nextId = 1;

const S = (key, ...args) => lookup(SHEET_TEXT, state.sheetLang, key, args);
const byId = id => state.modules.find(m => m.id === id);
const floors = () => [state.groundH, ...Array(state.upperFloors).fill(state.upperH)];
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const fmt = v => (Math.round(v * 10) / 10).toFixed(1);

const rgb = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) || 0);
const toHex = c => '#' + c.map(v => Math.round(v).toString(16).padStart(2, '0')).join('');
const mix = (a, b, t) => toHex(rgb(a).map((v, i) => v + (rgb(b)[i] - v) * t));

function updateTheme() {
  COL.bg = state.bg || '#f1efea';
  COL.ink = state.ink || '#1e1e1e';
  COL.grey = mix(COL.ink, COL.bg, 0.45);
  COL.light = mix(COL.ink, COL.bg, 0.75);
  COL.paper = mix(COL.bg, COL.ink, 0.06);
  COL.veil = `rgba(${rgb(COL.bg).join(',')},0.18)`;
}

// ---------- images ----------
const images = new Map();

function getImage(src) {
  if (!src) return null;
  let im = images.get(src);
  if (!im) {
    im = new Image();
    im.onload = () => { scheduleRender(); refreshCropEditors(); };
    im.src = src;
    images.set(src, im);
  }
  return im.complete && im.naturalWidth ? im : null;
}

function readImageFile(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const im = new Image();
    im.onload = () => {
      const k = Math.min(1, MAX_IMAGE / Math.max(im.naturalWidth, im.naturalHeight));
      const cv = document.createElement('canvas');
      cv.width = Math.round(im.naturalWidth * k);
      cv.height = Math.round(im.naturalHeight * k);
      cv.getContext('2d').drawImage(im, 0, 0, cv.width, cv.height);
      URL.revokeObjectURL(url);
      resolve(cv.toDataURL('image/jpeg', 0.9));
    };
    im.onerror = () => { URL.revokeObjectURL(url); reject(new Error(file.name)); };
    im.src = url;
  });
}

const newCrop = () => ({ cx: 0.5, cy: 0.5, zoom: 1 });

// Source rect of `img` that covers a w×h box, shifted and zoomed by `crop`.
function coverRect(img, w, h, crop) {
  const iw = img.naturalWidth, ih = img.naturalHeight;
  const s = Math.max(w / iw, h / ih) * crop.zoom;
  const sw = w / s, sh = h / s;
  return { s, sw, sh, sx: clamp(crop.cx * iw - sw / 2, 0, iw - sw), sy: clamp(crop.cy * ih - sh / 2, 0, ih - sh) };
}

function drawCover(c, img, x, y, w, h, crop = newCrop()) {
  const r = coverRect(img, w, h, crop);
  c.drawImage(img, r.sx, r.sy, r.sw, r.sh, x, y, w, h);
}

// ---------- sheet drawing helpers ----------
function text(s, x, y, font, color = COL.ink, align = 'left', base = 'alphabetic') {
  ctx.font = font; ctx.fillStyle = color; ctx.textAlign = align; ctx.textBaseline = base;
  ctx.fillText(s, x, y);
}

function textWidth(s, font) { ctx.font = font; return ctx.measureText(s).width; }

function fitText(s, font, maxW) {
  if (textWidth(s, font) <= maxW) return s;
  while (s.length > 1 && textWidth(s + '…', font) > maxW) s = s.slice(0, -1);
  return s + '…';
}

function line(x0, y0, x1, y1, color = COL.ink, w = 1) {
  ctx.strokeStyle = color; ctx.lineWidth = w;
  ctx.beginPath(); ctx.moveTo(x0 + 0.5, y0 + 0.5); ctx.lineTo(x1 + 0.5, y1 + 0.5); ctx.stroke();
}

function tick(x, y) { line(x - 5, y + 5, x + 5, y - 5, COL.ink, 2); }

function dimH(x0, x1, y, label, extFrom) {
  if (extFrom != null) { line(x0, extFrom, x0, y + 6, COL.grey); line(x1, extFrom, x1, y + 6, COL.grey); }
  line(x0, y, x1, y); tick(x0, y); tick(x1, y);
  const tw = textWidth(label, F.mono) + 10, mx = (x0 + x1) / 2;
  if (tw < x1 - x0 - 8) {
    ctx.fillStyle = COL.bg; ctx.fillRect(mx - tw / 2, y - 9, tw, 18);
    text(label, mx, y + 1, F.mono, COL.ink, 'center', 'middle');
  }
}

function dimV(x, y0, y1, label, extFrom) {
  if (extFrom != null) { line(extFrom, y0, x + 6, y0, COL.grey); line(extFrom, y1, x + 6, y1, COL.grey); }
  line(x, y0, x, y1); tick(x, y0); tick(x, y1);
  const tw = textWidth(label, F.mono) + 10, my = (y0 + y1) / 2;
  if (tw < Math.abs(y1 - y0) - 8) {
    ctx.save(); ctx.translate(x, my); ctx.rotate(-Math.PI / 2);
    ctx.fillStyle = COL.bg; ctx.fillRect(-tw / 2, -9, tw, 18);
    text(label, 0, 1, F.mono, COL.ink, 'center', 'middle');
    ctx.restore();
  }
}

function section(x, y, num, title) {
  text(num, x, y, F.h, state.accent);
  text(title.toUpperCase(), x + textWidth(num, F.h) + 12, y, F.h);
}

function placeholder(x, y, w, h, label) {
  ctx.fillStyle = COL.paper; ctx.fillRect(x, y, w, h);
  ctx.strokeStyle = COL.light; ctx.lineWidth = 1; ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
  text(label, x + w / 2, y + h / 2, F.monoS, COL.grey, 'center', 'middle');
}

// ---------- sheet sections ----------
function drawHeader() {
  text(state.title || 'UNTITLED', M, 92, F.title);
  const tx = M + textWidth(state.title || 'UNTITLED', F.title) + 28;
  text((state.subtitle || '').toUpperCase(), tx, 64, F.h);
  text(state.note || '', tx, 90, F.txt, COL.grey);

  const meta = [
    [S('grid'), S('gridValue', fmt(state.grid))],
    [S('floors'), S('floorsValue', fmt(state.groundH), fmt(state.upperH), state.upperFloors)],
  ];
  if (state.author) meta.push([S('author'), state.author]);
  meta.push([S('date'), state.date || '']);

  let x = W - M;
  for (const [k, v] of meta.reverse()) {
    text(v, x, 92, F.mono, COL.ink, 'right');
    text(k, x, 68, F.monoS, COL.grey, 'right');
    x -= Math.max(textWidth(v, F.mono), textWidth(k, F.monoS)) + 44;
  }
  line(M, 116, W - M, 116, COL.ink, 2);
}

// Returns the width used by the photo.
function drawOverview(top, boxH) {
  section(M, top - 18, '01', S('general'));
  const ov = state.overview, img = ov && getImage(ov.src);
  const w = overviewWidth(boxH);
  if (img) {
    drawCover(ctx, img, M, top, w, boxH, ov.crop);
    ctx.strokeStyle = COL.ink; ctx.lineWidth = 1; ctx.strokeRect(M - 0.5, top - 0.5, w + 1, boxH + 1);
  } else {
    placeholder(M, top, w, boxH, S('noOverview'));
  }
  text(S('photoRef'), M, top + boxH + 22, F.txt, COL.grey);
  return w;
}

function overviewWidth(boxH) {
  const img = state.overview && getImage(state.overview.src);
  const aspect = img ? img.naturalWidth / img.naturalHeight : 4 / 3;
  return Math.round(clamp(aspect * boxH, 320, 620));
}

function drawCell(x, y, w, h, mod) {
  const img = mod && getImage(mod.src);
  if (img) drawCover(ctx, img, x, y, w, h, mod.crop);
  else { ctx.fillStyle = COL.paper; ctx.fillRect(x, y, w, h); }
}

function drawLayout(x0, x1, top) {
  section(x0, top - 18, '02', S('layout'));
  const fl = floors(), g = state.grid, n = state.bays;
  const roofM = state.roof ? 1.6 : 0;
  const totalM = fl.reduce((a, b) => a + b, 0) + roofM;
  const labelW = 70, dimW = 60;
  const u = Math.min((x1 - x0 - labelW - dimW) / (n * g), 300 / totalM);
  const mw = g * u, gx0 = x0 + labelW, gx1 = gx0 + n * mw;
  const gyBot = Math.round(top + 20 + totalM * u);

  const levels = [gyBot];
  fl.forEach((h, i) => levels.push(levels[i] - h * u));
  const gyTop = levels[levels.length - 1];
  const filler = byId(state.filler);

  for (let f = 0; f < fl.length; f++) {
    const cellTop = levels[f + 1], cellH = levels[f] - levels[f + 1];
    for (let b = 0; b < n; b++) {
      const x = gx0 + b * mw;
      const mod = byId(state.layout[`${f}_${b}`]);
      if (!mod) { drawCell(x, cellTop, mw, cellH, filler); continue; }
      // A module lower than the floor sits at the top; the filler fills the rest.
      const mh = Math.min(cellH, mod.h * u);
      if (mh < cellH) drawCell(x, cellTop + mh, mw, cellH - mh, filler);
      drawCell(x, cellTop, mw, mh, mod);
    }
  }

  // lift the photos a little so the line work reads on top
  ctx.fillStyle = COL.veil;
  ctx.fillRect(gx0, gyTop, gx1 - gx0, gyBot - gyTop);

  for (let b = 0; b <= n; b++) line(gx0 + b * mw, gyTop, gx0 + b * mw, gyBot);
  levels.forEach(y => line(gx0, y, gx1, y));
  line(gx0 - 20, gyBot, gx1 + 20, gyBot, COL.ink, 3);

  for (let f = 0; f < fl.length; f++) {
    for (let b = 0; b < n; b++) {
      const mod = byId(state.layout[`${f}_${b}`]) || filler;
      if (!mod || mw < 44) continue;
      const code = mod.code || '?';
      const x = gx0 + b * mw + 6, y = levels[f + 1] + 5;
      const tw = textWidth(code, F.monoS);
      ctx.fillStyle = mod === filler && !state.layout[`${f}_${b}`] ? COL.ink : state.accent;
      ctx.fillRect(x - 2, y, tw + 6, 17);
      text(code, x + 1, y + 9, F.monoS, COL.bg, 'left', 'middle');
    }
  }

  if (state.roof) {
    const rh = roofM * u;
    ctx.strokeStyle = COL.ink; ctx.lineWidth = 1; ctx.beginPath();
    ctx.moveTo(gx0 - 14, gyTop); ctx.lineTo(gx0 + 30, gyTop - rh); ctx.lineTo(gx1 - 30, gyTop - rh); ctx.lineTo(gx1 + 14, gyTop);
    ctx.stroke();
    for (let k = 1; k < 6; k++) {
      const yy = gyTop - rh * k / 6, d = 44 * k / 6;
      line(gx0 - 14 + d, yy, gx1 + 14 - d, yy, COL.light);
    }
    text(S('roof'), (gx0 + gx1) / 2, gyTop - rh / 2, F.monoS, COL.grey, 'center', 'middle');
  }

  for (let b = 0; b < n; b++) dimH(gx0 + b * mw, gx0 + (b + 1) * mw, gyBot + 12, fmt(g));
  dimH(gx0, gx1, gyBot + 34, `${fmt(n * g)} ${S('m')}`, gyBot + 4);
  let acc = 0;
  levels.forEach((y, i) => {
    text(`${i ? '+' : '±'}${acc.toFixed(2)}`, gx0 - 26, y, F.monoS, COL.grey, 'right', 'middle');
    ctx.fillStyle = COL.grey; ctx.beginPath();
    ctx.moveTo(gx0 - 20, y - 5); ctx.lineTo(gx0 - 14, y); ctx.lineTo(gx0 - 20, y + 5); ctx.fill();
    if (i < fl.length) {
      dimV(gx1 + 34, levels[i + 1], y, `${fmt(fl[i])} ${S('m')}`, gx1 + 4);
      acc += fl[i];
    }
  });
}

function drawPalette(x0, top) {
  section(x0, top - 18, '04', S('materials'));
  const sw = 46;
  let y = top;
  for (const p of state.palette.slice(0, 6)) {
    const img = p.src && getImage(p.src);
    if (img) drawCover(ctx, img, x0, y, sw, sw, p.crop);
    else { ctx.fillStyle = p.hex; ctx.fillRect(x0, y, sw, sw); }
    ctx.strokeStyle = COL.ink; ctx.lineWidth = 1; ctx.strokeRect(x0 + 0.5, y + 0.5, sw - 1, sw - 1);
    text(fitText(p.label || '', F.txt, 230), x0 + sw + 16, y + 18, F.txt);
    text((p.src ? `${S('texture')} · ` : '') + p.hex.toUpperCase(), x0 + sw + 16, y + 38, F.monoS, COL.grey);
    y += sw + 12;
  }
}

function drawModules() {
  const MY = 590;
  line(M, MY - 46, W - M, MY - 46, COL.light);
  section(M, MY, '03', S('modules'));
  const mods = state.modules;
  const sizes = [...new Set(mods.map(m => `${fmt(m.w)} × ${fmt(m.h)} ${S('m')}`))].join(' · ');
  if (mods.length) text(S('modulesCount', mods.length, sizes), W - M, MY, F.txt, COL.grey, 'right');
  if (!mods.length) { placeholder(M, MY + 30, W - 2 * M, 330, S('noModules')); return; }

  const base = H - 62, dim = 40, minGap = 30;
  const maxH = Math.max(...mods.map(m => m.h));
  const sumW = mods.reduce((a, m) => a + m.w, 0);
  const avail = W - 2 * M - mods.length * dim - (mods.length - 1) * minGap;
  const um = Math.min(288 / maxH, avail / sumW);
  const used = mods.reduce((a, m) => a + m.w * um + dim, 0);
  const gap = mods.length > 1 ? (W - 2 * M - used) / (mods.length - 1) : 0;

  let x = M;
  for (const m of mods) {
    const w = Math.round(m.w * um), h = Math.round(m.h * um), y0 = base - h;
    const img = getImage(m.src);
    if (img) drawCover(ctx, img, x, y0, w, h, m.crop); else placeholder(x, y0, w, h, S('noPhoto'));
    ctx.strokeStyle = COL.ink; ctx.lineWidth = 1; ctx.strokeRect(x - 0.5, y0 - 0.5, w + 1, h + 1);

    const ty = MY + 36, room = w + dim + gap - 16;
    text(m.code || '', x, ty, F.code, state.accent);
    const cw = textWidth(m.code || '', F.code) + 12;
    text(fitText(m.name || '', F.h, room - cw), x + cw, ty, F.h);
    text(fitText(m.sub || '', F.txt, room), x, ty + 22, F.txt, COL.grey);

    dimH(x, x + w, base + 26, `${fmt(m.w)} ${S('m')}`, base + 4);
    dimV(x + w + 26, y0, base, `${fmt(m.h)} ${S('m')}`, x + w + 4);
    x += w + dim + gap;
  }
}

function render() {
  updateTheme();
  ctx.fillStyle = COL.bg; ctx.fillRect(0, 0, W, H);
  drawHeader();
  const TOP = 172, BOX_H = 340;
  const photoW = drawOverview(TOP, BOX_H);
  const hasPalette = state.palette.length > 0;
  const px0 = W - M - 290;
  if (hasPalette) drawPalette(px0, TOP);
  drawLayout(M + photoW + 90, hasPalette ? px0 - 70 : W - M, TOP);
  drawModules();
}

let pending = false;
function scheduleRender() {
  if (pending) return;
  pending = true;
  requestAnimationFrame(() => { pending = false; render(); });
}

// ---------- palette extraction (k-means on downscaled module photos) ----------
function extractPalette(k = 6) {
  const cv = document.createElement('canvas'); cv.width = cv.height = 48;
  const c = cv.getContext('2d', { willReadFrequently: true });
  const px = [];
  const sources = state.modules.length ? state.modules : state.overview ? [state.overview] : [];
  for (const m of sources) {
    const img = getImage(m.src);
    if (!img) continue;
    c.clearRect(0, 0, 48, 48); c.drawImage(img, 0, 0, 48, 48);
    const d = c.getImageData(0, 0, 48, 48).data;
    for (let i = 0; i < d.length; i += 4) px.push([d[i], d[i + 1], d[i + 2]]);
  }
  if (!px.length) return [];

  const lum = p => 0.3 * p[0] + 0.59 * p[1] + 0.11 * p[2];
  px.sort((a, b) => lum(a) - lum(b));
  let centers = Array.from({ length: k }, (_, i) => px[Math.floor((i + 0.5) * px.length / k)].slice());
  let counts = [];
  for (let it = 0; it < 12; it++) {
    const sum = centers.map(() => [0, 0, 0]);
    counts = centers.map(() => 0);
    for (const p of px) {
      let best = 0, bd = Infinity;
      centers.forEach((cc, j) => {
        const d = (p[0] - cc[0]) ** 2 + (p[1] - cc[1]) ** 2 + (p[2] - cc[2]) ** 2;
        if (d < bd) { bd = d; best = j; }
      });
      sum[best][0] += p[0]; sum[best][1] += p[1]; sum[best][2] += p[2]; counts[best]++;
    }
    centers = centers.map((cc, j) => counts[j] ? sum[j].map(v => v / counts[j]) : cc);
  }
  const hex = c3 => '#' + c3.map(v => Math.round(v).toString(16).padStart(2, '0')).join('');
  return centers.map((cc, j) => ({ hex: hex(cc), n: counts[j] }))
    .filter(x => x.n > 0).sort((a, b) => b.n - a.n).map(x => x.hex);
}

// ---------- crop editor ----------
const cropEditors = new Set();

function cropEditor(target, aspect) {
  const cv = document.createElement('canvas');
  cv.className = 'crop';
  cv.width = 300; cv.height = Math.round(300 / aspect);
  const c = cv.getContext('2d');

  const draw = () => {
    const img = getImage(target.src);
    c.fillStyle = '#ddd'; c.fillRect(0, 0, cv.width, cv.height);
    if (img) drawCover(c, img, 0, 0, cv.width, cv.height, target.crop);
  };
  const clampCrop = img => {
    const r = coverRect(img, cv.width, cv.height, target.crop);
    target.crop.cx = clamp(target.crop.cx, r.sw / 2 / img.naturalWidth, 1 - r.sw / 2 / img.naturalWidth);
    target.crop.cy = clamp(target.crop.cy, r.sh / 2 / img.naturalHeight, 1 - r.sh / 2 / img.naturalHeight);
  };

  let drag = null;
  cv.addEventListener('pointerdown', e => { drag = { x: e.clientX, y: e.clientY }; cv.setPointerCapture(e.pointerId); });
  cv.addEventListener('pointerup', () => { drag = null; });
  cv.addEventListener('pointermove', e => {
    const img = getImage(target.src);
    if (!drag || !img) return;
    const k = cv.width / cv.getBoundingClientRect().width;      // css px -> canvas px
    const r = coverRect(img, cv.width, cv.height, target.crop);
    target.crop.cx -= (e.clientX - drag.x) * k / r.s / img.naturalWidth;
    target.crop.cy -= (e.clientY - drag.y) * k / r.s / img.naturalHeight;
    drag = { x: e.clientX, y: e.clientY };
    clampCrop(img); draw(); scheduleRender();
  });
  cv.addEventListener('wheel', e => {
    const img = getImage(target.src);
    if (!img) return;
    e.preventDefault();
    target.crop.zoom = clamp(target.crop.zoom * (e.deltaY < 0 ? 1.08 : 1 / 1.08), 1, 6);
    clampCrop(img); draw(); scheduleRender();
  }, { passive: false });
  cv.addEventListener('dblclick', () => { target.crop = newCrop(); draw(); scheduleRender(); });

  cv.redraw = draw;
  cropEditors.add(cv);
  draw();
  return cv;
}

function refreshCropEditors() {
  for (const cv of cropEditors) cv.isConnected ? cv.redraw() : cropEditors.delete(cv);
}

// ---------- UI: small builders ----------
function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (k === 'class') e.className = v;
    else e.setAttribute(k, v);
  }
  for (const ch of children) e.append(ch);
  return e;
}

// A labelled input bound to obj[key].
function field(label, obj, key, type = 'text', opts = {}) {
  const input = el('input', { type, ...(opts.attrs || {}) });
  input.value = obj[key] ?? '';
  input.addEventListener('input', () => {
    obj[key] = type === 'number' ? (parseFloat(input.value) || 0) : input.value;
    if (opts.onChange) opts.onChange(); else scheduleRender();
  });
  return el('label', { class: opts.wide ? 'wide' : '' }, label, input);
}

function checkbox(label, obj, key, onChange) {
  const input = el('input', { type: 'checkbox' });
  input.checked = !!obj[key];
  input.addEventListener('change', () => { obj[key] = input.checked; onChange ? onChange() : scheduleRender(); });
  return el('label', { class: 'check' }, input, label);
}

// ---------- UI: panels ----------
function buildProject() {
  const box = document.getElementById('projectFields');
  box.replaceChildren(
    field(t('title'), state, 'title', 'text', { wide: true }),
    field(t('subtitle'), state, 'subtitle', 'text', { wide: true }),
    field(t('note'), state, 'note', 'text', { wide: true }),
    field(t('author'), state, 'author'),
    field(t('date'), state, 'date', 'date'),
    field(t('accent'), state, 'accent', 'color', { onChange: () => { applyAccent(); scheduleRender(); } }),
    field(t('bg'), state, 'bg', 'color'),
    field(t('ink'), state, 'ink', 'color'),
    el('label', {}, t('defaults'), el('button', {
      class: 'btn small',
      onclick: () => { const d = defaultState(); state.bg = d.bg; state.ink = d.ink; state.accent = d.accent; buildProject(); applyAccent(); scheduleRender(); },
    }, t('reset'))),
    langSelect(),
  );
}

function langSelect() {
  const sel = el('select');
  [['en', 'English'], ['ru', 'Русский']].forEach(([v, n]) => sel.append(el('option', { value: v }, n)));
  sel.value = state.sheetLang;
  sel.addEventListener('change', () => { state.sheetLang = sel.value; scheduleRender(); });
  return el('label', {}, t('sheetLang'), sel);
}

function buildGrid() {
  const num = (label, key, min, max, step, rebuild) => field(label, state, key, 'number', {
    attrs: { min, max, step },
    onChange: () => { if (rebuild) buildLayout(); scheduleRender(); },
  });
  document.getElementById('gridFields').replaceChildren(
    num(t('grid'), 'grid', 1, 10, 0.5),
    num(t('bays'), 'bays', 1, 16, 1, true),
    num(t('groundH'), 'groundH', 2, 8, 0.5),
    num(t('upperH'), 'upperH', 2, 8, 0.5),
    num(t('upperFloors'), 'upperFloors', 0, 6, 1, true),
    checkbox(t('roof'), state, 'roof'),
  );
}

function buildOverview() {
  const box = document.getElementById('overviewPanel');
  const input = el('input', { type: 'file', accept: 'image/*', hidden: '' });
  input.addEventListener('change', async () => {
    if (!input.files[0]) return;
    state.overview = { src: await readImageFile(input.files[0]), crop: newCrop() };
    buildOverview(); scheduleRender();
  });
  const drop = el('label', { class: 'drop' }, state.overview ? t('ovReplace') : t('ovDrop'), input);
  makeDropZone(drop, async files => {
    state.overview = { src: await readImageFile(files[0]), crop: newCrop() };
    buildOverview(); scheduleRender();
  });
  const children = [drop];
  if (state.overview) {
    const img = getImage(state.overview.src);
    const aspect = img ? overviewWidth(340) / 340 : 4 / 3;
    children.push(el('div', { class: 'card' },
      cropEditor(state.overview, aspect),
      el('div', {}, el('p', { class: 'hint' }, t('ovHint')),
        el('button', { class: 'btn small', onclick: () => { state.overview = null; buildOverview(); scheduleRender(); } }, t('remove')))));
  }
  box.replaceChildren(...children);
}

function moduleCard(m, i) {
  const sizeSel = el('select');
  SIZE_PRESETS.forEach(([w, h]) => sizeSel.append(el('option', { value: `${w}x${h}` }, t('sizeOpt', w, h))));
  sizeSel.append(el('option', { value: 'custom' }, t('customSize')));
  const preset = SIZE_PRESETS.find(([w, h]) => w === m.w && h === m.h);
  sizeSel.value = preset ? `${m.w}x${m.h}` : 'custom';
  sizeSel.addEventListener('change', () => {
    if (sizeSel.value !== 'custom') [m.w, m.h] = sizeSel.value.split('x').map(Number);
    buildModules(); buildLayout(); scheduleRender();
  });

  const meta = el('div', { class: 'meta' },
    field(t('code'), m, 'code', 'text', { onChange: () => { buildLayout(); scheduleRender(); } }),
    el('label', {}, t('size'), sizeSel),
    field(t('name'), m, 'name', 'text', { wide: true }),
    field(t('caption'), m, 'sub', 'text', { wide: true }),
  );
  if (sizeSel.value === 'custom') {
    const onChange = () => { buildModules(); scheduleRender(); };
    meta.append(field(t('width'), m, 'w', 'number', { attrs: { min: 0.5, step: 0.5 }, onChange }),
      field(t('height'), m, 'h', 'number', { attrs: { min: 0.5, step: 0.5 }, onChange }));
  }

  const move = d => {
    const j = i + d;
    if (j < 0 || j >= state.modules.length) return;
    [state.modules[i], state.modules[j]] = [state.modules[j], state.modules[i]];
    buildModules(); buildLayout(); scheduleRender();
  };
  const remove = () => {
    state.modules.splice(i, 1);
    for (const k of Object.keys(state.layout)) if (state.layout[k] === m.id) delete state.layout[k];
    if (state.filler === m.id) state.filler = '';
    if (brush === m.id) brush = '';
    buildModules(); buildLayout(); scheduleRender();
  };

  return el('div', { class: 'card' },
    cropEditor(m, m.w / m.h),
    meta,
    el('div', { class: 'tools' },
      el('button', { class: 'btn small', onclick: () => move(-1) }, '←'),
      el('button', { class: 'btn small', onclick: () => move(1) }, '→'),
      el('button', { class: 'btn small', onclick: remove }, t('remove'))));
}

function buildModules() {
  document.getElementById('moduleList').replaceChildren(...state.modules.map(moduleCard));
}

async function addModules(files) {
  for (const file of files) {
    if (!file.type.startsWith('image/')) continue;
    const n = state.modules.length + 1;
    state.modules.push({
      id: `m${nextId++}`, code: `M-${String(n).padStart(2, '0')}`,
      name: file.name.replace(/\.[^.]+$/, ''), sub: '',
      w: 3, h: 3, src: await readImageFile(file), crop: newCrop(),
    });
  }
  buildModules(); buildLayout(); scheduleRender();
}

function buildLayout() {
  const box = document.getElementById('layoutPanel');
  if (!state.modules.length) { box.replaceChildren(el('p', { class: 'hint' }, t('addModulesFirst'))); return; }

  const brushBtn = (id, label) => el('button', {
    class: 'btn small' + (brush === id ? ' active' : ''),
    onclick: () => { brush = id; buildLayout(); },
  }, label);
  const brushes = el('div', { class: 'brushes' },
    ...state.modules.map(m => brushBtn(m.id, m.code || '?')), brushBtn('', t('eraser')));

  const fillerSel = el('select');
  fillerSel.append(el('option', { value: '' }, t('none')));
  state.modules.forEach(m => fillerSel.append(el('option', { value: m.id }, `${m.code} ${m.name}`)));
  fillerSel.value = state.filler;
  fillerSel.addEventListener('change', () => { state.filler = fillerSel.value; buildLayout(); scheduleRender(); });

  const fl = floors(), n = state.bays;
  const grid = el('div', { class: 'facade' });
  grid.style.gridTemplateColumns = `repeat(${n}, 1fr)`;
  for (let f = fl.length - 1; f >= 0; f--) {
    for (let b = 0; b < n; b++) {
      const key = `${f}_${b}`;
      const mod = byId(state.layout[key]);
      const shown = mod || byId(state.filler);
      const cell = el('div', { class: 'cell' + (mod ? '' : ' empty'), title: t('cellTitle', f + 1, b + 1) },
        el('span', {}, mod ? mod.code : shown ? '·' : ''));
      cell.style.minHeight = `${Math.round(fl[f] * 14)}px`;
      if (shown) cell.style.backgroundImage = `url(${shown.src})`;
      if (!mod && shown) cell.style.opacity = '0.55';
      cell.addEventListener('click', () => {
        if (brush) state.layout[key] = brush; else delete state.layout[key];
        buildLayout(); scheduleRender();
      });
      cell.addEventListener('contextmenu', e => { e.preventDefault(); delete state.layout[key]; buildLayout(); scheduleRender(); });
      grid.append(cell);
    }
  }

  box.replaceChildren(
    brushes, grid,
    el('div', { class: 'fields', style: 'margin-top:10px' },
      el('label', { class: 'wide' }, t('filler'), fillerSel)),
    el('div', { class: 'tools', style: 'margin-top:8px;display:flex;gap:6px' },
      el('button', { class: 'btn small', onclick: () => { state.layout = {}; buildLayout(); scheduleRender(); } }, t('clearLayout'))));
}

// Average colour of an image, so a texture material also has a HEX code.
function averageHex(src) {
  return new Promise(resolve => {
    const im = new Image();
    im.onload = () => {
      const cv = document.createElement('canvas'); cv.width = cv.height = 16;
      const c = cv.getContext('2d', { willReadFrequently: true });
      c.drawImage(im, 0, 0, 16, 16);
      const d = c.getImageData(0, 0, 16, 16).data, sum = [0, 0, 0];
      for (let i = 0; i < d.length; i += 4) { sum[0] += d[i]; sum[1] += d[i + 1]; sum[2] += d[i + 2]; }
      resolve('#' + sum.map(v => Math.round(v / 256).toString(16).padStart(2, '0')).join(''));
    };
    im.onerror = () => resolve('#888888');
    im.src = src;
  });
}

async function setTexture(p, file) {
  p.src = await readImageFile(file);
  p.crop = newCrop();
  p.hex = await averageHex(p.src);
  if (!p.label) p.label = file.name.replace(/\.[^.]+$/, '');
}

async function addTextureMaterials(files) {
  for (const file of files) {
    if (!file.type.startsWith('image/') || state.palette.length >= 6) continue;
    const p = { hex: '#888888', label: '' };
    await setTexture(p, file);
    state.palette.push(p);
  }
  buildPalette(); scheduleRender();
}

function imagePicker(label, onFiles, multiple = false) {
  const input = el('input', { type: 'file', accept: 'image/*', hidden: '' });
  if (multiple) input.multiple = true;
  input.addEventListener('change', () => { if (input.files.length) onFiles([...input.files]); input.value = ''; });
  return el('label', { class: 'btn small' }, label, input);
}

function buildPalette() {
  const box = document.getElementById('palettePanel');
  const rows = state.palette.map((p, i) => {
    let swatch;
    if (p.src) {
      swatch = cropEditor(p, 1);
      swatch.classList.add('mini');
    } else {
      swatch = el('input', { type: 'color' }); swatch.value = p.hex;
      swatch.addEventListener('input', () => { p.hex = swatch.value; scheduleRender(); });
    }
    const label = el('input', { type: 'text', placeholder: t('material') }); label.value = p.label;
    label.addEventListener('input', () => { p.label = label.value; scheduleRender(); });
    const photo = imagePicker(p.src ? t('otherPhoto') : t('photo'), async files => {
      await setTexture(p, files[0]); buildPalette(); scheduleRender();
    });
    const tools = el('div', { class: 'swatch-tools' }, photo);
    if (p.src) {
      tools.append(el('button', {
        class: 'btn small',
        onclick: () => { delete p.src; delete p.crop; buildPalette(); scheduleRender(); },
      }, t('colour')));
    }
    tools.append(el('button', { class: 'btn small', onclick: () => { state.palette.splice(i, 1); buildPalette(); scheduleRender(); } }, '×'));
    return el('div', { class: 'swatch' }, swatch, label, tools);
  });

  // Extraction refreshes the plain colours and keeps the texture materials.
  const extract = () => {
    const textures = state.palette.filter(p => p.src);
    const colours = state.palette.filter(p => !p.src);
    const hexes = extractPalette().slice(0, 6 - textures.length);
    const isDefault = label => !label || /^(Материал|Material) \d+$/.test(label);
    state.palette = [...textures, ...hexes.map((hex, i) => {
      const old = colours[i]?.label;
      return { hex, label: isDefault(old) ? S('materialN', textures.length + i + 1) : old };
    })];
    buildPalette(); scheduleRender();
  };
  const full = state.palette.length >= 6;
  const drop = el('div', { class: 'drop small' }, t('matDrop'));
  makeDropZone(drop, addTextureMaterials);
  box.replaceChildren(
    el('div', { class: 'brushes' },
      el('button', { class: 'btn small', onclick: extract }, t('takeColours')),
      el('button', {
        class: 'btn small',
        onclick: () => { if (!full) state.palette.push({ hex: '#888888', label: '' }); buildPalette(); scheduleRender(); },
      }, t('addColour')),
      imagePicker(t('addMaterial'), addTextureMaterials, true)),
    ...(full ? [] : [drop]),
    ...rows,
    el('p', { class: 'hint' }, t('matHint')));
}

function applyAccent() { document.documentElement.style.setProperty('--accent', state.accent); }

function buildAll() {
  applyStaticText();
  applyAccent();
  buildProject(); buildGrid(); buildOverview(); buildModules(); buildLayout(); buildPalette();
  scheduleRender();
}

// ---------- drag & drop, files ----------
function makeDropZone(zone, onFiles) {
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('over'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('over');
    const files = [...e.dataTransfer.files].filter(f => f.type.startsWith('image/'));
    if (files.length) onFiles(files);
  });
}

function download(blob, name) {
  const a = el('a', { href: URL.createObjectURL(blob), download: name });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

const fileBase = () => (state.title || 'refboard').replace(/[^\w.-]+/g, '_');

document.getElementById('version').textContent = `v${VERSION}`;

document.querySelectorAll('[data-lang]').forEach(b => b.addEventListener('click', () => {
  uiLang = b.dataset.lang;
  saveUiLang();
  buildAll();
}));

document.getElementById('moduleFiles').addEventListener('change', e => { addModules([...e.target.files]); e.target.value = ''; });
makeDropZone(document.getElementById('moduleDrop'), addModules);

document.getElementById('exportPng').addEventListener('click', () => {
  render();
  sheet.toBlob(b => download(b, `${fileBase()}_refboard.png`), 'image/png');
});

document.getElementById('saveProject').addEventListener('click', () => {
  download(new Blob([JSON.stringify({ ...state, version: VERSION })], { type: 'application/json' }), `${fileBase()}.refboard.json`);
});

document.getElementById('loadProject').addEventListener('change', async e => {
  const file = e.target.files[0];
  e.target.value = '';
  if (!file) return;
  try {
    state = Object.assign(defaultState(), JSON.parse(await file.text()));
    nextId = 1 + Math.max(0, ...state.modules.map(m => parseInt(m.id.slice(1), 10) || 0));
    brush = '';
    buildAll();
  } catch (err) {
    alert(t('loadError') + err.message);
  }
});

// Loads after fonts so the first render uses Bahnschrift where available.
(document.fonts ? document.fonts.ready : Promise.resolve()).then(buildAll);

// For quick checks from the browser console.
window.RB = { state: () => state, addModules, render, extractPalette };
