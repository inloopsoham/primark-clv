import { api } from "../api.js";
import { lineChart, columnChart, hbars, legend } from "../charts.js";
import { SEGMENTS, esc, int, gbp, gbpShort, pct, pctPts, fdate, toDate, segPill, icon, btn, debounce, $ } from "../util.js";

export const lede = "Look up any customer and see why the model flagged them and what to do next.";
export const title = "Customer lookup";

const warnIcon = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17.2v.1"/></svg>`;
const okIcon = `<svg viewBox="0 0 24 24" aria-hidden="true" style="stroke:var(--good)"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>`;

export async function render(root, args) {
  const id = args[0];
  root.innerHTML = `
  <section style="display:flex;flex-wrap:wrap;gap:16px;align-items:center;justify-content:space-between">
    <div style="position:relative;flex:1 1 360px;max-width:520px">
      <label class="search">${icon("search")}<span class="sr">Search customers</span>
        <input id="q" type="text" autocomplete="off" placeholder="Search by customer number, for example C10000" value="${esc(id || "")}"></label>
      <div class="suggest" id="suggest" hidden></div>
    </div>
    <div class="chips"><span class="label" style="align-self:center">Jump to</span>
      <button class="chip" data-go="#/customer/C10000" style="cursor:pointer">C10000, guided demo</button></div>
  </section>
  <div id="body" style="display:contents"></div>`;
  wireSearch(root);
  if (!id) return renderHome($("#body", root));
  let c;
  try { c = await api.customer(id); } catch (e) {
    $("#body", root).innerHTML = `<div class="error"><b>No customer found for "${esc(id)}".</b><p class="note" style="margin-top:6px">Customer numbers look like C00001 to C20000. Try C10000.</p></div>`;
    return;
  }
  renderDetail($("#body", root), c);
}

function wireSearch(root) {
  const q = $("#q", root), box = $("#suggest", root);
  const close = () => { box.hidden = true; };
  const lookup = debounce(async () => {
    const t = q.value.trim();
    if (t.length < 2) return close();
    const res = await api.customers({ q: t, limit: 6, sort: "customer_id", descending: "false" });
    if (!res.rows.length) { box.innerHTML = `<div class="note" style="padding:10px 12px">No customer matches "${esc(t)}".</div>`; box.hidden = false; return; }
    box.innerHTML = res.rows.map((r) => `<button data-id="${r.customer_id}"><span class="strong">${r.customer_id}</span><span class="label">${esc(r.segment)}, churn risk ${pct(r.churn_risk)}</span></button>`).join("");
    box.hidden = false;
  }, 140);
  q.addEventListener("input", lookup);
  q.addEventListener("keydown", async (e) => {
    if (e.key === "Escape") close();
    if (e.key === "Enter") {
      const t = q.value.trim().toUpperCase();
      if (/^C\d{5}$/.test(t)) { close(); location.hash = "#/customer/" + t; }
      else { const first = box.querySelector("button"); if (first) { close(); location.hash = "#/customer/" + first.dataset.id; } }
    }
  });
  box.addEventListener("click", (e) => { const b = e.target.closest("button[data-id]"); if (b) { close(); location.hash = "#/customer/" + b.dataset.id; } });
  document.addEventListener("click", (e) => { if (!e.target.closest("#suggest") && e.target !== q) close(); });
}

async function renderHome(el) {
  const top = await api.customers({ segment: "Protect", limit: 8, sort: "revenue_at_risk_12m" });
  el.innerHTML = `
  <section class="panel">
    <h2>Look up any customer</h2>
    <p class="sub">See what the model expects, why a customer was flagged, and what to do next. Start with the guided demo customer, or pick someone from the list of customers with the most revenue at risk.</p>
    <div style="margin-top:18px">${btn("Open the guided demo customer", 'data-go="#/customer/C10000"')}</div>
  </section>
  <section class="panel">
    <div class="panel-head"><div><h2>Most revenue at risk right now</h2><p class="sub">High-value customers who are slipping away (the Protect segment).</p></div></div>
    <div class="table-wrap"><table><thead><tr><th>Customer</th><th class="r">At risk</th><th class="r">Churn risk</th><th>Why</th></tr></thead><tbody>
    ${top.rows.map((c) => `<tr class="link" data-id="${c.customer_id}"><td><a href="#/customer/${c.customer_id}" class="strong">${c.customer_id}</a></td><td class="r">${gbp(c.revenue_at_risk_12m)}</td><td class="r">${pct(c.churn_risk)}</td><td><div class="why">${esc(c.why)}</div></td></tr>`).join("")}
    </tbody></table></div>
  </section>`;
  el.querySelectorAll("tr.link").forEach((tr) => tr.addEventListener("click", () => { location.hash = "#/customer/" + tr.dataset.id; }));
}

