// Hand-written SVG charts. No libraries, so the demo works fully offline.
// Every chart: thin marks, quiet grid, hover tooltip, direct values where they help.
import { esc, hideTip, showTip, reduceMotion } from "./util.js";

const NS = "http://www.w3.org/2000/svg";
let uid = 0;

export function niceTicks(min, max, n = 5) {
  const span = max - min || 1;
  const raw = span / n;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const err = raw / mag;
  const step = (err >= 5 ? 10 : err >= 2 ? 5 : err >= 1 ? 2 : 1) * mag;
  const out = [];
  for (let v = Math.ceil(min / step - 1e-9) * step; v <= max + step * 1e-6; v += step) out.push(+v.toFixed(10));
  return out;
}

function mount(container, render) {
  container.classList.add("chart");
  let lastW = 0;
  const run = () => {
    const w = Math.max(260, Math.floor(container.clientWidth));
    if (w === lastW) return;
    lastW = w;
    render(w);
  };
  run();
  if (container._ro) container._ro.disconnect();
  if ("ResizeObserver" in window) {
    const ro = new ResizeObserver(run);
    ro.observe(container);
    container._ro = ro;
  }
}

const num = (v) => Math.round(v * 100) / 100;
const lineD = (pts) => pts.map((p, i) => (i ? "L" : "M") + num(p[0]) + "," + num(p[1])).join("");
const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const timeLabel = (v) => { const d = new Date(v); return MON[d.getUTCMonth()] + " " + String(d.getUTCFullYear()).slice(2); };
const fullDate = (v) => { const d = new Date(v); return d.getUTCDate() + " " + MON[d.getUTCMonth()] + " " + d.getUTCFullYear(); };

function roundedTop(x, y, w, h, r) {
  r = Math.max(0, Math.min(r, w / 2, h));
  if (h <= 0) return "";
  return `M${num(x)},${num(y + h)}V${num(y + r)}Q${num(x)},${num(y)} ${num(x + r)},${num(y)}H${num(x + w - r)}Q${num(x + w)},${num(y)} ${num(x + w)},${num(y + r)}V${num(y + h)}Z`;
}

function yAxis(ticks, Y, m, W, fmt) {
  return `<g class="grid">${ticks.map((t) => `<line x1="${m.l}" x2="${W - m.r}" y1="${num(Y(t))}" y2="${num(Y(t))}"/>`).join("")}</g>` +
    ticks.map((t) => `<text x="${m.l - 10}" y="${num(Y(t))}" text-anchor="end" dominant-baseline="middle">${esc(fmt(t))}</text>`).join("");
}

