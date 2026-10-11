import { api } from "../api.js";
import { columnChart, hbars, legend } from "../charts.js";
import { esc, int, gbp, gbpShort, pct, fdate, debounce, $, $$ } from "../util.js";

export const lede = "How the numbers are made, and how well they match a year the model never saw.";
export const title = "Data and model";

const NAMES = { aov: "Average basket value", avg_items_per_order: "Items per basket", exp_visits_12m: "Expected visits, 12 months", exp_visits_6m: "Expected visits, 6 months", p_alive: "Chance still active", email_open_rate_3m: "Email opens, last 3 months", aov_std: "Basket value variation", avg_gap_days: "Average days between visits", overdue_ratio: "How overdue the next visit is", top_category: "Favourite category" };
const human = (f) => NAMES[f] || f.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
const TABLES = {
  customers: "People: age, home, region, favourite categories",
  transactions: "Every purchase basket, with items and spend",
  returns: "Items sent back, so spend is counted net of returns",
  loyalty: "Loyalty membership and join date",
  email_engagement: "Emails sent, opened and clicked",
};

export async function render(root) {
  const M = await api.model();
  const dict = Object.fromEntries(M.feature_dictionary.map((f) => [f.feature, f]));
  const st = { h: "12m" };
  const blendName = (h) => M.scorecard.find((r) => r.horizon === h && r.model_key === "blend");
  const base12 = M.scorecard.find((r) => r.horizon === "12m" && r.model_key === "baseline");
  const fin12 = blendName("12m");

  root.innerHTML = `
  <section class="panel">
    <h2>How the numbers are made</h2>
    <p class="sub" style="max-width:100ch">The model watches how often each customer shops and how long they have been quiet. A statistical visit model (BG/NBD) estimates the chance they are still active and how many visits to expect. Gradient boosting estimates what they spend on each visit. Multiplying the two gives the expected value. We then test it on a year the model never saw.</p>
    <div class="strip" style="margin-top:18px">
      <div><p class="num lg">${gbp(fin12.mae_gbp, 0)}</p><p class="label" style="margin-top:8px">Average miss per customer, 12 months. The baseline misses by ${gbp(base12.mae_gbp, 0)}.</p></div>
      <div><p class="num lg">${fin12.total_bias_pct > 0 ? "+" : ""}${fin12.total_bias_pct.toFixed(1)}%</p><p class="label" style="margin-top:8px">Total forecast vs actual. The baseline overshoots by ${base12.total_bias_pct.toFixed(0)}%.</p></div>
      <div><p class="num lg">${M.churn.auc_bgnbd.toFixed(2)}</p><p class="label" style="margin-top:8px">Churn detection score. Looking at days since last visit alone scores ${M.churn.auc_recency_only.toFixed(2)}.</p></div>
      <div><p class="num lg">${fin12.top10pct_captures_pct.toFixed(0)}%</p><p class="label" style="margin-top:8px">of next-year spend comes from the 10% of customers we rank highest. A perfect ranking would capture ${fin12.perfect_top10pct_captures_pct.toFixed(0)}%.</p></div>
    </div>
  </section>

  <section class="panel">
    <div class="panel-head">
      <div><h2>Scorecard against a held-out year</h2><p class="sub">Lower miss is better. The final model blends two approaches.</p></div>
      <div class="tabs" role="tablist" id="h-tabs"><button role="tab" data-h="6m" aria-selected="false">6 months</button><button role="tab" data-h="12m" aria-selected="true">12 months</button></div>
    </div>
    <div class="table-wrap" id="score"></div>
  </section>

  <section class="grid-2e">
    <div class="panel">
      <div class="panel-head"><div><h2>Does the forecast match reality?</h2><p class="sub">Customers sorted into ten equal groups from highest to lowest predicted 12-month spend. Average predicted against average actual.</p></div></div>
      ${legend([{ name: "Predicted", color: "var(--s1)" }, { name: "Actual", color: "var(--s2)" }])}
      <div id="cal" style="margin-top:8px"></div>
    </div>
    <div class="panel">
      <div class="panel-head"><div><h2>Visit counts</h2><p class="sub">Customers grouped by past repeat visits. Average visits predicted against what happened next year.</p></div></div>
      ${legend([{ name: "Predicted", color: "var(--s1)" }, { name: "Actual", color: "var(--s2)" }])}
      <div id="vis" style="margin-top:8px"></div>
    </div>
  </section>

  <section class="grid-2e">
    <div class="panel">
      <h2>What drives spend per visit</h2><p class="sub">Share of the basket model's decisions.</p>
      <div style="margin-top:14px">${hbars(M.importance_basket_model.slice(0, 8).map((r) => ({ label: human(r.feature), value: r.importance })), { format: (v) => pct(v, 0) })}</div>
    </div>
    <div class="panel">
      <h2>What drives 12-month value</h2><p class="sub">Share of the final spend model's decisions.</p>
      <div style="margin-top:14px">${hbars(M.importance_stacked_model_12m.slice(0, 8).map((r) => ({ label: human(r.feature), value: r.importance })), { format: (v) => pct(v, 0) })}</div>
    </div>
  </section>

  <section class="grid-2e">
    <div class="panel">
      <h2>Did the visit model learn the truth?</h2>
      <p class="sub">Because the data is synthetic we know the settings that produced it. The model, shown without access to them, lands close.</p>
      <div class="table-wrap" style="margin-top:12px"><table>
        <thead><tr><th>Setting</th><th class="r">Learned</th><th class="r">True</th></tr></thead>
        <tbody>${[["r", "Spread of visit rates (r)"], ["alpha", "Visit rate scale (alpha)"], ["a", "Leaving shape (a)"], ["b", "Leaving shape (b)"]].map(([k, n]) => `<tr><td>${n}</td><td class="r strong">${M.bgnbd_params_final[k].toFixed(2)}</td><td class="r">${M.bgnbd_true_values_in_generator[k].toFixed(2)}</td></tr>`).join("")}</tbody>
      </table></div>
      <p class="note" style="margin-top:12px">Against the hidden truth about who really left, the churn score is ${M.churn.auc_vs_hidden_truth.toFixed(2)}. Customers who truly left were given an average risk of ${pct(M.churn.avg_churn_risk_if_truly_left)}; those still active ${pct(M.churn.avg_churn_risk_if_truly_active)}.</p>
    </div>
    <div class="panel">
      <h2>The data</h2>
      <p class="sub">Everything here is synthetic. It is modelled on Primark-style UK and Ireland shopping behaviour and contains no real customers. Period ${fdate("2023-10-01")} to ${fdate(M.data_summary.as_of)}.</p>
      <div class="table-wrap" style="margin-top:12px"><table>
        <thead><tr><th>Table</th><th>What it holds</th><th class="r">Rows</th></tr></thead>
        <tbody>${Object.entries(TABLES).map(([k, v]) => `<tr><td class="strong">${k}</td><td>${v}</td><td class="r">${int(M.tables[k])}</td></tr>`).join("")}</tbody>
      </table></div>
    </div>
  </section>

  <section class="panel">
    <div class="panel-head">
      <div><h2>Data dictionary</h2><p class="sub">${M.feature_dictionary.length} measures the model can use for each customer.</p></div>
      <div class="search" style="min-width:260px"><input id="dq" type="search" placeholder="Search measures" aria-label="Search measures"></div>
    </div>
    <div class="table-wrap" style="max-height:420px;overflow:auto"><table><thead><tr><th>Measure</th><th>Group</th><th>Meaning</th></tr></thead><tbody id="dict"></tbody></table></div>
  </section>`;

  const drawScore = () => {
    const rows = M.scorecard.filter((r) => r.horizon === st.h);
    const best = Math.min(...rows.map((r) => r.mae_gbp));
    $("#score", root).innerHTML = `<table><thead><tr><th>Approach</th><th class="r">Average miss</th><th class="r">Total vs actual</th><th class="r">Ranking quality</th><th class="r">Top 10% captures</th></tr></thead><tbody>${rows.map((r) =>
      `<tr><td class="${r.model_key === "blend" ? "strong" : ""}">${esc(r.model)}${r.model_key === "blend" ? " (used in the app)" : ""}</td><td class="r ${r.mae_gbp === best ? "good strong" : ""}">${gbp(r.mae_gbp, 2)}</td><td class="r">${r.total_bias_pct > 0 ? "+" : ""}${r.total_bias_pct.toFixed(1)}%</td><td class="r">${r.rank_correlation.toFixed(2)}</td><td class="r">${r.top10pct_captures_pct.toFixed(0)}%</td></tr>`).join("")}</tbody></table>`;
  };
  drawScore();
  $("#h-tabs", root).addEventListener("click", (e) => {
    const b = e.target.closest("button[data-h]");
    if (!b) return;
    st.h = b.dataset.h;
    $$("#h-tabs button", root).forEach((x) => x.setAttribute("aria-selected", x === b));
    drawScore();
  });

  const cal = M.calibration_deciles_12m;
  columnChart($("#cal", root), {
    label: "Predicted against actual spend by decile", height: 280, left: 54, categories: cal.map((c) => String(c.decile)), yFormat: gbpShort, maxBar: 18, labelWidth: 24,
    series: [{ name: "Predicted", color: "var(--s1)", values: cal.map((c) => c.predicted_avg) }, { name: "Actual", color: "var(--s2)", values: cal.map((c) => c.actual_avg) }],
    tooltip: (i) => { const c = cal[i]; return `<div class="t">Group ${c.decile} of 10${c.decile === 1 ? " (highest predicted)" : c.decile === 10 ? " (lowest predicted)" : ""}</div><div class="row">Customers: <b style="color:var(--ink)">${int(c.customers)}</b></div><div class="row">Predicted: <b style="color:var(--ink)">${gbp(c.predicted_avg, 2)}</b></div><div class="row">Actual: <b style="color:var(--ink)">${gbp(c.actual_avg, 2)}</b></div>`; },
  });
  const vc = M.visits_calibration_12m;
  columnChart($("#vis", root), {
    label: "Predicted against actual visits by past repeat visits", height: 280, left: 40, categories: vc.map((c) => c.repeat_visits), yFormat: (v) => v, maxBar: 18, labelWidth: 30,
    series: [{ name: "Predicted", color: "var(--s1)", values: vc.map((c) => c.predicted) }, { name: "Actual", color: "var(--s2)", values: vc.map((c) => c.actual) }],
    tooltip: (i) => { const c = vc[i]; return `<div class="t">${esc(c.repeat_visits)} past repeat visits</div><div class="row">Customers: <b style="color:var(--ink)">${int(c.customers)}</b></div><div class="row">Predicted visits: <b style="color:var(--ink)">${c.predicted.toFixed(2)}</b></div><div class="row">Actual visits: <b style="color:var(--ink)">${c.actual.toFixed(2)}</b></div>`; },
  });

  const drawDict = (q = "") => {
    const s = q.trim().toLowerCase();
    const rows = M.feature_dictionary.filter((f) => !s || (f.feature + f.group + f.description).toLowerCase().includes(s));
    $("#dict", root).innerHTML = rows.length
      ? rows.map((f) => `<tr><td class="strong">${esc(f.feature)}</td><td>${esc(f.group)}</td><td>${esc(f.description)}</td></tr>`).join("")
      : `<tr><td colspan="3" class="note">No measure matches "${esc(q)}". Try a shorter word.</td></tr>`;
  };
  drawDict();
  $("#dq", root).addEventListener("input", debounce((e) => drawDict(e.target.value), 100));
}
