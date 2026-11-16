import io


def test_status_reports_ocr_honestly(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    data = r.json()
    # This machine has no tesseract binary — the API must say so plainly.
    assert data["ocr_available"] is False
    assert "NOT installed" in data["ocr_note"]


def test_create_and_get_shop(client):
    r = client.post("/api/shops", json={
        "name": "API Store", "owner_name": "Owner", "phone": "0300-2222222",
        "address": "G-8, Islamabad", "sector": "Pharmacy",
    })
    assert r.status_code == 201
    shop = r.json()
    assert shop["stage"] == "lead"
    assert shop["raast_demo_id"].startswith("DEMO-RAAST-")
    r2 = client.get(f"/api/shops/{shop['id']}")
    assert r2.status_code == 200
    assert r2.json()["name"] == "API Store"


def test_stage_transition_rules_via_api(client, shop):
    # Skip ahead must be rejected.
    r = client.post(f"/api/shops/{shop['id']}/stage", json={"stage": "qr_issued"})
    assert r.status_code == 400
    # One step forward works.
    r = client.post(f"/api/shops/{shop['id']}/stage", json={"stage": "documents"})
    assert r.status_code == 200
    assert r.json()["stage"] == "documents"
    # Unknown stage rejected.
    r = client.post(f"/api/shops/{shop['id']}/stage", json={"stage": "bogus"})
    assert r.status_code == 400
    # Missing shop 404s.
    r = client.post("/api/shops/99999/stage", json={"stage": "documents"})
    assert r.status_code == 404


def test_document_upload_advances_pipeline(client, shop):
    files = {"file": ("demo-cnic.png", b"fake-image-bytes", "image/png")}
    r = client.post(f"/api/shops/{shop['id']}/documents",
                    data={"doc_type": "cnic"}, files=files)
    assert r.status_code == 201
    assert r.json()["stage"] == "documents"
    assert "OCR not installed" in r.json()["ocr_note"]
    # Bad doc type rejected.
    r = client.post(f"/api/shops/{shop['id']}/documents",
                    data={"doc_type": "passport"}, files=files)
    assert r.status_code == 400


def test_qr_issue_and_public_catalog(client, shop):
    client.post(f"/api/shops/{shop['id']}/stage", json={"stage": "documents"})
    r = client.post(f"/api/shops/{shop['id']}/qr")
    assert r.status_code == 201
    data = r.json()
    assert data["raast_demo_id"].startswith("DEMO-RAAST-")
    assert "DEMO QR" in data["warning"]
    assert data["stage"] == "qr_issued"
    # Catalog item add auto-advances to catalog_live.
    r = client.post(f"/api/shops/{shop['id']}/catalog",
                    json={"name": "Atta 10kg", "price": 1250, "category": "Grocery"})
    assert r.status_code == 201
    shop_now = client.get(f"/api/shops/{shop['id']}").json()
    assert shop_now["stage"] == "catalog_live"
    # Public catalog page renders the item.
    r = client.get(f"/c/{shop['id']}")
    assert r.status_code == 200
    assert "Atta 10kg" in r.text
    assert "DEMO" in r.text


def test_transactions_csv_and_summary(client, shop):
    csv_text = (
        "date,description,amount\n"
        "2026-11-01,Cash sale — customer,5000\n"
        "2026-11-02,Stock purchase — supplier,3000\n"
        "2026-11-03,Electricity bill IESCO,1000\n"
        "2026-11-04,bad row,not-a-number\n"
    )
    r = client.post(f"/api/shops/{shop['id']}/transactions/upload",
                    files={"file": ("tx.csv", csv_text.encode(), "text/csv")})
    assert r.status_code == 201
    data = r.json()
    assert data["imported"] == 3
    assert data["skipped_rows"] == [5]
    assert data["transactions"][0]["category"] == "sales"
    # First sale auto-advances catalog_live -> first_sale only if already there;
    # this shop is still at lead, so stage stays lead (no skip).
    assert client.get(f"/api/shops/{shop['id']}").json()["stage"] == "lead"
    # Summary math via API.
    r = client.get(f"/api/shops/{shop['id']}/summary",
                   params={"month": "2026-11", "tax_rate_pct": 5})
    assert r.status_code == 200
    s = r.json()
    assert s["total_sales"] == 5000
    assert s["total_purchases"] == 3000
    assert s["total_expenses"] == 1000
    assert s["net_income"] == 1000
    assert s["tax_estimate"] == 50.0
    assert "accountant" in s["disclaimer"]
    # CSV export.
    r = client.get(f"/api/shops/{shop['id']}/summary.csv",
                   params={"month": "2026-11", "tax_rate_pct": 5})
    assert r.status_code == 200
    assert "total_sales_pkr,5000" in r.text


def test_manual_transaction_and_category_edit(client, shop):
    r = client.post(f"/api/shops/{shop['id']}/transactions", json={
        "date": "2026-11-05", "description": "Mystery payment", "amount": 2000})
    assert r.status_code == 201
    tx = r.json()
    assert tx["category"] == "expenses"  # fallback category
    r = client.put(f"/api/transactions/{tx['id']}", json={"category": "sales"})
    assert r.status_code == 200
    assert r.json()["category"] == "sales"
    r = client.put(f"/api/transactions/{tx['id']}", json={"category": "bogus"})
    assert r.status_code == 400


def test_board_endpoint(client, shop):
    r = client.get("/api/board")
    assert r.status_code == 200
    data = r.json()
    assert data["counts"]["lead"] == 1
    assert len(data["shops"]) == 1
    assert data["shops"][0]["checklist"][0]["done"] is True


def test_home_redirect_and_static_pages(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (200, 307)
    r = client.get("/static/index.html")
    assert r.status_code == 200
    assert "TAYYAR" in r.text
    r = client.get("/static/shop.html")
    assert r.status_code == 200
