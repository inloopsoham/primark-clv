// Talks to the Python backend. Every answer is precomputed, so calls are instant.
const cache = new Map();

async function request(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) {
    let detail = "";
    try { detail = (await res.json()).detail || ""; } catch (_) { /* ignore */ }
    throw new Error(detail || `The server answered ${res.status} for ${url}`);
  }
  return res.json();
}

export function get(url, { fresh = false } = {}) {
  if (!fresh && cache.has(url)) return cache.get(url);
  const p = request(url);
  cache.set(url, p);
  p.catch(() => cache.delete(url));
  return p;
}

export const post = (url, body) =>
  request(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const api = {
  overview: () => get("/api/overview"),
  segments: () => get("/api/segments"),
  customers: (params = {}) => {
    const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ""));
    return get(`/api/customers?${q}`);
  },
  customer: (id) => get(`/api/customers/${encodeURIComponent(id)}`),
  loyalty: () => get("/api/loyalty"),
  simulate: (body) => post("/api/simulate", body),
  model: () => get("/api/model"),
};
