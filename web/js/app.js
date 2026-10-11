// App shell: hash router, page title, error handling.
import { $, $$, esc, hideTip } from "./util.js";

const routes = {
  overview: () => import("./pages/overview.js"),
  segments: () => import("./pages/segments.js"),
  customer: () => import("./pages/customer.js"),
  loyalty: () => import("./pages/loyalty.js"),
  model: () => import("./pages/model.js"),
};

const view = $("#view");

// Light is the default. The switch remembers the choice on this browser.
const themeBtn = $("#theme");
function setTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  themeBtn.setAttribute("aria-checked", String(t === "dark"));
  try { localStorage.setItem("clv-theme", t); } catch (_) { /* private window: ignore */ }
}
themeBtn.setAttribute("aria-checked", String(document.documentElement.getAttribute("data-theme") === "dark"));
themeBtn.addEventListener("click", () => setTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark"));
let token = 0;

async function navigate() {
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const name = parts[0] || "overview";
  const key = routes[name] ? name : "overview";
  const args = parts.slice(1).map(decodeURIComponent);
  const mine = ++token;
  hideTip();
  $$(".nav a").forEach((a) => (a.getAttribute("href") === "#/" + key ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current")));
  view.innerHTML = `<div class="loading">Loading...</div>`;
  try {
    const page = await routes[key]();
    const holder = document.createElement("div");
    holder.className = "content-inner";
    holder.style.display = "contents";
    if (mine !== token) return;
    view.replaceChildren(holder);
    view.classList.toggle("bleed", key === "overview");
    if (key !== "overview") {
      const head = document.createElement("div");
      head.className = "page-head";
      head.innerHTML = `<h1>${esc(page.title)}</h1>${page.lede ? `<p>${esc(page.lede)}</p>` : ""}`;
      view.prepend(head);
    }
    document.title = `${page.title} | Customer lifetime value (synthetic data)`;
    await page.render(holder, args);
    if (mine === token) window.scrollTo({ top: 0 });
  } catch (err) {
    if (mine !== token) return;
    console.error(err);
    view.innerHTML = `<div class="error"><b>Something went wrong loading this page.</b><p class="note" style="margin-top:6px">${esc(err.message)}</p><p class="note" style="margin-top:6px">Check that the server is still running in the terminal, then reload.</p></div>`;
  }
}

document.addEventListener("click", (e) => {
  const go = e.target.closest("[data-go]");
  if (go) { e.preventDefault(); location.hash = go.dataset.go; }
});
window.addEventListener("hashchange", navigate);
navigate();
