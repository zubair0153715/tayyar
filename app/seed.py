"""Seed TAYYAR with clearly-labelled DEMO shops only. Run: python -m app.seed"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db
from app.categorizer import categorize
from app.main import make_qr, maybe_auto_advance

DEMO_SHOPS = [
    {
        "name": "DEMO — Bilal General Store",
        "owner_name": "Demo Owner",
        "phone": "0300-0000001",
        "address": "F-7 Markaz, Islamabad (DEMO)",
        "sector": "General Store",
        "ntn": "DEMO-NTN-0001",
        "catalog": [("Atta 10kg", 1250, "Grocery"), ("Cooking Oil 5L", 3200, "Grocery"),
                    ("Sugar 5kg", 850, "Grocery"), ("Tea 500g", 950, "Grocery")],
        "transactions": [
            ("2026-11-01", "Cash sale — customer", 4500),
            ("2026-11-02", "Raast QR payment — customer", 2800),
            ("2026-11-03", "Stock purchase — supplier", 15000),
            ("2026-11-05", "Electricity bill IESCO", 4200),
            ("2026-11-06", "Cash sale — customer", 6100),
            ("2026-11-08", "Shop rent November", 25000),
            ("2026-11-10", "Card sale — customer", 3400),
        ],
    },
    {
        "name": "DEMO — Ayesha Pharmacy",
        "owner_name": "Demo Owner",
        "phone": "0300-0000002",
        "address": "G-9 Markaz, Islamabad (DEMO)",
        "sector": "Pharmacy",
        "ntn": "DEMO-NTN-0002",
        "catalog": [("Paracetamol 500mg (10 tabs)", 120, "Medicine"),
                    ("Vitamin D 2000 IU", 850, "Medicine"),
                    ("Hand Sanitizer 250ml", 450, "Care")],
        "transactions": [
            ("2026-11-01", "Cash sale — customer", 8900),
            ("2026-11-04", "Wholesale stock — supplier", 22000),
            ("2026-11-07", "Salary — staff", 18000),
            ("2026-11-09", "Cash sale — customer", 5200),
        ],
    },
    {
        "name": "DEMO — Usman Mobile & Accessories",
        "owner_name": "Demo Owner",
        "phone": "0300-0000003",
        "address": "Blue Area, Islamabad (DEMO)",
        "sector": "Mobile Accessories",
        "ntn": "DEMO-NTN-0003",
        "catalog": [("Phone Cover", 600, "Accessories"), ("Charger 25W", 1800, "Accessories"),
                    ("Earbuds", 2500, "Accessories")],
        "transactions": [
            ("2026-11-02", "Online order sale", 7500),
            ("2026-11-05", "Restock — wholesale supplier", 30000),
            ("2026-11-11", "Internet bill PTCL", 3500),
        ],
    },
]


def seed():
    db.init_db()
    with db.get_db() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM shops").fetchone()[0]
        if existing:
            print(f"DB already has {existing} shop(s) — skipping seed.")
            return
    for shop in DEMO_SHOPS:
        with db.get_db() as conn:
            cur = conn.execute(
                "INSERT INTO shops (name, owner_name, phone, address, sector, ntn, stage) "
                "VALUES (?, ?, ?, ?, ?, ?, 'lead')",
                (shop["name"], shop["owner_name"], shop["phone"],
                 shop["address"], shop["sector"], shop["ntn"]),
            )
            sid = cur.lastrowid
            conn.execute(
                "UPDATE shops SET raast_demo_id = ? WHERE id = ?",
                (f"DEMO-RAAST-{sid:04d}", sid),
            )
            for name, price, cat in shop["catalog"]:
                conn.execute(
                    "INSERT INTO catalog_items (shop_id, name, price, category) VALUES (?, ?, ?, ?)",
                    (sid, name, price, cat),
                )
            for d, desc, amt in shop["transactions"]:
                conn.execute(
                    "INSERT INTO transactions (shop_id, date, description, amount, category, source) "
                    "VALUES (?, ?, ?, ?, ?, 'seed')",
                    (sid, d, desc, amt, categorize(desc)),
                )
        make_qr(sid)
        # Walk the demo shop through the pipeline to showcase the board.
        for target in ["documents", "qr_issued", "catalog_live", "first_sale"]:
            maybe_auto_advance(sid, {"documents": "lead", "qr_issued": "documents",
                                     "catalog_live": "qr_issued",
                                     "first_sale": "catalog_live"}[target], target)
        print(f"Seeded DEMO shop {sid}: {shop['name']}")
    print("Seed complete — DEMO data only.")


if __name__ == "__main__":
    seed()
