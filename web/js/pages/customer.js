import { api } from "../api.js";
import { lineChart, columnChart, hbars, legend } from "../charts.js";
import { SEGMENTS, esc, int, gbp, gbpShort, pct, pctPts, fdate, toDate, segPill, icon, btn, debounce, $ } from "../util.js";

export const lede = "Look up any customer and see why the model flagged them and what to do next.";
export const title = "Customer lookup";

// The two guided-demo customers: same warning sign, different decision.
const FEATURED = [
  { id: "C10000", tag: "High value", who: "Loyal family shopper, Manchester", label: "A loyal family shopper." },
  { id: "C10001", tag: "Low value", who: "Occasional small-basket shopper, Leeds", label: "An occasional shopper." },
];
const isFeatured = (id) => FEATURED.some((f) => f.id === id);

const warnIcon = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17.2v.1"/></svg>`;
const okIcon = `<svg viewBox="0 0 24 24" aria-hidden="true" style="stroke:var(--good)"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>`;

export async function render(root, args) {
  const id = args[0];
  root.innerHTML = `
  <section style="display:flex;flex-wrap:wrap;gap:16px;align-items:center;justify-content:space-between">
    <div style="position:relative;flex:1 1 360px;max-width:520px">
      <label class="search">${icon("search")}<span class="sr">Search customers</span>
        <input id="q" type="text" autocomplete="off" placeholder="Search by customer number, for example C10000 or C10001" value="${esc(id || "")}"></label>
      <div class="suggest" id="suggest" hidden></div>
    </div>
    <div class="chips"><span class="label" style="align-self:center">Jump to</span>
      ${FEATURED.map((f) => `<button class="chip" data-go="#/customer/${f.id}" style="cursor:pointer${f.id === id ? ";box-shadow:inset 0 0 0 1.5px var(--ink)" : ""}">${f.id}, ${f.tag.toLowerCase()}</button>`).join("")}</div>
  </section>
  <div id="body" style="display:contents"></div>`;
  wireSearch(root);
  if (!id) return renderHome($("#body", root));
  let c;
  try { c = await api.customer(id); } catch (e) {
    $("#body", root).innerHTML = `<div class="error"><b>No customer found for "${esc(id)}".</b><p class="note" style="margin-top:6px">Customer numbers look like C00001 to C20000. Try C10000 or C10001.</p></div>`;
    return;
  }
  renderDetail($("#body", root), c);
  if (isFeatured(c.customer_id)) {
    const sec = document.createElement("section");
    sec.className = "panel";
    $("#body", root).append(step5(), sec);
    renderCompare(sec, c.customer_id);
  }
}

const step5 = () => { const d = document.createElement("div"); d.innerHTML = `<div style="display:flex;align-items:baseline;gap:14px;margin:6px 2px -4px"><span class="num" style="font-size:15px;color:var(--ink-3)">5</span><div><h2 style="font-size:22px">Compared with another drifting customer</h2></div></div>`; return d.firstElementChild; };

// ---- side by side: two drifting customers, two different decisions
async function renderCompare(el, current) {
  const cs = await Promise.all(FEATURED.map((f) => api.customer(f.id).catch(() => null)));
  if (cs.some((x) => !x)) { el.remove(); return; }
  const col = (c, f) => {
    const p = c.prediction, k = c.campaign, on = c.customer_id === current;
    const row = (label, value, big = false) => `<div style="display:grid;gap:4px"><span class="label">${label}</span><span style="${big ? "font-size:40px;font-weight:700;letter-spacing:-0.02em;line-height:1" : "font-size:18px;font-weight:600"}">${value}</span></div>`;
    return `<div style="display:grid;gap:18px;align-content:start;padding:24px;border-radius:20px;${on ? "background:var(--fill);box-shadow:inset 0 0 0 1.5px var(--line)" : "box-shadow:inset 0 0 0 1px var(--line)"}">
      <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
        <a href="#/customer/${c.customer_id}" class="num md" style="color:var(--ink)">${c.customer_id}</a>${segPill(c.segment)}<span class="label">${f.tag}</span></div>
      <p class="note" style="margin-top:-8px">${esc(f.who)}</p>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
        ${row("Chance she has drifted", pct(p.churn_risk), true)}
        ${row("Worth next year if she stays", gbp(p.potential_clv_12m), true)}
      </div>
      ${row("Recommended next step", esc(c.recommended_action))}
      <p class="note" style="margin-top:-10px">Channel: <span style="color:var(--ink)">${esc(c.channel)}</span></p>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px;padding-top:14px;border-top:1px solid var(--line)">
        ${row("Expected back", gbp(k.expected_gain_gbp, 2))}
        ${row("What we would spend", gbp(k.expected_cost_gbp, 2))}
      </div>
    </div>`;
  };
  el.innerHTML = `
    <div class="panel-head"><div><h2>Same warning sign, different decision</h2>
      <p class="sub">Both customers are drifting away. The model tells us how much each one is worth keeping, so the spend follows the value.</p></div></div>
    <div class="grid-2" style="grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px;margin-top:6px">${cs.map((c, i) => col(c, FEATURED[i])).join("")}</div>
    <p style="margin-top:18px;font-size:18px;font-weight:600">Not every customer deserves the same pound.</p>
    <p class="note" style="margin-top:4px">Expected back and spend use the same illustrative save rates and costs as the Segments page.</p>`;
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
  const cmp = document.createElement("section"); cmp.className = "panel";
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
  el.firstElementChild.after(cmp);
  renderCompare(cmp, null);
}

