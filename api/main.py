"""
main.py - the web server (FastAPI).

Start it from the project root:

    uvicorn api.main:app --reload

then open  http://127.0.0.1:8000        (the app, once the front end exists)
       and http://127.0.0.1:8000/docs   (a built-in page to try every endpoint)

Everything is served from precomputed results, so it works offline and
responds instantly. All data is synthetic.
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from api.service import SEGMENTS, Store
from src import config as C

WEB_DIR = C.ROOT / "web"

app = FastAPI(
    title="Primark CLV - customer lifetime value (synthetic data)",
    description="Demo API. All data is synthetic and modelled on Primark-style retail behaviour.",
    version="1.0",
)
store = Store()


@app.middleware("http")
async def no_stale_front_end(request, call_next):
    """Make the browser re-check page files on every load, so code updates show up without a hard refresh."""
    response = await call_next(request)
    if not request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-cache"
    return response


# ----------------------------------------------------------------------------
# API
# ----------------------------------------------------------------------------
@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok", "customers": int(len(store.seg)), "as_of": store.summary["as_of"],
            "data": "synthetic"}


@app.get("/api/overview", tags=["pages"])
def overview():
    """Executive overview: headline numbers, segments, sales history, charts."""
    return store.overview()


@app.get("/api/segments", tags=["pages"])
def segments():
    """The four action segments, their campaigns and breakdowns by region, category, age."""
    return store.segments()


@app.get("/api/customers", tags=["customers"])
def customers(
    segment: str | None = Query(None, description="Protect, Grow, Win back or Maintain"),
    region: str | None = Query(None, description="UK, Ireland or Europe"),
    member: int | None = Query(None, description="1 = loyalty members, 0 = non-members"),
    q: str | None = Query(None, description="part of a customer id, e.g. C1000"),
    sort: str = Query("revenue_at_risk_12m"),
    descending: bool = Query(True),
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Searchable, sortable customer list (also powers the segment lists)."""
    if segment is not None and segment not in SEGMENTS:
        raise HTTPException(400, f"segment must be one of {SEGMENTS}")
    return store.list_customers(segment, region, member, q, sort, descending, limit, offset)


@app.get("/api/customers/{customer_id}", tags=["customers"])
def customer(customer_id: str):
    """Everything about one customer: prediction, reasons, history, how 'still active' changed over time."""
    result = store.customer(customer_id)
    if result is None:
        raise HTTPException(404, f"No customer called {customer_id}")
    return result


@app.get("/api/demo", tags=["customers"])
def demo():
    """The guided demo customer (a high-value shopper whose visits are slipping)."""
    return store.customer(store.demo_id)


@app.get("/api/loyalty", tags=["pages"])
def loyalty():
    """Members vs non-members and the modelled value of the loyalty programme."""
    return store.loyalty_info()


class SimulationRequest(BaseModel):
    enrol_pct: float = Field(20, ge=0, le=100, description="share of non-members to enrol (%)")
    causal_share: float = Field(0.5, ge=0, le=1, description="share of the member gap the programme causes")
    cost_per_enrolment: float = Field(1.5, ge=0, description="GBP per enrolment (assumption)")
    targeting: str = Field("targeted", description="'targeted' (best prospects first) or 'random'")


@app.post("/api/simulate", tags=["pages"])
def simulate(req: SimulationRequest):
    """What-if: enrol more customers in the loyalty programme."""
    return store.simulate(req.enrol_pct, req.causal_share, req.cost_per_enrolment, req.targeting)


@app.get("/api/model", tags=["pages"])
def model():
    """Analyst view: scorecard vs baseline, calibration, feature importance, data dictionary."""
    return store.model_info()


# ----------------------------------------------------------------------------
# Plotly served from the installed Python package, so charts work offline
# ----------------------------------------------------------------------------
@app.get("/vendor/plotly.min.js", include_in_schema=False)
def plotly_js():
    try:
        import plotly
        path = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
    except Exception:
        path = None
    if path is None or not path.exists():
        raise HTTPException(404, "plotly is not installed")
    return FileResponse(path, media_type="application/javascript")


# ----------------------------------------------------------------------------
# Front end: serve /web if it exists, otherwise a friendly placeholder
# ----------------------------------------------------------------------------
if (WEB_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
else:
    @app.get("/", include_in_schema=False)
    def placeholder():
        return HTMLResponse(
            "<body style='font-family:system-ui;background:#0b1020;color:#e8ecf5;padding:48px'>"
            "<h1>Primark CLV backend is running</h1>"
            "<p>The data service is ready. The web interface arrives in the next stage.</p>"
            "<p>Try the endpoints: <a style='color:#6ea8ff' href='/docs'>/docs</a> &middot; "
            "<a style='color:#6ea8ff' href='/api/overview'>/api/overview</a> &middot; "
            "<a style='color:#6ea8ff' href='/api/demo'>/api/demo</a></p>"
            "<p style='opacity:.6'>All data is synthetic.</p></body>")