// ------------------------------------------------------------------ line / area
export function lineChart(container, o) {
  const H = o.height || 300;
  const m = { l: o.left || 54, r: 18, t: 16, b: 32 };
  const id = ++uid;
  mount(container, (W) => {
    const iw = W - m.l - m.r, ih = H - m.t - m.b;
    const all = o.series.flatMap((s) => s.values);
    const xs = all.map((p) => +p.x);
    const x0 = o.xMin ?? Math.min(...xs), x1 = o.xMax ?? Math.max(...xs);
    const y0 = o.yMin ?? 0;
    let y1 = o.yMax ?? Math.max(...all.map((p) => p.y)) * 1.06;
    const yt = niceTicks(y0, y1, o.yTicks || 5);
    if (o.yMax == null) y1 = Math.max(y1, yt[yt.length - 1]);
    const X = (v) => m.l + ((v - x0) / (x1 - x0 || 1)) * iw;
    const Y = (v) => m.t + ih - ((v - y0) / (y1 - y0 || 1)) * ih;
    const yFmt = o.yFormat || String;
    const xFmt = o.xFormat || timeLabel;
    const nx = Math.max(2, Math.min(8, Math.floor(iw / 120)));
    let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(o.label || "Line chart")}" height="${H}">`;
    svg += `<defs>${o.series.map((s, i) => `<linearGradient id="g${id}_${i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${s.color}" stop-opacity="0.26"/><stop offset="1" stop-color="${s.color}" stop-opacity="0"/></linearGradient>`).join("")}</defs>`;
    svg += yAxis(yt, Y, m, W, yFmt);
    const xticks = o.xTicks && iw > 420 ? o.xTicks : Array.from({ length: nx + 1 }, (_, i) => x0 + ((x1 - x0) * i) / nx);
    for (let i = 0; i < xticks.length; i++) {
      const v = xticks[i];
      const anchor = i === 0 ? "start" : i === xticks.length - 1 ? "end" : "middle";
      svg += `<text x="${num(X(v))}" y="${H - 8}" text-anchor="${anchor}">${esc(xFmt(v))}</text>`;
    }
    svg += `<line class="axis-line" x1="${m.l}" x2="${W - m.r}" y1="${num(Y(y0))}" y2="${num(Y(y0))}"/>`;
    (o.refs || []).forEach((r) => {
      svg += `<line x1="${m.l}" x2="${W - m.r}" y1="${num(Y(r.y))}" y2="${num(Y(r.y))}" stroke="${r.color || "var(--ink-3)"}" stroke-dasharray="5 5" stroke-width="1"/>` +
        `<text class="halo" x="${m.l + 8}" y="${num(Y(r.y)) + 16}" text-anchor="start" style="fill:var(--ink-2)">${esc(r.label)}</text>`;
    });
    (o.markers || []).forEach((mk) => {
      const x = X(mk.x);
      const anchor = x > W - 150 ? "end" : "start";
      svg += `<line x1="${num(x)}" x2="${num(x)}" y1="${m.t}" y2="${num(Y(y0))}" stroke="${mk.color || "var(--ink-3)"}" stroke-dasharray="3 4" stroke-width="1"/>` +
        `<text x="${num(x) + (anchor === "start" ? 7 : -7)}" y="${num(m.t + ih * 0.62)}" text-anchor="${anchor}" style="fill:var(--ink-2)" class="halo">${esc(mk.label)}</text>`;
    });
    (o.rug || []).forEach((r) => {
      svg += `<line x1="${num(X(+r))}" x2="${num(X(+r))}" y1="${num(Y(y0)) - 9}" y2="${num(Y(y0))}" stroke="var(--ink-2)" stroke-width="1.5" stroke-linecap="round" opacity="0.8"/>`;
    });
    o.series.forEach((s, i) => {
      const pts = s.values.map((p) => [X(+p.x), Y(p.y)]);
      if (s.area) svg += `<path d="${lineD(pts)}L${num(pts[pts.length - 1][0])},${num(Y(y0))}L${num(pts[0][0])},${num(Y(y0))}Z" fill="url(#g${id}_${i})"/>`;
      svg += `<path class="${o.animate === false ? "" : "draw"} s-line" data-i="${i}" d="${lineD(pts)}" fill="none" stroke="${s.color}" stroke-width="${s.width || 2}" stroke-linejoin="round" stroke-linecap="round"/>`;
    });
    svg += `<g class="hover" style="display:none"><line class="cross" y1="${m.t}" y2="${num(Y(y0))}" stroke="var(--ink-2)" stroke-width="1" opacity="0.55"/>` +
      o.series.map((s) => `<circle class="dotp" r="4.5" fill="${s.color}" stroke="var(--surface)" stroke-width="2"/>`).join("") + `</g>`;
    svg += `<rect class="hit" x="${m.l}" y="${m.t}" width="${iw}" height="${ih}"/></svg>`;
    container.innerHTML = svg;

    container.querySelectorAll(".draw").forEach((p) => { try { p.style.setProperty("--len", Math.ceil(p.getTotalLength()) + 2); } catch (_) { p.classList.remove("draw"); } });
    if (reduceMotion()) container.querySelectorAll(".draw").forEach((p) => p.classList.remove("draw"));

    const hover = container.querySelector(".hover"), cross = container.querySelector(".cross");
    const dots = [...container.querySelectorAll(".dotp")];
    const hit = container.querySelector(".hit");
    const nearest = (vals, xv) => {
      let lo = 0, hi = vals.length - 1;
      while (hi - lo > 1) { const mid = (lo + hi) >> 1; (+vals[mid].x < xv ? (lo = mid) : (hi = mid)); }
      return Math.abs(+vals[lo].x - xv) <= Math.abs(+vals[hi].x - xv) ? vals[lo] : vals[hi];
    };
    hit.addEventListener("mousemove", (e) => {
      const r = container.querySelector("svg").getBoundingClientRect();
      const xv = x0 + ((e.clientX - r.left - m.l) / iw) * (x1 - x0);
      const pts = o.series.map((s) => nearest(s.values, xv));
      const px = X(+pts[0].x);
      hover.style.display = "";
      cross.setAttribute("x1", px); cross.setAttribute("x2", px);
      pts.forEach((p, i) => { dots[i].setAttribute("cx", px); dots[i].setAttribute("cy", Y(p.y)); });
      const html = o.tooltip
        ? o.tooltip(pts, o.series)
        : `<div class="t">${esc(xFmt === timeLabel ? fullDate(+pts[0].x) : xFmt(+pts[0].x))}</div>` +
          pts.map((p, i) => `<div class="row"><i class="sw" style="background:${o.series[i].color}"></i>${esc(o.series[i].name)}: <b style="color:var(--ink)">${esc(yFmt(p.y))}</b></div>`).join("");
      showTip(html, e.clientX, e.clientY);
    });
    hit.addEventListener("mouseleave", () => { hover.style.display = "none"; hideTip(); });
  });
}