// ---- step 1: who she is (identity sentence, four facts, how we can reach her)
const ICONS = {
  member: `<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>`,
  app: `<rect x="6" y="2.5" width="12" height="19" rx="3"/><path d="M11 18h2"/>`,
  email: `<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M3.5 6.5l8.5 6 8.5-6"/>`,
};
function whoCard(c, pr, her) {
  const years = pr.tenure_days / 365;
  const yrs = years.toFixed(1);
  const f = FEATURED.find((x) => x.id === c.customer_id);
  const fav = c.categories.length ? c.categories[0].category : "";
  const gap = pr.avg_gap_days;
  const habit = [fav ? `Mostly ${esc(fav)}` : "", gap ? `about every ${Math.round(gap)} days` : ""].filter(Boolean).join(", ");
  const first = c.orders.length ? toDate(c.orders[0].date) : null;
  const since = first ? first.toLocaleDateString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" }) : "";
  // Ring: a full circle is 3 years, the longest history in the data.
  const C = 2 * Math.PI * 60, frac = Math.max(0.02, Math.min(1, pr.tenure_days / 1096));
  const ring = `<div class="who-ring" role="img" aria-label="Customer for ${yrs} years">
    <svg viewBox="0 0 132 132" width="132" height="132" fill="none" stroke-width="6" aria-hidden="true"><circle cx="66" cy="66" r="60" class="track" fill="none" stroke="rgba(128,128,128,.18)"/>
      <circle cx="66" cy="66" r="60" class="arc" fill="none" stroke="currentColor" stroke-linecap="round" stroke-dasharray="${C.toFixed(1)}" stroke-dashoffset="${(C * (1 - frac)).toFixed(1)}" transform="rotate(-90 66 66)"/></svg>
    <div class="in"><b>${yrs}</b><span>years with<br>Primark</span></div></div>`;
  const fact = (v, l) => `<div class="who-fact"><b>${v}</b><span>${l}</span></div>`;
  const tile = (on, ic, t, s) => `<div class="who-tile${on ? "" : " off"}"><span class="ic"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">${ICONS[ic]}</svg></span><div><p class="t">${t}</p><p class="s">${s}</p></div></div>`;
  const o3 = pr.email_open_rate_3m, oAll = pr.email_open_rate;
  const falling = o3 != null && oAll != null && o3 < oAll - 0.02;
  const opens = o3 == null ? "No opens recorded yet"
    : `Opens <span class="${falling ? "who-down" : ""}">${pct(o3)}</span> lately${oAll != null ? `, was ${pct(oAll)}` : ""}`;
  return `<section class="bezel"><div class="core who">
    <div class="who-top">${ring}
      <div><p class="who-id">Customer ${c.customer_id}${since ? ` · first visit ${since}` : ""}</p>
        <p class="who-line">${pr.age}, ${esc(pr.city || pr.country)}.${f ? ` ${esc(f.label)}` : ""}${habit ? ` <span>${habit}.</span>` : ""}</p></div></div>
    <div class="who-facts">
      ${fact(int(pr.n_orders), `visits in ${years < 1.05 ? "the last year" : yrs + " years"}`)}
      ${fact(gbp(pr.total_spend), "spent in total")}
      ${fact(gbp(pr.aov), "a typical basket")}
      ${fact(pct(pr.return_rate), "of items returned")}
    </div>
    <div class="who-tiles">
      ${pr.is_member ? tile(true, "member", "Loyalty member", `We know ${her} by name`) : tile(false, "member", "Not a member", `Known only by ${her} card`)}
      ${pr.app_installed ? tile(true, "app", "Has the app", `We can reach ${her} with a notification`) : tile(false, "app", "No app", "No notifications possible")}
      ${pr.email_subscribed ? tile(true, "email", "Gets our emails", opens) : tile(false, "email", "No marketing email", "Not opted in")}
    </div>
  </div></section>`;
}

