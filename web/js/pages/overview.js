import { api } from "../api.js";
import { scatter, legend } from "../charts.js";
import { SEGMENTS, SEG_ORDER, esc, int, gbp, gbpShort, pct, pctPts, countUp, btn, $, $$ } from "../util.js";

export const title = "Overview";

const SHORT = {
  Protect: { goal: "High value, slipping away", act: "Personal outreach before they lapse" },
  Grow: { goal: "High value, still active", act: "Reward and deepen, no discounts" },
  "Win back": { goal: "Lower value, likely gone", act: "Low-cost reactivation, email first" },
  Maintain: { goal: "Lower value, still active", act: "Keep warm, no extra spend" },
};

export async function render(root) {
  const [o, seg, demo] = await Promise.all([api.overview(), api.segments(), api.customer("C10000").catch(() => null)]);
  const h = o.headline, mh = o.model_headline;
  const segs = Object.fromEntries(o.segments.map((s) => [s.segment, s]));
  const plan = Object.fromEntries(seg.segments.map((s) => [s.segment, s]));
  const potential = o.segments.reduce((a, s) => a + s.potential_12m_gbp, 0);
  const totals = { risk: h.revenue_at_risk_12m_gbp, customers: h.customers };
  const protect = segs["Protect"];

  const tile = (n) => {
    const s = segs[n], p = plan[n];
    const act = SHORT[n].act, goal = SHORT[n].goal;
    const ret = p.roi == null ? "No campaign spend" : `Expected return ${p.roi.toFixed(1)}x on campaign cost`;
    return `<button class="tile" data-seg="${esc(n)}" aria-label="${esc(n)}: open details">
      <div><div class="nm"><i class="dot ${SEGMENTS[n].key}"></i>${esc(n)}</div><div class="goal">${goal}</div></div>
      <div><div class="fig">${gbpShort(s.revenue_at_risk_12m_gbp)}</div>
        <div class="meta">at risk, across ${int(s.customers)} customers (${pctPts(p.customers_pct)} of the base)</div>
        <div class="act"><b class="strong">${esc(act)}</b><br><span class="label">${ret}</span></div></div>
    </button>`;
  };

  root.innerHTML = `
  <section class="hero">
    <p class="kicker">Revenue at risk over the next 12 months</p>
    <p class="big" id="hero-risk">${gbpShort(h.revenue_at_risk_12m_gbp)}</p>
    <p class="lede">${int(protect.customers)} of our best customers are quietly drifting away. <span class="label" style="font-size:inherit;display:block;margin-top:2px">Targeted campaigns could realistically win back <b style="color:var(--ink);white-space:nowrap" id="gain">about ${gbpShort(h.expected_gain_gbp)}</b><span class="tag">assumption</span></span></p>
    <div class="sim" id="sim">
      <label>Protect save rate <b id="v-p">${Math.round(plan["Protect"].assumptions.save_rate * 100)}%</b>
        <input type="range" id="r-p" min="0" max="60" step="1" value="${Math.round(plan["Protect"].assumptions.save_rate * 100)}" aria-label="Protect save rate"></label>
      <label>Win back rate <b id="v-w">${Math.round(plan["Win back"].assumptions.save_rate * 100)}%</b>
        <input type="range" id="r-w" min="0" max="40" step="1" value="${Math.round(plan["Win back"].assumptions.save_rate * 100)}" aria-label="Win back rate"></label>
      <div class="simout"><span id="sim-net"></span></div>
    </div>
    <div class="cta">${btn("Start the guided demo", 'data-go="#/customer/C10000"')}<a class="link" data-scroll="#bento" role="link" tabindex="0">See where it sits</a></div>
    <div class="barzone">
      <div class="barhead"><span id="bar-title"></span>
        <div class="tabs" role="tablist" id="bar-tabs"><button role="tab" data-m="risk" aria-selected="true">Revenue at risk</button><button role="tab" data-m="customers" aria-selected="false">Customers</button></div></div>
      <div class="bar" id="bar" role="img"></div>
      <div class="barlabels" id="barlabels"></div>
    </div>
  </section>
  <div class="seam" id="seam"><svg id="seam-svg" aria-hidden="true"></svg></div>

  <section class="bento" id="bento">
    ${SEG_ORDER.map(tile).join("")}

    <div class="card span2" style="grid-row:span 2">
      <h2>The four groups are the four corners of this map</h2>
      <p class="sub">Left to right: chance the customer has drifted away. Bottom to top: 12-month value if kept active. Each dot is a customer.</p>
      <div id="map" style="margin-top:8px"></div>
    </div>
    <div class="card span2">
      <h2>What the next year looks like</h2>
      <p class="sub">Of the ${gbpShort(potential)} these customers could be worth, ${gbpShort(h.clv_12m_gbp)} is expected and ${gbpShort(h.revenue_at_risk_12m_gbp)} is at risk.</p>
      <div class="trio">
        <div><div class="fig">${gbpShort(h.clv_12m_gbp)}</div><div class="meta">expected, 12 months</div></div>
        <div><div class="fig">${gbpShort(h.clv_6m_gbp)}</div><div class="meta">expected, 6 months</div></div>
        <div><div class="fig">${gbpShort(potential)}</div><div class="meta">if every customer stayed active</div></div>
      </div>
    </div>
    <div class="card span2">
      <div style="display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap"><h2>Can we trust it?</h2><span class="label">Tested on a year the model never saw</span></div>
      <div class="trio">
        <div><div class="fig">${gbp(mh.mae_12m)}</div><div class="meta">average miss per customer, RFM benchmark ${gbp(mh.rfm_mae_12m)}</div></div>
        <div><div class="fig">${mh.bias_pct_12m > 0 ? "+" : ""}${mh.bias_pct_12m.toFixed(1)}%</div><div class="meta">total vs actual, RFM benchmark ${mh.rfm_bias_pct_12m > 0 ? "+" : ""}${mh.rfm_bias_pct_12m.toFixed(0)}%</div></div>
        <div><div class="fig">${mh.churn_auc.toFixed(2)}</div><div class="meta">churn detection, 1.0 is perfect</div></div>
      </div>
    </div>

    <div class="demo span4">
      <div><h2>Follow one customer from signal to action.</h2>
        <p>${demo ? `C10000, ${demo.profile.age}, ${esc(demo.profile.country)}. ${pct(demo.prediction.churn_risk)} chance they have drifted away, with ${gbp(demo.prediction.revenue_at_risk_12m)} of value at risk.` : "Pick a customer and see why the model flagged them."}</p></div>
      <div style="display:flex;gap:12px;flex-wrap:wrap">${btn("Start the guided demo", 'data-go="#/customer/C10000"')}${btn("Compare with C10001", 'data-go="#/customer/C10001"')}</div>
    </div>
  </section>`;

  // what-if sliders: recompute recoverable revenue and net return from the plan's own assumptions
  const calc = (sp, sw) => {
    let gain = 0, cost = 0;
    for (const n of SEG_ORDER) {
      const a = plan[n].assumptions, s = segs[n];
      const rate = n === "Protect" ? sp : n === "Win back" ? sw : a.save_rate;
      const rec = s.revenue_at_risk_12m_gbp * rate + s.clv_12m_gbp * a.upside_rate;
      gain += rec; cost += s.customers * a.cost_contact + rec * a.offer_cost;
    }
    return { gain, cost, net: gain - cost };
  };
  const rp = $("#r-p"), rw = $("#r-w");
  const upd = () => {
    const sp = +rp.value / 100, sw = +rw.value / 100, r = calc(sp, sw);
    $("#v-p").textContent = rp.value + "%"; $("#v-w").textContent = rw.value + "%";
    $("#gain").textContent = "about " + gbpShort(r.gain);
    $("#sim-net").textContent = `Campaign cost ${gbpShort(r.cost)}, net return ${gbpShort(r.net)}`;
  };
  rp.addEventListener("input", upd); rw.addEventListener("input", upd); upd();


  countUp($("#hero-risk", root), h.revenue_at_risk_12m_gbp, gbpShort);

  // ---- the bar: one measure at a time, same colours as the tiles below
  let metric = "risk";
  const drawBar = () => {
    const key = metric === "risk" ? "revenue_at_risk_12m_gbp" : "customers";
    const tot = metric === "risk" ? totals.risk : totals.customers;
    $("#bar-title", root).textContent = metric === "risk" ? `Share of the ${gbpShort(totals.risk)}, by customer group` : `Share of ${int(totals.customers)} customers, by customer group`;
    const items = SEG_ORDER.map((n) => ({ n, v: segs[n][key], f: segs[n][key] / tot }));
    const bar = $("#bar", root), lab = $("#barlabels", root);
    bar.setAttribute("aria-label", items.map((i) => `${i.n} ${Math.round(i.f * 100)}%`).join(", "));
    if (!bar.children.length) {
      bar.innerHTML = items.map((i) => `<div style="background:${SEGMENTS[i.n].color}"></div>`).join("");
      lab.innerHTML = items.map(() => `<div></div>`).join("");
    }
    items.forEach((i, k) => {
      bar.children[k].style.flexGrow = Math.max(i.f, 0.0001);
      lab.children[k].style.flexGrow = Math.max(i.f, 0.0001);
      lab.children[k].innerHTML = `<b>${i.n}</b> ${Math.round(i.f * 100)}%`;
    });
  };
  drawBar();
  $("#bar-tabs", root).addEventListener("click", (e) => {
    const b = e.target.closest("button[data-m]");
    if (!b) return;
    metric = b.dataset.m;
    $$("#bar-tabs button", root).forEach((x) => x.setAttribute("aria-selected", x === b));
    drawBar();
    [60, 380, 760].forEach((t) => setTimeout(drawSeam, t));
  });

  // ---- the seam: the bar's colours run down into the tiles
  function drawSeam() {
    const seam = $("#seam", root), svg = $("#seam-svg", root);
    if (!seam || !svg) return;
    const sr = seam.getBoundingClientRect();
    if (sr.width < 700) { svg.innerHTML = ""; return; }
    const H = sr.height, W = sr.width;
    svg.setAttribute("width", W); svg.setAttribute("height", H); svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.style.left = "0";
    const bars = $("#bar", root).children, tiles = $$(".tile", root);
    let out = "";
    SEG_ORDER.forEach((n, k) => {
      const b = bars[k].getBoundingClientRect(), t = tiles[k].getBoundingClientRect();
      const x1 = b.left + b.width / 2 - sr.left, x2 = t.left + t.width / 2 - sr.left;
      const y1 = b.bottom - sr.top + 3, y2 = H - 8;
      const c = SEGMENTS[n].color;
      out += `<path d="M${x1.toFixed(1)} ${y1.toFixed(1)} C${x1.toFixed(1)} ${(y1 + (y2 - y1) * 0.6).toFixed(1)} ${x2.toFixed(1)} ${(y1 + (y2 - y1) * 0.35).toFixed(1)} ${x2.toFixed(1)} ${y2}" fill="none" style="stroke:${c}" stroke-width="2" opacity="0.7"/><circle cx="${x2.toFixed(1)}" cy="${y2 + 2}" r="5" style="fill:${c}"/>`;
    });
    svg.innerHTML = out;
  }
  requestAnimationFrame(drawSeam);
  setTimeout(drawSeam, 250);
  if ("ResizeObserver" in window) new ResizeObserver(drawSeam).observe($("#seam", root));

  // ---- navigation
  $$(".tile", root).forEach((t) => t.addEventListener("click", () => { location.hash = "#/segments/" + encodeURIComponent(t.dataset.seg); }));
  const go = $("[data-scroll]", root);
  const scrollDown = () => $(go.dataset.scroll, root).scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
  go.addEventListener("click", scrollDown);
  go.addEventListener("keydown", (e) => { if (e.key === "Enter") scrollDown(); });

  // ---- customer map
  const yCap = (() => {
    const v = o.scatter.map((p) => p.potential_clv_12m).sort((a, b) => a - b);
    const top = Math.max(v[Math.floor(v.length * 0.985)], demo ? demo.prediction.potential_clv_12m * 1.04 : 0);
    return Math.ceil(top / 50) * 50;
  })();
  const cut = o.rules.high_value_cutoff_potential_12m_gbp, risk = o.rules.high_risk_cutoff;
  scatter($("#map", root), {
    label: "Customer map: churn risk against 12-month value if kept active",
    height: 400, xDomain: [0, 1], yDomain: [0, yCap],
    xFormat: (v) => Math.round(v * 100) + "%", yFormat: (v) => "£" + v,
    xTitle: "Chance the customer has drifted away",
    quad: { x: risk, y: cut },
    points: o.scatter.map((p) => ({ x: p.churn_risk, y: p.potential_clv_12m, color: SEGMENTS[p.segment].color, id: p.customer_id, seg: p.segment, v: p.potential_clv_12m, c: p.clv_12m })),
    labels: [
      { text: "Grow", x: 0.015, y: yCap * 0.95, color: "var(--grow-text)" },
      { text: "Protect", x: 0.985, y: yCap * 0.95, anchor: "end", color: "var(--protect-text)" },
      { text: "Maintain", x: 0.015, y: cut * 0.82, color: "var(--maintain-text)" },
      { text: "Win back", x: 0.985, y: cut * 0.82, anchor: "end", color: "var(--winback-text)" },
    ],
    highlight: demo ? { x: demo.prediction.churn_risk, y: demo.prediction.potential_clv_12m, label: "C10000, guided demo" } : null,
    tooltip: (p) => `<div class="t">${esc(p.id)}</div><div class="row"><i class="sw ${SEGMENTS[p.seg].key}"></i>${esc(p.seg)}</div><div class="row">Worth if kept active: <b style="color:var(--ink)">${gbp(p.v)}</b></div><div class="row">Expected value: <b style="color:var(--ink)">${gbp(p.c)}</b></div><div class="row">Click to open</div>`,
    onPick: (p) => { location.hash = "#/customer/" + p.id; },
  });
}