// ------------------------------------------------------------------ columns (single or grouped)
export function columnChart(container, o) {
  const H = o.height || 280;
  const m = { l: o.left || 54, r: 12, t: 22, b: o.bottom || 34 };
  mount(container, (W) => {
    const iw = W - m.l - m.r, ih = H - m.t - m.b;
    const cats = o.categories, k = o.series.length;
    const max = Math.max(...o.series.flatMap((s) => s.values), o.ref ? o.ref.y : 0, 1e-9);
    const yt = niceTicks(0, max * 1.08, o.yTicks || 4);
    const y1 = Math.max(yt[yt.length - 1], max);
    const Y = (v) => m.t + ih - (v / y1) * ih;
    const gw = iw / cats.length;
    const barW = Math.min(o.maxBar || 40, (gw * 0.72 - 2 * (k - 1)) / k);
    const yFmt = o.yFormat || String;
    const every = Math.max(1, Math.ceil(cats.length / Math.max(1, Math.floor(iw / (o.labelWidth || 54)))));
    let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(o.label || "Column chart")}" height="${H}">`;
    svg += yAxis(yt, Y, m, W, yFmt);
    svg += `<line class="axis-line" x1="${m.l}" x2="${W - m.r}" y1="${num(Y(0))}" y2="${num(Y(0))}"/>`;
    cats.forEach((c, i) => {
      const gx = m.l + i * gw + (gw - (barW * k + 2 * (k - 1))) / 2;
      o.series.forEach((s, j) => {
        const v = s.values[i];
        const h = Math.max(0, (v / y1) * ih);
        const color = (s.colors && s.colors[i]) || s.color;
        svg += `<path d="${roundedTop(gx + j * (barW + 2), Y(v), barW, h, 4)}" fill="${color}"/>`;
        if (o.valueLabels && cats.length <= 14 && k === 1) svg += `<text x="${num(gx + barW / 2)}" y="${num(Y(v)) - 6}" text-anchor="middle" style="fill:var(--ink-2)">${esc(yFmt(v))}</text>`;
      });
      if (i % every === 0) svg += `<text x="${num(m.l + i * gw + gw / 2)}" y="${H - 10}" text-anchor="middle">${esc(c)}</text>`;
      svg += `<rect class="hit" data-i="${i}" x="${num(m.l + i * gw)}" y="${m.t}" width="${num(gw)}" height="${ih}"/>`;
    });
    if (o.ref) svg += `<line x1="${m.l}" x2="${W - m.r}" y1="${num(Y(o.ref.y))}" y2="${num(Y(o.ref.y))}" stroke="var(--line-strong)" stroke-dasharray="5 5" stroke-width="1"/>` +
      `<text x="${m.l + 6}" y="${num(Y(o.ref.y)) - 7}" style="fill:var(--ink-2)">${esc(o.ref.label)}</text>`;
    container.innerHTML = svg + "</svg>";
    container.querySelectorAll(".hit").forEach((r) => {
      r.addEventListener("mousemove", (e) => {
        const i = +r.dataset.i;
        const html = o.tooltip
          ? o.tooltip(i)
          : `<div class="t">${esc(cats[i])}</div>` + o.series.map((s) => `<div class="row"><i class="sw" style="background:${(s.colors && s.colors[i]) || s.color}"></i>${esc(s.name)}: <b style="color:var(--ink)">${esc(yFmt(s.values[i]))}</b></div>`).join("");
        showTip(html, e.clientX, e.clientY);
      });
      r.addEventListener("mouseleave", hideTip);
    });
  });
}

