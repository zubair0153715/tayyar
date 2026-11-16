from app.categorizer import CATEGORIES, categorize, kind_of, monthly_summary


def test_sales_keywords():
    assert categorize("Cash sale — customer") == "sales"
    assert categorize("Raast QR payment received") == "sales"
    assert categorize("Card sale at counter") == "sales"


def test_purchase_and_utility_keywords():
    assert categorize("Stock purchase from supplier") == "purchases"
    assert categorize("Wholesale restock") == "purchases"
    assert categorize("Electricity bill IESCO") == "utilities"
    assert categorize("Internet bill PTCL") == "utilities"


def test_expense_keywords():
    assert categorize("Shop rent November") == "rent"
    assert categorize("Salary — staff") == "salaries"
    assert categorize("Petrol for delivery") == "transport"


def test_unknown_falls_back_to_expenses():
    assert categorize("something random with no keywords") == "expenses"
    assert categorize("") == "expenses"


def test_kind_mapping():
    assert kind_of("sales") == "income"
    assert kind_of("purchases") == "expense"
    assert kind_of("utilities") == "expense"


def test_monthly_summary_math():
    txs = [
        {"amount": 10000, "category": "sales"},
        {"amount": 5000, "category": "sales"},
        {"amount": 6000, "category": "purchases"},
        {"amount": 2000, "category": "utilities"},
        {"amount": 1000, "category": "rent"},
    ]
    s = monthly_summary(txs, tax_rate_pct=5.0)
    assert s["total_sales"] == 15000
    assert s["total_purchases"] == 6000
    assert s["total_expenses"] == 3000
    assert s["net_income"] == 6000
    assert s["tax_estimate"] == 300.0
    assert s["breakdown"]["sales"]["count"] == 2
    assert s["breakdown"]["sales"]["total"] == 15000
    assert s["transaction_count"] == 5


def test_monthly_summary_no_tax_on_loss():
    txs = [{"amount": 1000, "category": "sales"},
           {"amount": 5000, "category": "purchases"}]
    s = monthly_summary(txs, tax_rate_pct=5.0)
    assert s["net_income"] == -4000
    assert s["tax_estimate"] == 0.0


def test_monthly_summary_empty_month():
    s = monthly_summary([], tax_rate_pct=5.0)
    assert s["total_sales"] == 0
    assert s["tax_estimate"] == 0.0
    assert s["transaction_count"] == 0
    assert "accountant" in s["disclaimer"]
