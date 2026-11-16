from app.pipeline import STAGES, can_transition, checklist_for, next_stage


def test_stages_order():
    assert STAGES == ["lead", "documents", "qr_issued", "catalog_live", "first_sale"]


def test_advance_one_step_allowed():
    assert can_transition("lead", "documents")
    assert can_transition("documents", "qr_issued")
    assert can_transition("catalog_live", "first_sale")


def test_skip_ahead_rejected():
    assert not can_transition("lead", "qr_issued")
    assert not can_transition("lead", "first_sale")
    assert not can_transition("documents", "catalog_live")


def test_move_back_allowed():
    assert can_transition("qr_issued", "lead")
    assert can_transition("first_sale", "documents")


def test_same_stage_and_unknown_rejected():
    assert not can_transition("lead", "lead")
    assert not can_transition("lead", "bogus")
    assert not can_transition("bogus", "documents")


def test_next_stage():
    assert next_stage("lead") == "documents"
    assert next_stage("first_sale") is None
    assert next_stage("bogus") is None


def test_checklist_progress():
    cl = checklist_for("qr_issued")
    assert len(cl) == 5
    assert [c["done"] for c in cl] == [True, True, True, False, False]
    assert checklist_for("first_sale")[-1]["done"] is True
    assert checklist_for("lead")[1]["done"] is False