function renderDetail(el, c) {
  const p = c.prediction, pr = c.profile, risky = c.segment === "Protect" || c.segment === "Win back";
  const whys = c.why.split("; ").filter(Boolean);
  const orders = c.orders;
  const last = orders[orders.length - 1];
  const avgGap = pr.avg_gap_days;

  const step = (n, title, sub) => `<div style="display:flex;align-items:baseline;gap:14px;margin:6px 2px -4px"><span class="num" style="font-size:15px;color:var(--ink-3)">${n}</span><div><h2 style="font-size:22px">${title}</h2>${sub ? `<p class="sub">${sub}</p>` : ""}</div></div>`;
  const she = pr.gender === "M" ? "he" : "she", her = pr.gender === "M" ? "his" : "her", Her = her[0].toUpperCase() + her.slice(1);
  const fav = c.categories.length ? c.categories[0].category : "";
  el.innerHTML = `
  ${step("1", `Who ${she} is`, "The facts we already hold about this customer.")}
  ${whoCard(c, pr, her)}

  ${step("2", `How ${she} shops`, `${Her} visits and baskets, straight from the till data.`)}
  <section class="grid-2e">
    <div class="panel">
      <div class="panel-head"><div><h2>Days between visits</h2><p class="sub">${Her} usual gap is about ${avgGap == null ? "n/a" : Math.round(avgGap)} days. Bars turn orange when a gap is more than 1.5 times the usual.</p></div></div>
      ${legend([{ name: "Normal gap", color: "var(--s1)" }, { name: "Much longer than usual", color: SEGMENTS.Protect.color }])}
      <div id="gaps" style="margin-top:6px"></div>
    </div>
    <div class="panel">
      <div class="panel-head"><div><h2>What ${she} buys</h2><p class="sub">Total spend by category, all visits so far.</p></div></div>
      <div id="cats"></div>
      <div class="table-wrap" style="margin-top:14px"><table><thead><tr><th>Last visits</th><th class="r">Spend</th><th class="r">Gap</th></tr></thead><tbody>
      ${orders.slice(-4).reverse().map((o) => `<tr><td class="nw">${fdate(o.date)}</td><td class="r">${gbp(o.amount, 2)}</td><td class="r">${o.gap_days == null ? "first" : o.gap_days + " days"}</td></tr>`).join("")}
      </tbody></table></div>
    </div>
  </section>

  ${step("3", "What the model sees", `From ${her} history alone: is ${she} still with us, and what is ${she} worth?`)}
  <section class="panel">
    <div class="panel-head"><div><h2>How likely is ${c.customer_id} to still be a customer?</h2>
      <p class="sub">Each tick on the bottom edge is a visit. After a visit the chance jumps back up, then it fades while the gap since the last visit keeps growing.</p></div>
      <div class="legend"><span><i class="sw" style="background:var(--s1)"></i>Chance still active</span><span><i class="sw" style="background:var(--ink-2)"></i>A visit</span></div></div>
    <div id="alive"></div>
  </section>
  <section class="strip five">
    <div><p class="num lg">${pct(p.p_alive)}</p><p class="label" style="margin-top:8px">chance ${she} is still an active customer</p></div>
    <div><p class="num lg">${gbp(p.potential_clv_12m)}</p><p class="label" style="margin-top:8px">worth over 12 months if ${she} stays</p></div>
    <div><p class="num lg">${gbp(p.clv_12m)}</p><p class="label" style="margin-top:8px">expected value, next 12 months (${gbp(p.clv_6m)} in 6 months)</p></div>
    <div><p class="num lg ${risky ? "bad" : ""}">${gbp(p.revenue_at_risk_12m)}</p><p class="label" style="margin-top:8px">revenue at risk over 12 months</p></div>
    <div><p class="num lg" style="color:var(--ink-3)">${gbp(p.baseline_12m)}</p><p class="label" style="margin-top:8px">what a simple "same as before" forecast would say</p></div>
  </section>

  ${step("4", "What we do about it", "")}
  <section class="bezel"><div class="core">
    <div class="grid-2" style="grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:34px">
      <div style="display:grid;gap:18px;align-content:start">
        <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap">${segPill(c.segment)}
          <span class="label">Number ${int(c.priority_rank)} of ${int(c.segment_size)} in ${esc(c.segment)} by revenue at risk</span></div>
        <p style="font-size:17px;line-height:1.55;max-width:60ch">${esc(c.summary)}</p>
        <div><p class="strong" style="margin-bottom:10px">${risky ? `Why ${she} was flagged` : `Why ${she} looks healthy`}</p>
          <ul class="list">${whys.map((w) => `<li>${risky ? warnIcon : okIcon}<span>${esc(w)}</span></li>`).join("")}</ul></div>
      </div>
      <div style="border-left:1px solid var(--line);padding-left:30px;display:grid;gap:14px;align-content:start">
        <p class="label">Recommended next step</p>
        <p style="font-size:21px;line-height:1.3;letter-spacing:-0.01em">${esc(c.recommended_action)}</p>
        <p class="note">${esc(c.play)}</p>
        <p class="note">Channel: <span style="color:var(--ink)">${esc(c.channel)}</span></p>
      </div>
    </div>
  </div></section>`;

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