// ------------------------------------------------------------------ scatter (customer map)
export function scatter(container, o) {
  const H = o.height || 420;
  const m = { l: 56, r: 16, t: 14, b: 40 };
  mount(container, (W) => {
    const iw = W - m.l - m.r, ih = H - m.t - m.b;
    const [x0, x1] = o.xDomain, [y0, y1] = o.yDomain;
    const X = (v) => m.l + ((v - x0) / (x1 - x0)) * iw;
    const Y = (v) => m.t + ih - ((Math.min(v, y1 * 0.985) - y0) / (y1 - y0)) * ih;
    const yt = niceTicks(y0, y1, 4), xt = niceTicks(x0, x1, 5);
    let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(o.label || "Scatter chart")}" height="${H}">`;
    svg += yAxis(yt, Y, m, W, o.yFormat || String);
    svg += xt.map((t) => `<text x="${num(X(t))}" y="${H - 20}" text-anchor="middle">${esc((o.xFormat || String)(t))}</text>`).join("");
    svg += `<text x="${num(m.l + iw / 2)}" y="${H - 2}" text-anchor="middle">${esc(o.xTitle || "")}</text>`;
    svg += `<line class="axis-line" x1="${m.l}" x2="${W - m.r}" y1="${num(Y(y0))}" y2="${num(Y(y0))}"/>`;
    if (o.quad) {
      svg += `<line x1="${num(X(o.quad.x))}" x2="${num(X(o.quad.x))}" y1="${m.t}" y2="${num(Y(y0))}" stroke="var(--ink-3)" stroke-dasharray="4 5" opacity="0.7"/>` +
        `<line x1="${m.l}" x2="${W - m.r}" y1="${num(Y(o.quad.y))}" y2="${num(Y(o.quad.y))}" stroke="var(--ink-3)" stroke-dasharray="4 5" opacity="0.7"/>`;
    }
    svg += o.points.map((p) => `<circle cx="${num(X(p.x))}" cy="${num(Y(p.y))}" r="${o.r || 2.6}" fill="${p.color}" opacity="0.78"/>`).join("");
    (o.labels || []).forEach((l) => {
      svg += `<text class="qlabel" x="${num(X(l.x))}" y="${num(Y(l.y))}" text-anchor="${l.anchor || "start"}" style="fill:${l.color}">${esc(l.text)}</text>` +
        (l.sub ? `<text x="${num(X(l.x))}" y="${num(Y(l.y)) + 16}" text-anchor="${l.anchor || "start"}">${esc(l.sub)}</text>` : "");
    });
    if (o.highlight) {
      const hx = X(o.highlight.x), hy = Y(o.highlight.y);
      svg += `<circle class="pulse" cx="${num(hx)}" cy="${num(hy)}" r="7" fill="none" stroke="var(--s1)" stroke-width="1.5"/>` +
        `<circle cx="${num(hx)}" cy="${num(hy)}" r="5.5" fill="var(--s1)" stroke="var(--surface)" stroke-width="2"/>`;
      const left = hx > W - 170;
      svg += `<text x="${num(hx) + (left ? -12 : 12)}" y="${num(hy) - 10}" text-anchor="${left ? "end" : "start"}" style="fill:var(--accent);font-weight:600;font-size:13px">${esc(o.highlight.label)}</text>`;
    }
    svg += `<rect class="hit" x="${m.l}" y="${m.t}" width="${iw}" height="${ih}"/></svg>`;
    container.innerHTML = svg;
    const hit = container.querySelector(".hit");
    const find = (e) => {
      const r = container.querySelector("svg").getBoundingClientRect();
      const mx = e.clientX - r.left, my = e.clientY - r.top;
      let best = null, bd = 14 * 14;
      for (const p of o.points) { const dx = X(p.x) - mx, dy = Y(p.y) - my, d = dx * dx + dy * dy; if (d < bd) { bd = d; best = p; } }
      return best;
    };
    hit.addEventListener("mousemove", (e) => {
      const p = find(e);
      hit.style.cursor = p && o.onPick ? "pointer" : "default";
      if (p) showTip(o.tooltip(p), e.clientX, e.clientY); else hideTip();
    });
    hit.addEventListener("mouseleave", hideTip);
    if (o.onPick) hit.addEventListener("click", (e) => { const p = find(e); if (p) o.onPick(p); });
  });
}

// ------------------------------------------------------------------ html helpers
export function hbars(rows, { format = String, max } = {}) {
  const top = max ?? Math.max(...rows.map((r) => r.value), 1e-9);
  return rows.map((r) => `<div class="hbar"><span title="${esc(r.label)}">${esc(r.label)}</span>` +
    `<div class="track"><div class="fill" style="width:${Math.max(1, (r.value / top) * 100)}%;${r.color ? "background:" + r.color : ""}"></div></div>` +
    `<span class="val">${esc(format(r.value))}</span></div>`).join("");
}

export function stackBar(items) {
  return `<div class="stack" role="img" aria-label="${esc(items.map((i) => i.name + " " + i.text).join(", "))}">` +
    items.map((i) => `<div style="flex-grow:${Math.max(i.value, 0.0001)};background:${i.color}" title="${esc(i.name)}: ${esc(i.text)}"></div>`).join("") + `</div>`;
}

export const legend = (items) =>
  `<div class="legend">${items.map((i) => `<span><i class="sw" style="background:${i.color}"></i>${esc(i.name)}</span>`).join("")}</div>`;
