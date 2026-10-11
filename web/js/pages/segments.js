import { api } from "../api.js";
import { columnChart, legend } from "../charts.js";
import { SEGMENTS, SEG_ORDER, esc, int, gbp, gbpShort, pctPts, pct, segPill, $, $$ } from "../util.js";

export const lede = "Four groups of customers, each with its own play and its own return.";
export const title = "Segments and actions";

const CUT_TABS = [["region", "Region"], ["country", "Country"], ["top_category", "Favourite category"], ["age_band", "Age"], ["loyalty_status", "Loyalty"]];

export async function render(root, args) {
  const data = await api.segments();
  const byName = Object.fromEntries(data.segments.map((s) => [s.segment, s]));
  const current = SEG_ORDER.includes(args[0]) ? args[0] : "Protect";
  const r = data.rules;

  root.innerHTML = `
  <section class="panel">
    <h2>How customers are grouped</h2>
    <p class="sub" style="max-width:100ch">Every customer is placed on two questions. How much would they be worth over 12 months if we keep them active? And how likely is it that they have already drifted away? High value means ${gbp(r.high_value_cutoff_potential_12m_gbp)} or more, the top ${Math.round(r.high_value_top_share * 100)}% of customers. High risk means a ${Math.round(r.high_risk_cutoff * 100)}% or higher chance of having drifted.</p>
  </section>

  <section class="grid-2e" style="grid-template-columns:repeat(4,minmax(0,1fr));gap:16px" id="tiles">
    ${SEG_ORDER.map((n) => tile(byName[n], n === current)).join("")}
  </section>

  <section id="detail"></section>

  <section class="panel">
    <div class="panel-head">
      <div><h2>Where the value sits</h2><p class="sub">Expected 12-month value and revenue at risk, by group. Both are in pounds on one scale.</p></div>
      <div class="tabs" role="tablist" id="cut-tabs">${CUT_TABS.map(([k, l], i) => `<button role="tab" data-k="${k}" aria-selected="${i === 0}">${l}</button>`).join("")}</div>
    </div>
    ${legend([{ name: "Expected value, 12 months", color: "var(--s1)" }, { name: "Revenue at risk, 12 months", color: "var(--s2)" }])}
    <div id="cut-chart" style="margin-top:8px"></div>
  </section>

  <p class="note">${esc(data.note)}</p>`;

  $("#tiles", root).addEventListener("click", (e) => {
    const t = e.target.closest("[data-seg]");
    if (t) location.hash = "#/segments/" + encodeURIComponent(t.dataset.seg);
  });

  await renderDetail($("#detail", root), byName[current]);

  const drawCut = (k) => {
    const rows = data.cuts[k];
    columnChart($("#cut-chart", root), {
      label: "Value and revenue at risk by group", height: 300, left: 60, categories: rows.map((x) => x.group),
      yFormat: gbpShort, labelWidth: 90, maxBar: 34,
      series: [{ name: "Expected value", color: "var(--s1)", values: rows.map((x) => x.clv_12m) }, { name: "Revenue at risk", color: "var(--s2)", values: rows.map((x) => x.revenue_at_risk_12m) }],
      tooltip: (i) => { const x = rows[i]; return `<div class="t">${esc(x.group)}</div><div class="row">Customers: <b style="color:var(--ink)">${int(x.customers)}</b></div><div class="row">Expected value: <b style="color:var(--ink)">${gbp(x.clv_12m)}</b></div><div class="row">Revenue at risk: <b style="color:var(--ink)">${gbp(x.revenue_at_risk_12m)}</b></div><div class="row">Average churn risk: <b style="color:var(--ink)">${pct(x.avg_churn_risk)}</b></div>`; },
    });
  };
  drawCut("region");
  $("#cut-tabs", root).addEventListener("click", (e) => {
    const b = e.target.closest("button[data-k]");
    if (!b) return;
    $$("#cut-tabs button", root).forEach((x) => x.setAttribute("aria-selected", x === b));
    drawCut(b.dataset.k);
  });
}

