"""Transaction auto-categorization (keyword rules) + monthly summary math.

Rules are transparent and editable: a merchant can change any transaction's
category after import. Nothing here is tax advice — the summary is an
estimate the merchant's accountant must check.
"""

import re

# category -> (keywords, kind)  kind: 'income' or 'expense'
RULES = [
    ("sales", ["sale", "customer", "cash sale", "card sale", "raast", "qr payment",
               "online order", "delivery sale"], "income"),
    ("purchases", ["stock", "supplier", "wholesale", "inventory", "purchase",
                   "restock", "goods bought"], "expense"),
    ("utilities", ["electricity", "iesco", "lesco", "gas bill", "sui gas", "water bill",
                   "internet", "ptcl", "mobile bill", "utility"], "expense"),
    ("rent", ["rent", "shop rent", "lease"], "expense"),
    ("salaries", ["salary", "wages", "staff pay", "employee"], "expense"),
    ("transport", ["petrol", "diesel", "transport", "delivery charges", "courier",
                   "fuel", "rickshaw"], "expense"),
    ("expenses", ["expense", "repair", "maintenance", "packaging", "marketing",
                  "advertis", "misc"], "expense"),
]

CATEGORIES = [name for name, _, _ in RULES]
KIND = {name: kind for name, _, kind in RULES}


def categorize(description: str) -> str:
    """Return the first matching category by keyword, else 'expenses'.

    Keywords match on word boundaries, so e.g. 'wholesale' (a purchase)
    does not trigger the 'sale' keyword.
    """
    text = (description or "").lower()
    for category, keywords, _ in RULES:
        if any(re.search(r"\b" + re.escape(kw) + r"\b", text) for kw in keywords):
            return category
    return "expenses"


def kind_of(category: str) -> str:
    return KIND.get(category, "expense")


def monthly_summary(transactions, tax_rate_pct: float = 5.0) -> dict:
    """Compute an FBR-ready monthly summary from transaction dicts.

    transactions: iterable of dicts with keys amount, category.
    tax_rate_pct: illustrative flat rate supplied by the merchant/accountant.
    Returns totals, category breakdown, net income and a tax estimate.
    """
    total_sales = 0.0
    total_purchases = 0.0
    total_expenses = 0.0
    breakdown = {c: {"count": 0, "total": 0.0, "kind": kind_of(c)} for c in CATEGORIES}

    for tx in transactions:
        cat = tx["category"] if tx["category"] in KIND else "expenses"
        amt = float(tx["amount"])
        breakdown[cat]["count"] += 1
        breakdown[cat]["total"] = round(breakdown[cat]["total"] + amt, 2)
        if cat == "sales":
            total_sales += amt
        elif cat == "purchases":
            total_purchases += amt
        else:
            total_expenses += amt

    total_sales = round(total_sales, 2)
    total_purchases = round(total_purchases, 2)
    total_expenses = round(total_expenses, 2)
    net_income = round(total_sales - total_purchases - total_expenses, 2)
    taxable = max(0.0, net_income)
    tax_estimate = round(taxable * float(tax_rate_pct) / 100.0, 2)

    return {
        "total_sales": total_sales,
        "total_purchases": total_purchases,
        "total_expenses": total_expenses,
        "net_income": net_income,
        "tax_rate_pct": float(tax_rate_pct),
        "tax_estimate": tax_estimate,
        "breakdown": breakdown,
        "transaction_count": len(list(transactions)),
        "disclaimer": "Estimate only — not an FBR filing. Your accountant must verify "
                      "all figures and the applicable tax rate before any filing.",
    }
