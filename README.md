# TAYYAR (تیار) — B2B Digital Onboarding & Tax Compliance Agency

A working web app that helps Islamabad merchants go cashless: onboard the shop,
collect documents, issue a demo Raast merchant QR, publish a digital catalog,
and keep clean monthly tax records with an AI-assisted tax assistant.

**Stack:** FastAPI + plain HTML/JS (no build step) + SQLite. Zero paid services,
nothing outbound.

## What it does

1. **Merchant onboarding** — shop details form (name, owner, phone, address,
   sector, NTN). Document upload for CNIC / NTN / utility bill: files are stored
   on disk, metadata in SQLite. Uploading the first document auto-advances the
   pipeline from Lead → Documents.
2. **Raast Merchant QR + digital catalog** — each shop gets a public catalog page
   (`/c/{shop_id}`) with items and prices, plus a QR code linking to it. The
   merchant ID shown is a clearly-labelled **DEMO** placeholder.
3. **AI Tax Assistant** — paste daily transactions or upload a CSV
   (`date,description,amount`). Each row is auto-categorized by transparent
   keyword rules (sales, purchases, utilities, rent, salaries, transport,
   expenses) and every category is editable. Produces an FBR-ready monthly
   summary (total sales, purchases, expenses, net income, tax estimate,
   category breakdown) exportable as CSV.
4. **"Cashless Ready" checklist + package tracker** — per-shop pipeline board:
   `lead → documents → qr_issued → catalog_live → first_sale`, with a checklist
   and stage controls the agency updates. Stages advance one step at a time;
   skipping ahead is rejected.

## Context (verified facts)

- Dawn reported on **13 November 2026** ([dawn.com/news/2044285](https://www.dawn.com/news/2044285))
  that Islamabad will become Pakistan's first fully cashless city by
  **31 December 2026**.
- After **30 November 2026**, no cash payment will be accepted in any ICT
  administration / CDA department.
- The target is all Islamabad merchants cashless by 31 December 2026.
- The Interior Ministry statement cited in the article says **26,000 merchants
  are already connected** to the digital payments system. That number is
  attributed to the minister's statement — it is **not** independently verified.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed        # optional: 3 clearly-labelled DEMO shops
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 — the dashboard has the onboarding form and the
pipeline board; click any shop to open its workspace (documents, QR, catalog,
tax assistant).

Run the tests:

```bash
python -m pytest tests/ -q
```

## Honest limits

- **Raast merchant QR is a DEMO placeholder.** The QR links to the shop's public
  catalog page and the merchant ID (`DEMO-RAAST-0001` etc.) is invented for demo
  purposes. A real Raast merchant QR needs the shop's **real bank-issued
  merchant ID** — TAYYAR never fakes one.
- **No real FBR filing.** The monthly summary is an **estimate** computed at an
  illustrative tax rate the merchant/accountant sets (default 5%). The
  merchant's accountant must verify all figures and the applicable rate before
  any filing. TAYYAR files nothing with FBR.
- **OCR is NOT installed on this machine.** There is no `tesseract` binary, so
  document text is **not** auto-read. Details from uploaded documents must be
  entered manually, and the UI says so plainly. If Tesseract is installed later,
  `/api/status` will report it as available.
- **Demo data only.** The seed creates 3 clearly-labelled DEMO shops. Do **not**
  upload real CNICs — no real CNIC numbers are stored by this app, and uploads
  are plain files on this machine's disk.
- **Local only.** SQLite database + on-disk uploads; no hosting, no backups,
  no multi-user auth. Deploying for real customers needs authentication,
  encrypted storage, and a real database.

## Sales pitch (one page)

**TAYYAR (تیار) — "Cashless Ready" for Islamabad merchants**

**The deadline is real.** Islamabad goes fully cashless by 31 December 2026, and
after 30 November 2026 no cash will be accepted in any ICT administration or CDA
department. Every shop in the city has weeks, not months, to get ready — and
most small merchants don't know where to start.

**Who pays:** the shop owner — general stores, pharmacies, mobile shops,
restaurants, and clinics across Islamabad who need to accept digital payments
and keep clean records.

**What they get (one-time "Cashless Ready Package"):** we register the shop,
collect and file the documents (CNIC, NTN, utility bill), issue their Raast
merchant QR, build their digital catalog with live prices, and set up their
monthly tax record — so the first digital sale happens in days, not weeks.

**How much (the owner's asking prices):** one-time **PKR 10,000–20,000 per shop**
depending on shop size and catalog size. No monthly fee for the basic package;
tax-assistant support is included for the first month.

**Why TAYYAR:** one visit, one package, everything done — documents, QR,
catalog, and tax records in a single pipeline the merchant can watch move.
The alternative is the merchant figuring out bank paperwork, QR codes, and
FBR records alone, after the deadline has already passed.

**The honest part:** the Raast merchant ID comes from the merchant's own bank;
we prepare everything around it and never fake it. The monthly tax summary is
an estimate their accountant checks — we make the record-keeping easy, we
don't pretend to be the accountant.
```

## API (main endpoints)

| Method | Endpoint | What it does |
|---|---|---|
| POST | `/api/shops` | Register a merchant |
| GET | `/api/shops`, `/api/board` | List shops / pipeline board |
| POST | `/api/shops/{id}/documents` | Upload CNIC / NTN / utility bill |
| POST | `/api/shops/{id}/qr` | Issue DEMO Raast QR |
| POST/GET | `/api/shops/{id}/catalog` | Add / list catalog items |
| GET | `/c/{id}` | Public catalog page |
| POST | `/api/shops/{id}/transactions` | Add one transaction (auto-categorized) |
| POST | `/api/shops/{id}/transactions/upload` | CSV import |
| PUT | `/api/transactions/{id}` | Change a transaction's category |
| GET | `/api/shops/{id}/summary?month=YYYY-MM` | Monthly summary (estimate) |
| GET | `/api/shops/{id}/summary.csv` | Summary CSV export |
| POST | `/api/shops/{id}/stage` | Move pipeline stage |
| GET | `/api/status` | App + OCR availability status |
