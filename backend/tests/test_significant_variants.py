import polars as pl
import pytest

from app.analysis.significant_variants import extract_significant_variants


def _frame(pvals):
    n = len(pvals)
    return pl.DataFrame(
        {
            "rsid": [f"rs{i}" for i in range(n)],
            "chromosome": ["1"] * n,
            "position": list(range(n)),
            "p_value": pvals,
        }
    )


def test_genome_wide_threshold():
    frame = _frame([1e-9, 4e-8, 5e-8, 1e-3, None])
    sel = extract_significant_variants(frame, method="genome_wide")
    assert sel.threshold == 5e-8
    # 5e-8 is NOT < 5e-8; None excluded
    assert sel.n_selected == 2
    assert set(sel.frame["rsid"].to_list()) == {"rs0", "rs1"}


def test_suggestive_threshold():
    frame = _frame([1e-9, 1e-6, 1e-4, 0.2])
    sel = extract_significant_variants(frame, method="suggestive")
    assert sel.threshold == 1e-5
    assert sel.n_selected == 2


def test_top_k_selection_sorted():
    frame = _frame([0.5, 1e-9, 1e-3, 1e-7])
    sel = extract_significant_variants(frame, method="top_k", k=2)
    assert sel.n_selected == 2
    assert sel.frame["p_value"].to_list() == [1e-9, 1e-7]


def test_custom_threshold_requires_value():
    frame = _frame([0.01, 0.5])
    with pytest.raises(ValueError):
        extract_significant_variants(frame, method="custom")


def test_invalid_pvalues_excluded():
    frame = _frame([1e-9, -1.0, 2.0, None])
    sel = extract_significant_variants(frame, method="genome_wide")
    assert sel.n_selected == 1


def test_unknown_method_raises():
    frame = _frame([1e-9])
    with pytest.raises(ValueError):
        extract_significant_variants(frame, method="bogus")