function tile(s, active) {
  const c = SEGMENTS[s.segment].color;
  return `<button data-seg="${esc(s.segment)}" class="panel" aria-pressed="${active}" style="text-align:left;cursor:pointer;border-top:3px solid ${c};padding:18px 20px;${active ? `background:var(--accent-dim);box-shadow:inset 0 0 0 1px var(--accent-line)` : ""}">
    <div style="display:flex;align-items:center;gap:8px;font-weight:600"><i class="sw ${SEGMENTS[s.segment].key}"></i>${esc(s.segment)}</div>
    <p class="num lg" style="margin-top:14px">${int(s.customers)}</p>
    <p class="label" style="margin-top:6px">customers, ${pctPts(s.customers_pct)} of the base</p>
    <p style="margin-top:14px;font-size:14px;color:var(--ink-2)">${gbpShort(s.clv_12m_gbp)} expected value<br>${gbpShort(s.revenue_at_risk_12m_gbp)} at risk</p>
  </button>`;
}

async function renderDetail(el, s) {
  const list = await api.customers({ segment: s.segment, limit: 10, sort: "revenue_at_risk_12m" });
  const a = s.assumptions;
  const eco = [];
  if (a.save_rate) eco.push(["Customers kept or won back", pctPts(a.save_rate * 100) + " of revenue at risk"]);
  if (a.upside_rate) eco.push(["Extra spend from rewards", pctPts(a.upside_rate * 100) + " of expected value"]);
  eco.push(["Cost to contact one customer", gbp(a.cost_contact, 2)]);
  if (a.offer_cost) eco.push(["Offer or reward cost", pctPts(a.offer_cost * 100) + " of the gain"]);
  el.innerHTML = `
  <div class="grid-2" style="grid-template-columns:minmax(0,1fr) minmax(0,1.3fr)">
    <div class="panel" style="display:grid;gap:20px;align-content:start">
      <div><div style="display:flex;align-items:center;gap:12px">${segPill(s.segment)}<span class="label">${esc(s.goal)}</span></div>
        <p style="margin-top:14px;color:var(--ink-2);font-size:15px">${esc(s.play)}</p></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div><p class="label">Channel</p><p>${esc(s.channel)}</p></div>
        <div><p class="label">Measure of success</p><p>${esc(s.kpi)}</p></div>
        <div><p class="label">Average churn risk</p><p>${pctPts(s.avg_churn_risk_pct)}</p></div>
        <div><p class="label">Loyalty members</p><p>${pctPts(s.loyalty_member_pct)}</p></div>
        <div><p class="label">Average age</p><p>${s.avg_age.toFixed(0)}</p></div>
        <div><p class="label">Average visits so far</p><p>${s.avg_orders.toFixed(1)}</p></div>
        <div style="grid-column:1/-1"><p class="label">Most common favourite categories</p><div class="chips" style="margin-top:6px">${s.top_categories.map((c) => `<span class="chip">${esc(c)}</span>`).join("")}</div></div>
      </div>
      <div>
        <p class="strong" style="margin-bottom:8px">Campaign economics <span class="label" style="font-weight:400">(illustrative assumptions)</span></p>
        <table><tbody>${eco.map(([k, v]) => `<tr><td>${k}</td><td class="r">${v}</td></tr>`).join("")}
          <tr><td>Expected gain</td><td class="r strong">${gbp(s.expected_gain_gbp)}</td></tr>
          <tr><td>Campaign cost</td><td class="r">${gbp(s.campaign_cost_gbp)}</td></tr>
          <tr><td>Return on spend</td><td class="r strong ${s.roi > 0 ? "good" : ""}">${s.roi == null ? "n/a" : s.roi.toFixed(1) + "x"}</td></tr></tbody></table>
      </div>
    </div>
    <div class="panel">
      <div class="panel-head"><div><h2>Where to start in ${esc(s.segment)}</h2><p class="sub">The ${list.rows.length} customers with the most revenue at risk. Open any row for the full story.</p></div></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Customer</th><th class="r">At risk</th><th class="r">Churn risk</th><th class="r">Last visit</th><th>Why</th></tr></thead>
        <tbody>${list.rows.map((c) => `<tr class="link" data-id="${c.customer_id}"><td><a href="#/customer/${c.customer_id}" class="strong">${c.customer_id}</a></td><td class="r">${gbp(c.revenue_at_risk_12m)}</td><td class="r">${pct(c.churn_risk)}</td><td class="r">${int(c.recency_days)} days ago</td><td><div class="why">${esc(c.why)}</div></td></tr>`).join("")}</tbody>
      </table></div>
    </div>
  </div>`;
  el.querySelectorAll("tr.link").forEach((tr) => tr.addEventListener("click", () => { location.hash = "#/customer/" + tr.dataset.id; }));
}
