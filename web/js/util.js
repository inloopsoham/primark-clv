// Small helpers shared by every page. No dependencies.

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

export const int = (n) => (n == null ? "n/a" : Number(n).toLocaleString("en-GB", { maximumFractionDigits: 0 }));
export const gbp = (n, d = 0) =>
  n == null ? "n/a" : (n < 0 ? "-" : "") + "£" + Math.abs(Number(n)).toLocaleString("en-GB", { minimumFractionDigits: d, maximumFractionDigits: d });
export function gbpShort(n) {
  if (n == null) return "n/a";
  const a = Math.abs(n), s = n < 0 ? "-" : "";
  const t = (v, d) => v.toFixed(d).replace(/\.0+$/, "");
  if (a >= 1e6) return s + "£" + t(a / 1e6, 2) + "m";
  if (a >= 1e5) return s + "£" + Math.round(a / 1e3) + "k";
  if (a >= 1e3) return s + "£" + t(a / 1e3, 1) + "k";
  return s + "£" + Math.round(a);
}
export const pct = (frac, d = 0) => (frac == null ? "n/a" : (frac * 100).toFixed(d) + "%");
export const pctPts = (v, d = 0) => (v == null ? "n/a" : Number(v).toFixed(d) + "%");
export const signed = (v, d = 1) => (v > 0 ? "+" : "") + Number(v).toFixed(d);

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export function fdate(iso) {
  if (!iso) return "n/a";
  const [y, m, d] = String(iso).slice(0, 10).split("-").map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
}
export const fmonth = (ym) => { const [y, m] = ym.split("-").map(Number); return `${MONTHS[m - 1]} ${String(y).slice(2)}`; };
export const toDate = (iso) => { const [y, m, d] = iso.slice(0, 10).split("-").map(Number); return new Date(Date.UTC(y, m - 1, d)); };

export const SEGMENTS = {
  Protect: { key: "protect", color: "var(--protect)" },
  Grow: { key: "grow", color: "var(--grow)" },
  "Win back": { key: "win-back", color: "var(--winback)" },
  Maintain: { key: "maintain", color: "var(--maintain)" },
};
export const SEG_ORDER = ["Protect", "Grow", "Win back", "Maintain"];
export const segPill = (name) =>
  `<span class="pill"><i class="dot ${SEGMENTS[name].key}"></i>${esc(name)}</span>`;

export const reduceMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function countUp(el, to, fmt, ms = 1100) {
  if (reduceMotion() || !isFinite(to)) { el.textContent = fmt(to); return; }
  const t0 = performance.now();
  const step = (t) => {
    const k = Math.min(1, (t - t0) / ms);
    el.textContent = fmt(to * (1 - Math.pow(1 - k, 3)));
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// ---- tooltip (one shared element)
let tipEl;
function tip() {
  if (!tipEl) { tipEl = document.createElement("div"); tipEl.className = "tip"; tipEl.setAttribute("role", "status"); document.body.appendChild(tipEl); }
  return tipEl;
}
export function showTip(html, clientX, clientY) {
  const t = tip();
  t.innerHTML = html;
  t.classList.add("on");
  const r = t.getBoundingClientRect();
  let x = clientX + 16, y = clientY + 16;
  if (x + r.width > window.innerWidth - 8) x = clientX - r.width - 16;
  if (y + r.height > window.innerHeight - 8) y = clientY - r.height - 16;
  t.style.left = Math.max(8, x) + "px";
  t.style.top = Math.max(8, y) + "px";
}
export const hideTip = () => tipEl && tipEl.classList.remove("on");

export function icon(name) {
  const p = {
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    search: '<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4-4"/>',
    warn: '<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17.2v.1"/>',
  }[name];
  return `<svg viewBox="0 0 24 24" aria-hidden="true">${p}</svg>`;
}

export function btn(label, attrs = "") {
  return `<button class="btn" ${attrs}>${esc(label)}<span class="ic">${icon("arrow")}</span></button>`;
}

export const debounce = (fn, ms = 160) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
