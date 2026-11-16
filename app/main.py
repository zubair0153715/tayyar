"""TAYYAR (تیار) — B2B Digital Onboarding & Tax Compliance Agency.

FastAPI + plain HTML/JS + SQLite. Zero paid services, nothing outbound.
Every demo value is labelled DEMO. No real payment, verification, Raast
merchant ID, government approval, or FBR filing is ever faked.
"""
import csv
import io
import os
import shutil
from datetime import date
from pathlib import Path

import qrcode
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import db
from app.categorizer import CATEGORIES, categorize, kind_of, monthly_summary
from app.pipeline import STAGES, STAGE_LABELS, can_transition, checklist_for, next_stage

BASE_URL = os.environ.get("TAYYAR_BASE_URL", "http://127.0.0.1:8000")
OCR_AVAILABLE = shutil.which("tesseract") is not None

app = FastAPI(title="TAYYAR — تیار", version="1.0.0")
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
QR_DIR = STATIC_DIR / "qr"
QR_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def startup():
    db.init_db()


# ---------- helpers ----------

def get_shop_or_404(shop_id: int) -> dict:
    with db.get_db() as conn:
        shop = db.row_to_dict(
            conn.execute("SELECT * FROM shops WHERE id = ?", (shop_id,)).fetchone()
        )
    if not shop:
        raise HTTPException(404, "Shop not found")
    return shop


def set_stage(shop_id: int, target: str) -> dict:
    shop = get_shop_or_404(shop_id)
    if not can_transition(shop["stage"], target):
        raise HTTPException(
            400,
            f"Cannot move from '{shop['stage']}' to '{target}'. "
            "Advance one step at a time; skipping ahead is not allowed.",
        )
    with db.get_db() as conn:
        conn.execute("UPDATE shops SET stage = ? WHERE id = ?", (target, shop_id))
    return get_shop_or_404(shop_id)


def maybe_auto_advance(shop_id: int, expected_current: str, target: str) -> None:
    """Auto-advance the pipeline when an event completes the current stage."""
    shop = get_shop_or_404(shop_id)
    if shop["stage"] == expected_current and can_transition(expected_current, target):
        with db.get_db() as conn:
            conn.execute("UPDATE shops SET stage = ? WHERE id = ?", (target, shop_id))


def make_qr(shop_id: int) -> str:
    """Generate a QR code PNG encoding the shop's public catalog URL.

    This QR links to the shop catalog page. It is NOT a Raast payment QR —
    a real Raast merchant QR needs the shop's bank-issued merchant ID.
    """
    url = f"{BASE_URL}/c/{shop_id}"
    path = QR_DIR / f"shop-{shop_id}.png"
    img = qrcode.make(url)
    img.save(path)
    return f"/static/qr/shop-{shop_id}.png"


# ---------- models ----------

class ShopCreate(BaseModel):
    name: str = Field(min_length=1)
    owner_name: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    address: str = Field(min_length=1)
    sector: str = "General Store"
    ntn: str = ""


