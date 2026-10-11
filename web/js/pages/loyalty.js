import { api } from "../api.js";
import { lineChart, legend } from "../charts.js";
import { esc, int, gbp, gbpShort, pctPts, debounce, $, $$ } from "../util.js";

export const lede = "What members do differently, and what enrolling more customers could be worth.";
export const title = "Loyalty programme";

export async function render(root) {
  const L = await api.loyalty();
  const m = L.members, n = L.non_members, b = L.behaviour;
  const d = L.assumptions;

  const rows = [
    ["Customers", int(m.customers), int(n.customers)],
    ["Average visits so far", m.avg_orders.toFixed(1), n.avg_orders.toFixed(1)],
    ["Average spend per visit", gbp(m.avg_spend_gbp, 0), gbp(n.avg_spend_gbp, 0)],
    ["Have the app installed", pctPts(m.app_installed_pct), pctPts(n.app_installed_pct)],
    ["Subscribed to email", pctPts(m.email_subscribed_pct), pctPts(n.email_subscribed_pct)],
    ["Visits per year while active", b.members.visits_per_year_if_active.toFixed(1), b.non_members.visits_per_year_if_active.toFixed(1)],
    ["Chance of leaving after each visit", pctPts(b.members.chance_of_leaving_after_each_visit_pct, 1), pctPts(b.non_members.chance_of_leaving_after_each_visit_pct, 1)],
    ["Expected value per customer, 12 months", gbp(m.avg_clv_12m_gbp), gbp(n.avg_clv_12m_gbp)],
  ];

  root.innerHTML = `
  <section class="panel">
    <h2>What members do differently</h2>
    <p class="sub" style="max-width:100ch">We fitted the visit model separately for members and non-members. Members visit about ${b.visit_rate_ratio.toFixed(2)} times as often while active and are ${((1 - b.leave_rate_ratio) * 100).toFixed(0)}% less likely to leave after a visit. Members are ${pctPts(m.customers_pct)} of customers and hold ${pctPts(m.clv_12m_share_pct)} of expected value.</p>
    <p class="callout" style="margin-top:14px;max-width:100ch">This is an association, not proof of cause. Keen shoppers may simply be the ones who join. The simulator below lets you decide how much of the gap you believe the programme itself creates.</p>
  </section>

  <section class="grid-2" style="grid-template-columns:minmax(0,1fr) minmax(0,1fr)">
    <div class="panel">
      <div class="panel-head"><div><h2>Members and non-members side by side</h2></div></div>
      <div class="table-wrap"><table>
        <thead><tr><th></th><th class="r">Members</th><th class="r">Non-members</th></tr></thead>
        <tbody>${rows.map(([k, a, c]) => `<tr><td>${k}</td><td class="r strong">${a}</td><td class="r">${c}</td></tr>`).join("")}</tbody>
      </table></div>
    </div>
    <div class="panel" style="display:grid;gap:22px;align-content:start">
      <div><h2>The size of the opportunity</h2>
        <p class="sub">${int(L.non_member_uplift.customers)} customers are not yet members. If every one of them behaved like a member, their expected 12-month value would rise by ${gbp(L.non_member_uplift.total_uplift_12m_gbp_if_all_enrolled_full_effect)} at most. That is the ceiling, before any doubt about cause.</p></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
        <div><p class="num md">${gbp(L.non_member_uplift.avg_uplift_12m_gbp, 2)}</p><p class="label" style="margin-top:6px">Average gain per enrolled customer, full effect</p></div>
        <div><p class="num md">${((L.non_member_uplift.avg_ratio_12m - 1) * 100).toFixed(0)}%</p><p class="label" style="margin-top:6px">Average lift in expected value</p></div>
      </div>
      <p class="note">Gains are largest for customers who already visit often, so enrolling them first pays back much faster than enrolling at random.</p>
    </div>
  </section>

  <section class="panel">
    <div class="panel-head">
      <div><h2>Loyalty simulator</h2><p class="sub">Move the sliders. Everything below updates.</p></div>
      <div class="tabs" role="tablist" id="mode"><button role="tab" data-v="targeted" aria-selected="true">Best customers first</button><button role="tab" data-v="random" aria-selected="false">Random customers</button></div>
    </div>
    <div class="grid-2" style="grid-template-columns:minmax(0,0.8fr) minmax(0,1.6fr);gap:34px;align-items:start">
      <div style="display:grid;gap:26px">
        ${slider("enrol", "Non-members we enrol", 0, 100, 5, 20, (v) => v + "%")}
        ${slider("causal", "Share of the gap the programme really causes", 0, 100, 5, Math.round(d.share_of_gap_that_is_causal_default * 100), (v) => v + "%")}
        ${slider("cost", "Cost to enrol one customer", 0, 5, 0.25, d.cost_per_enrolment_gbp_default, (v) => gbp(v, 2))}
        <p class="note" id="enrolled-note"></p>
      </div>
      <div style="display:grid;gap:20px">
        <div class="strip" id="result"></div>
        ${legend([{ name: "Best customers first", color: "var(--s1)" }, { name: "Random customers", color: "var(--s2)" }])}
        <div id="curve"></div>
        <p class="note" id="best-note"></p>
      </div>
    </div>
    <p class="note" style="margin-top:14px" id="sim-note"></p>
  </section>`;

  const state = { mode: "targeted" };
  let last = null;
  const read = () => ({
    enrol_pct: +$("#enrol", root).value, causal_share: +$("#causal", root).value / 100,
    cost_per_enrolment: +$("#cost", root).value, targeting: state.mode,
  });
  const labels = () => {
    $("#enrol-o", root).textContent = $("#enrol", root).value + "%";
    $("#causal-o", root).textContent = $("#causal", root).value + "%";
    $("#cost-o", root).textContent = gbp(+$("#cost", root).value, 2);
  };
  let seq = 0;
  async function run() {
    const mine = ++seq;
    const r = await api.simulate(read());
    if (mine !== seq) return;
    last = r;
    paint(r);
  }
  function paint(r) {
    const x = r.result;
    const cell = (v, l, cls = "") => `<div><p class="num lg ${cls}">${v}</p><p class="label" style="margin-top:8px">${l}</p></div>`;
    $("#result", root).innerHTML =
      cell(gbpShort(x.extra_clv_gbp), "Extra 12-month value") +
      cell(gbpShort(x.cost_gbp), "Cost of enrolling") +
      cell(gbpShort(x.net_gbp), "Net gain", x.net_gbp < 0 ? "bad" : "good") +
      cell(x.roi == null ? "n/a" : (x.roi + 1).toFixed(1) + "x", "Value back per £1 spent");
    $("#enrolled-note", root).textContent = `${int(x.enrolled)} of ${int(r.non_members)} non-members enrolled.`;
    $("#best-note", root).textContent = `With these assumptions, the best result for best-customers-first is to enrol ${r.best_targeted_enrol_pct}% of non-members, for a net gain of ${gbp(r.best_targeted_net_gbp)}.`;
    $("#sim-note", root).textContent = r.note;
    const cur = r.curve;
    const mk = (key) => cur.map((c) => ({ x: c.enrol_pct, y: c[key], c }));
    lineChart($("#curve", root), {
      label: "Net gain by share of non-members enrolled", height: 300, left: 64,
      yMin: Math.min(0, ...cur.map((c) => Math.min(c.targeted_net_gbp, c.random_net_gbp))) * 1.1,
      xMin: 0, xMax: 100, xTicks: [0, 20, 40, 60, 80, 100], yTicks: 6, xFormat: (v) => v + "%", yFormat: gbpShort,
      series: [
        { name: "Best customers first", color: "var(--s1)", width: 2, values: mk("targeted_net_gbp") },
        { name: "Random customers", color: "var(--s2)", width: 2, values: mk("random_net_gbp") },
      ],
      tooltip: (pts) => { const c = pts[0].c; return `<div class="t">${c.enrol_pct}% of non-members enrolled</div><div class="row"><i class="sw" style="background:var(--s1)"></i>Best first: <b style="color:var(--ink)">${gbp(c.targeted_net_gbp)}</b></div><div class="row"><i class="sw" style="background:var(--s2)"></i>Random: <b style="color:var(--ink)">${gbp(c.random_net_gbp)}</b></div>`; },
    });
  }
  const go = debounce(run, 120);
  $$("input[type=range]", root).forEach((el) => el.addEventListener("input", () => { labels(); go(); }));
  $("#mode", root).addEventListener("click", (e) => {
    const bt = e.target.closest("button[data-v]");
    if (!bt) return;
    state.mode = bt.dataset.v;
    $$("#mode button", root).forEach((x) => x.setAttribute("aria-selected", x === bt));
    run();
  });
  labels();
  await run();
}

function slider(id, label, min, max, step, val, fmt) {
  return `<div class="slider"><div class="slider-top"><label for="${id}">${label}</label><output id="${id}-o">${esc(fmt(val))}</output></div>
    <input type="range" id="${id}" min="${min}" max="${max}" step="${step}" value="${val}"></div>`;
}