function renderDetail(el, c) {
  const p = c.prediction, pr = c.profile, risky = c.segment === "Protect" || c.segment === "Win back";
  const whys = c.why.split("; ").filter(Boolean);
  const orders = c.orders;
  const last = orders[orders.length - 1];
  const avgGap = pr.avg_gap_days;

  el.innerHTML = `
  <section class="bezel"><div class="core">
    <div class="grid-2" style="grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:34px">
      <div style="display:grid;gap:18px;align-content:start">
        <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap"><p class="num lg">${c.customer_id}</p>${segPill(c.segment)}
          <span class="label">Number ${int(c.priority_rank)} of ${int(c.segment_size)} in ${esc(c.segment)} by revenue at risk</span></div>
        <p style="font-size:17px;line-height:1.55;max-width:60ch">${esc(c.summary)}</p>
        <div><p class="strong" style="margin-bottom:10px">${risky ? "Why this customer was flagged" : "Why this customer looks healthy"}</p>
          <ul class="list">${whys.map((w) => `<li>${risky ? warnIcon : okIcon}<span>${esc(w)}</span></li>`).join("")}</ul></div>
      </div>
      <div style="border-left:1px solid var(--line);padding-left:30px;display:grid;gap:14px;align-content:start">
        <p class="label">Recommended next step</p>
        <p style="font-size:21px;line-height:1.3;letter-spacing:-0.01em">${esc(c.recommended_action)}</p>
        <p class="note">${esc(c.play)}</p>
        <p class="note">Channel: <span style="color:var(--ink)">${esc(c.channel)}</span></p>
      </div>
    </div>
  </div></section>

  <section class="strip five">
    <div><p class="num lg">${pct(p.p_alive)}</p><p class="label" style="margin-top:8px">chance they are still an active customer</p></div>
    <div><p class="num lg">${gbp(p.clv_12m)}</p><p class="label" style="margin-top:8px">expected value, next 12 months (${gbp(p.clv_6m)} in 6 months)</p></div>
    <div><p class="num lg">${gbp(p.potential_clv_12m)}</p><p class="label" style="margin-top:8px">worth over 12 months if kept active</p></div>
    <div><p class="num lg ${risky ? "bad" : ""}">${gbp(p.revenue_at_risk_12m)}</p><p class="label" style="margin-top:8px">revenue at risk over 12 months</p></div>
    <div><p class="num lg" style="color:var(--ink-3)">${gbp(p.baseline_12m)}</p><p class="label" style="margin-top:8px">what a simple "same as before" forecast would say</p></div>
  </section>

  <section class="panel">
    <div class="panel-head"><div><h2>How likely is ${c.customer_id} to still be a customer?</h2>
      <p class="sub">The model's weekly view. Each tick on the bottom edge is a visit. After a visit the chance jumps back up, then it fades while the gap since the last visit keeps growing.</p></div>
      <div class="legend"><span><i class="sw" style="background:var(--s1)"></i>Chance still active</span><span><i class="sw" style="background:var(--ink-2)"></i>A visit</span></div></div>
    <div id="alive"></div>
  </section>

  <section class="grid-2e">
    <div class="panel">
      <div class="panel-head"><div><h2>Days between visits</h2><p class="sub">Their usual gap is about ${avgGap == null ? "n/a" : Math.round(avgGap)} days. Bars turn orange when a gap is more than 1.5 times the usual.</p></div></div>
      ${legend([{ name: "Normal gap", color: "var(--s1)" }, { name: "Much longer than usual", color: SEGMENTS.Protect.color }])}
      <div id="gaps" style="margin-top:6px"></div>
    </div>
    <div class="panel">
      <div class="panel-head"><div><h2>What they buy</h2><p class="sub">Total spend by category, all visits so far.</p></div></div>
      <div id="cats"></div>
      <p class="note" style="margin-top:10px">Peer check: the average ${esc(c.segment)} customer has ${int(Math.round(c.peer_average.n_orders))} visits, an average basket of ${gbp(c.peer_average.aov)} and a ${pct(c.peer_average.churn_risk)} churn risk. This customer has ${int(pr.n_orders)} visits, ${gbp(pr.aov)} and ${pct(p.churn_risk)}.</p>
    </div>
  </section>

  <section class="grid-2e" style="grid-template-columns:minmax(0,1.4fr) minmax(0,1fr)">
    <div class="panel">
      <div class="panel-head"><div><h2>Recent visits</h2></div></div>
      <div class="table-wrap"><table><thead><tr><th>Date</th><th>Store</th><th class="r">Spend</th><th class="r">Items</th><th class="r">Gap</th><th>Categories</th></tr></thead><tbody>
      ${orders.slice(-8).reverse().map((o) => `<tr><td class="nw">${fdate(o.date)}</td><td>${o.store_id}</td><td class="r">${gbp(o.amount, 2)}</td><td class="r">${o.items}</td><td class="r">${o.gap_days == null ? "first" : o.gap_days + " days"}</td><td><div class="why">${esc(o.categories)}</div></td></tr>`).join("")}
      </tbody></table></div>
    </div>
    <div class="panel">
      <div class="panel-head"><div><h2>Profile</h2></div></div>
      <div class="chips">
        <span class="chip">Age ${pr.age}, ${pr.gender === "F" ? "female" : pr.gender === "M" ? "male" : "other"}</span>
        <span class="chip">${esc(pr.country)}</span>
        <span class="chip">Customer for ${(pr.tenure_days / 365).toFixed(1)} years</span>
        <span class="chip">${pr.is_member ? "Loyalty member" : "Not a loyalty member"}</span>
        <span class="chip">${pr.app_installed ? "Has the app" : "No app"}</span>
        <span class="chip">${pr.email_subscribed ? "Gets marketing email" : "No marketing email"}</span>
        <span class="chip">${int(pr.n_orders)} visits, ${gbp(pr.total_spend)} spent</span>
        <span class="chip">${pct(pr.return_rate)} of items returned</span>
        ${pr.email_open_rate != null ? `<span class="chip">Email opens: ${pct(pr.email_open_rate_3m)} recently, ${pct(pr.email_open_rate)} overall</span>` : ""}
      </div>
      ${c.loyalty_uplift_12m_gbp != null ? `<p class="callout" style="margin-top:16px">If they joined the loyalty programme and behaved like members, the model sees about ${gbp(c.loyalty_uplift_12m_gbp)} extra value over 12 months.</p>` : ""}
    </div>
  </section>`;

  // ---- hero chart: chance still active
  const visitDates = orders.map((o) => +toDate(o.date));
  const lastTs = visitDates[visitDates.length - 1];
  lineChart($("#alive", el), {
    label: `Chance that ${c.customer_id} is still an active customer, by week`, height: 340,
    series: [{ name: "Chance still active", color: "var(--s1)", area: true, width: 2.5, values: c.alive_trajectory.map((t) => ({ x: +toDate(t.date), y: t.p_alive })) }],
    yMin: 0, yMax: 1, yTicks: 4, yFormat: (v) => Math.round(v * 100) + "%",
    refs: [{ y: 0.5, label: "50%: more likely gone than active" }],
    rug: visitDates,
    markers: [{ x: lastTs, label: `Last visit: ${fdate(last.date)}`, color: "var(--ink-2)" }],
    tooltip: (pts) => {
      const x = pts[0].x;
      let k = -1; for (let i = 0; i < visitDates.length; i++) if (visitDates[i] <= x) k = i;
      const since = k >= 0 ? Math.round((x - visitDates[k]) / 864e5) : null;
      return `<div class="t">${fdate(new Date(x).toISOString())}</div><div class="row">Chance still active: <b style="color:var(--ink)">${pct(pts[0].y)}</b></div>${since != null ? `<div class="row">${since} days since the last visit</div>` : ""}`;
    },
  });

  // ---- gaps
  const gaps = orders.filter((o) => o.gap_days != null);
  const short = (iso) => { const d = toDate(iso); return d.toLocaleDateString("en-GB", { month: "short", year: "2-digit", timeZone: "UTC" }).replace("Sept", "Sep"); };
  columnChart($("#gaps", el), {
    label: "Days between consecutive visits", height: 280, left: 44, categories: gaps.map((o) => short(o.date)), labelWidth: 64, maxBar: 14,
    yFormat: (v) => v + "d", yTicks: 4,
    ref: avgGap ? { y: avgGap, label: `Usual gap ${Math.round(avgGap)} days` } : null,
    series: [{ name: "Days since previous visit", color: "var(--s1)", colors: gaps.map((o) => (avgGap && o.gap_days > 1.5 * avgGap ? SEGMENTS.Protect.color : "var(--s1)")), values: gaps.map((o) => o.gap_days) }],
    tooltip: (i) => `<div class="t">${fdate(gaps[i].date)}</div><div class="row">${gaps[i].gap_days} days after the previous visit</div><div class="row">Spend: <b style="color:var(--ink)">${gbp(gaps[i].amount, 2)}</b></div>`,
  });

  // ---- categories
  $("#cats", el).innerHTML = hbars(c.categories.map((x) => ({ label: x.category, value: x.spend })), { format: (v) => gbp(v) });
}
