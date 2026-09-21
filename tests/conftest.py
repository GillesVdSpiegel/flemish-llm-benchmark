import pytest

from flembench.items import build_items


def pair_doc(**overrides):
    doc = {
        "pair_id": "a1-9999",
        "category": "A1",
        "subcategory": "A1a",
        "format": "mc",
        "match_basis": "dcp_prevalence",
        "author": "test",
        "provenance": "human_written",
        "be": {"marker": "x", "prompt": "Wat betekent x?", "choices": ["juist", "f1", "f2", "f3"]},
        "nl": {"marker": "y", "prompt": "Wat betekent y?", "choices": ["goed", "g1", "g2", "g3"]},
    }
    doc.update(overrides)
    return doc


@pytest.fixture
def pair_items():
    return build_items(pair_doc())


@pytest.fixture(autouse=True)
def _no_heldout_env(monkeypatch):
    monkeypatch.delenv("FLEMBENCH_HELDOUT_DIR", raising=False)