class CatalogItemCreate(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(ge=0)
    category: str = "General"


class TransactionCreate(BaseModel):
    date: str
    description: str = Field(min_length=1)
    amount: float = Field(gt=0)
    category: str | None = None  # auto-categorized if omitted


class TransactionUpdate(BaseModel):
    category: str


class StageUpdate(BaseModel):
    stage: str


# ---------- pages ----------

@app.get("/", response_class=HTMLResponse)
def home():
    return RedirectResponse("/static/index.html")


@app.get("/c/{shop_id}", response_class=HTMLResponse)
def public_catalog(shop_id: int):
    """Publicly viewable shop catalog page (what the QR code links to)."""
    shop = get_shop_or_404(shop_id)
    with db.get_db() as conn:
        items = [
            db.row_to_dict(r)
            for r in conn.execute(
                "SELECT * FROM catalog_items WHERE shop_id = ? ORDER BY category, name",
                (shop_id,),
            ).fetchall()
        ]
    rows = "".join(
        f"<tr><td>{i['name']}</td><td>{i['category']}</td>"
        f"<td style='text-align:right'>Rs {i['price']:,.0f}</td></tr>"
        for i in items
    ) or "<tr><td colspan='3'>No items yet — catalog coming soon.</td></tr>"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{shop['name']} — Digital Catalog | TAYYAR</title>
<style>body{{font-family:system-ui,sans-serif;max-width:640px;margin:2rem auto;padding:0 1rem}}
table{{width:100%;border-collapse:collapse}}td,th{{padding:.5rem;border-bottom:1px solid #ddd;text-align:left}}
.badge{{background:#e8f5e9;color:#2e7d32;padding:.2rem .6rem;border-radius:1rem;font-size:.85rem}}</style>
</head><body>
<h1>🛍️ {shop['name']}</h1>
<p>{shop['address']} · {shop['sector']}<br>📞 {shop['phone']}</p>
<p><span class="badge">Cashless payments accepted (Raast QR — DEMO)</span></p>
<p>Raast Merchant ID: <strong>{shop['raast_demo_id'] or 'Not issued yet'}</strong> (DEMO placeholder)</p>
<table><tr><th>Item</th><th>Category</th><th style="text-align:right">Price</th></tr>{rows}</table>
<p style="color:#666;font-size:.85rem">Catalog by TAYYAR (تیار) — Digital Onboarding &amp; Tax Compliance Agency, Islamabad.
Prices in PKR. Pay digitally via the shop's Raast QR at the counter.</p>
</body></html>"""


# ---------- status / OCR ----------

@app.get("/api/status")
def status():
    return {
        "app": "TAYYAR",
        "ocr_available": OCR_AVAILABLE,
        "ocr_note": (
            "Tesseract OCR is installed — document text can be read automatically."
            if OCR_AVAILABLE
            else "OCR is NOT installed on this machine (no `tesseract` binary). "
                 "Document details must be entered manually — the app never "
                 "pretends OCR read text it did not read."
        ),
        "stages": STAGES,
    }


# ---------- shops / onboarding ----------

@app.post("/api/shops", status_code=201)
def create_shop(payload: ShopCreate):
    with db.get_db() as conn:
        cur = conn.execute(
            "INSERT INTO shops (name, owner_name, phone, address, sector, ntn) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (payload.name, payload.owner_name, payload.phone,
             payload.address, payload.sector, payload.ntn),
        )
        shop_id = cur.lastrowid
        demo_id = f"DEMO-RAAST-{shop_id:04d}"
        conn.execute(
            "UPDATE shops SET raast_demo_id = ? WHERE id = ?", (demo_id, shop_id)
        )
    return get_shop_or_404(shop_id)


@app.get("/api/shops")
def list_shops():
    with db.get_db() as conn:
        shops = [
            db.row_to_dict(r)
            for r in conn.execute("SELECT * FROM shops ORDER BY id").fetchall()
        ]
    for s in shops:
        s["stage_label"] = STAGE_LABELS.get(s["stage"], s["stage"])
        s["checklist"] = checklist_for(s["stage"])
    return shops


@app.get("/api/shops/{shop_id}")
def get_shop(shop_id: int):
    shop = get_shop_or_404(shop_id)
    shop["stage_label"] = STAGE_LABELS.get(shop["stage"], shop["stage"])
    shop["checklist"] = checklist_for(shop["stage"])
    with db.get_db() as conn:
        shop["documents"] = [
            db.row_to_dict(r)
            for r in conn.execute(
                "SELECT * FROM documents WHERE shop_id = ? ORDER BY uploaded_at",
                (shop_id,),
            ).fetchall()
        ]
        shop["catalog"] = [
            db.row_to_dict(r)
            for r in conn.execute(
                "SELECT * FROM catalog_items WHERE shop_id = ? ORDER BY category, name",
                (shop_id,),
            ).fetchall()
        ]
        shop["qr_url"] = (
            f"/static/qr/shop-{shop_id}.png"
            if (QR_DIR / f"shop-{shop_id}.png").exists()
            else None
        )
    return shop


@app.post("/api/shops/{shop_id}/documents", status_code=201)
async def upload_document(
    shop_id: int,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
):
    """Store a document upload on disk + metadata in SQLite.

    DEMO ONLY: merchants must upload demo/sample files here. Do NOT upload
    a real CNIC — no real CNIC numbers are stored by this app.
    """
    shop = get_shop_or_404(shop_id)
    if doc_type not in ("cnic", "ntn", "utility_bill"):
        raise HTTPException(400, "doc_type must be cnic, ntn or utility_bill")
    shop_dir = db.UPLOAD_DIR / str(shop_id)
    shop_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "upload").name
    stored = shop_dir / f"{doc_type}_{safe_name}"
    data = await file.read()
    stored.write_bytes(data)
    with db.get_db() as conn:
        conn.execute(
            "INSERT INTO documents (shop_id, doc_type, filename, stored_path, size_bytes) "
            "VALUES (?, ?, ?, ?, ?)",
            (shop_id, doc_type, safe_name, str(stored), len(data)),
        )
    # Auto-fill: first document completes the "documents" stage.
    maybe_auto_advance(shop_id, "lead", "documents")
    return {
        "shop_id": shop_id,
        "doc_type": doc_type,
        "filename": safe_name,
        "size_bytes": len(data),
        "ocr_note": "OCR not installed — details from this document were NOT auto-read. "
                    "Enter them manually in the shop form."
        if not OCR_AVAILABLE
        else "OCR available.",
        "stage": get_shop_or_404(shop_id)["stage"],
    }


# ---------- Raast QR + catalog ----------

@app.post("/api/shops/{shop_id}/qr", status_code=201)
def issue_qr(shop_id: int):
    """Issue the DEMO Raast merchant QR for a shop.

    The QR encodes the shop's public catalog URL. The merchant ID shown is
    a DEMO placeholder — a real Raast merchant QR needs the shop's real
    bank-issued merchant ID.
    """
    shop = get_shop_or_404(shop_id)
    qr_url = make_qr(shop_id)
    maybe_auto_advance(shop_id, "documents", "qr_issued")
    return {
        "shop_id": shop_id,
        "qr_url": qr_url,
        "catalog_url": f"{BASE_URL}/c/{shop_id}",
        "raast_demo_id": shop["raast_demo_id"],
        "warning": "DEMO QR — the merchant ID is a placeholder. A real Raast "
                   "merchant QR requires the shop's bank-issued merchant ID.",
        "stage": get_shop_or_404(shop_id)["stage"],
    }


@app.post("/api/shops/{shop_id}/catalog", status_code=201)
def add_catalog_item(shop_id: int, payload: CatalogItemCreate):
    get_shop_or_404(shop_id)
    with db.get_db() as conn:
        cur = conn.execute(
            "INSERT INTO catalog_items (shop_id, name, price, category) VALUES (?, ?, ?, ?)",
            (shop_id, payload.name, payload.price, payload.category),
        )
        item_id = cur.lastrowid
    maybe_auto_advance(shop_id, "qr_issued", "catalog_live")
    with db.get_db() as conn:
        item = db.row_to_dict(
            conn.execute("SELECT * FROM catalog_items WHERE id = ?", (item_id,)).fetchone()
        )
    return item


@app.get("/api/shops/{shop_id}/catalog")
def list_catalog(shop_id: int):
    get_shop_or_404(shop_id)
    with db.get_db() as conn:
        return [
            db.row_to_dict(r)
            for r in conn.execute(
                "SELECT * FROM catalog_items WHERE shop_id = ? ORDER BY category, name",
                (shop_id,),
            ).fetchall()
        ]


# ---------- pipeline ----------

@app.post("/api/shops/{shop_id}/stage")
def update_stage(shop_id: int, payload: StageUpdate):
    if payload.stage not in STAGES:
        raise HTTPException(400, f"Unknown stage '{payload.stage}'")
    shop = set_stage(shop_id, payload.stage)
    shop["stage_label"] = STAGE_LABELS.get(shop["stage"], shop["stage"])
    shop["checklist"] = checklist_for(shop["stage"])
    return shop


@app.get("/api/board")
def board():
    """Per-shop status board for the agency."""
    shops = list_shops()
    return {
        "stages": [{"id": s, "label": STAGE_LABELS[s]} for s in STAGES],
        "counts": {s: sum(1 for sh in shops if sh["stage"] == s) for s in STAGES},
        "shops": shops,
    }


# ---------- AI tax assistant ----------

@app.post("/api/shops/{shop_id}/transactions", status_code=201)
def add_transaction(shop_id: int, payload: TransactionCreate):
    get_shop_or_404(shop_id)
    category = payload.category or categorize(payload.description)
    if category not in CATEGORIES:
        raise HTTPException(400, f"Unknown category '{category}'")
    with db.get_db() as conn:
        cur = conn.execute(
            "INSERT INTO transactions (shop_id, date, description, amount, category, source) "
            "VALUES (?, ?, ?, ?, ?, 'manual')",
            (shop_id, payload.date, payload.description, payload.amount, category),
        )
        tx_id = cur.lastrowid
    # First recorded sale completes the pipeline.
    if category == "sales":
        maybe_auto_advance(shop_id, "catalog_live", "first_sale")
    with db.get_db() as conn:
        return db.row_to_dict(
            conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
        )


@app.post("/api/shops/{shop_id}/transactions/upload", status_code=201)
async def upload_transactions(shop_id: int, file: UploadFile = File(...)):
    """CSV upload: columns date,description,amount (header row required).
    Each row is auto-categorized by keyword rules."""
    get_shop_or_404(shop_id)
    text = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    required = {"date", "description", "amount"}
    if not reader.fieldnames or not required.issubset({f.strip() for f in reader.fieldnames}):
        raise HTTPException(400, "CSV needs header row: date,description,amount")
    imported, skipped = [], []
    with db.get_db() as conn:
        for i, row in enumerate(reader, start=2):
            try:
                desc = (row.get("description") or "").strip()
                amt = float(row["amount"])
                d = (row.get("date") or date.today().isoformat()).strip()
                if not desc or amt <= 0:
                    raise ValueError("empty description or non-positive amount")
            except (ValueError, TypeError, KeyError):
                skipped.append(i)
                continue
            category = categorize(desc)
            cur = conn.execute(
                "INSERT INTO transactions (shop_id, date, description, amount, category, source) "
                "VALUES (?, ?, ?, ?, ?, 'csv')",
                (shop_id, d, desc, amt, category),
            )
            imported.append({"id": cur.lastrowid, "date": d, "description": desc,
                             "amount": amt, "category": category})
    if any(t["category"] == "sales" for t in imported):
        maybe_auto_advance(shop_id, "catalog_live", "first_sale")
    return {"imported": len(imported), "skipped_rows": skipped, "transactions": imported}


@app.get("/api/shops/{shop_id}/transactions")
def list_transactions(shop_id: int, month: str | None = None):
    get_shop_or_404(shop_id)
    q = "SELECT * FROM transactions WHERE shop_id = ?"
    params: list = [shop_id]
    if month:
        q += " AND substr(date, 1, 7) = ?"
        params.append(month)
    q += " ORDER BY date DESC, id DESC"
    with db.get_db() as conn:
        return [
            db.row_to_dict(r) for r in conn.execute(q, params).fetchall()
        ]


@app.put("/api/transactions/{tx_id}")
def update_transaction(tx_id: int, payload: TransactionUpdate):
    if payload.category not in CATEGORIES:
        raise HTTPException(400, f"Unknown category '{payload.category}'")
    with db.get_db() as conn:
        tx = conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
        if not tx:
            raise HTTPException(404, "Transaction not found")
        conn.execute(
            "UPDATE transactions SET category = ? WHERE id = ?", (payload.category, tx_id)
        )
        return db.row_to_dict(
            conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
        )


@app.get("/api/shops/{shop_id}/summary")
def monthly_summary_endpoint(shop_id: int, month: str, tax_rate_pct: float = 5.0):
    get_shop_or_404(shop_id)
    txs = list_transactions(shop_id, month=month)
    summary = monthly_summary(txs, tax_rate_pct=tax_rate_pct)
    summary["shop_id"] = shop_id
    summary["month"] = month
    summary["kind"] = {c: kind_of(c) for c in CATEGORIES}
    return summary


@app.get("/api/shops/{shop_id}/summary.csv", response_class=PlainTextResponse)
def monthly_summary_csv(shop_id: int, month: str, tax_rate_pct: float = 5.0):
    get_shop_or_404(shop_id)
    txs = list_transactions(shop_id, month=month)
    s = monthly_summary(txs, tax_rate_pct=tax_rate_pct)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["TAYYAR monthly summary (ESTIMATE — accountant must verify)", f"Shop {shop_id}", month])
    w.writerow(["total_sales_pkr", s["total_sales"]])
    w.writerow(["total_purchases_pkr", s["total_purchases"]])
    w.writerow(["total_expenses_pkr", s["total_expenses"]])
    w.writerow(["net_income_pkr", s["net_income"]])
    w.writerow(["tax_rate_pct", s["tax_rate_pct"]])
    w.writerow(["tax_estimate_pkr", s["tax_estimate"]])
    w.writerow([])
    w.writerow(["category", "kind", "count", "total_pkr"])
    for cat, b in s["breakdown"].items():
        w.writerow([cat, b["kind"], b["count"], b["total"]])
    return out.getvalue()
