"""Onboarding pipeline stages and transition rules.

Stages: lead -> documents -> qr_issued -> catalog_live -> first_sale
Advance one step at a time; moving back to any earlier stage is allowed
(e.g. documents rejected). Skipping ahead is rejected.
"""

STAGES = ["lead", "documents", "qr_issued", "catalog_live", "first_sale"]

STAGE_LABELS = {
    "lead": "Lead",
    "documents": "Documents received",
    "qr_issued": "Raast QR issued (DEMO)",
    "catalog_live": "Catalog live",
    "first_sale": "First digital sale",
}

# "Cashless Ready" checklist shown per shop
CHECKLIST = [
    ("lead", "Shop registered with TAYYAR"),
    ("documents", "CNIC / NTN / utility bill on file (demo copies)"),
    ("qr_issued", "Raast merchant QR issued (DEMO ID — real ID comes from the bank)"),
    ("catalog_live", "Digital catalog published"),
    ("first_sale", "First digital (cashless) sale recorded"),
]


def can_transition(current: str, target: str) -> bool:
    """True if moving from current stage to target stage is allowed."""
    if current not in STAGES or target not in STAGES:
        return False
    cur_i, tgt_i = STAGES.index(current), STAGES.index(target)
    if tgt_i == cur_i:
        return False
    if tgt_i == cur_i + 1:  # advance exactly one step
        return True
    if tgt_i < cur_i:  # move back to any earlier stage
        return True
    return False  # skipping ahead


def next_stage(current: str) -> str | None:
    if current not in STAGES:
        return None
    i = STAGES.index(current)
    return STAGES[i + 1] if i + 1 < len(STAGES) else None


def checklist_for(stage: str) -> list[dict]:
    """Checklist items with done/pending state for a shop at `stage`."""
    idx = STAGES.index(stage) if stage in STAGES else -1
    return [
        {"stage": s, "label": label, "done": STAGES.index(s) <= idx}
        for s, label in CHECKLIST
    ]
