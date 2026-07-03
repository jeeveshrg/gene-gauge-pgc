import pytest

from app.analysis.gene_overlap import (
    apply_fdr_correction,
    compute_gene_overlap,
    compute_hypergeometric_p_value,
)


def test_gene_overlap_shared_and_jaccard():
    res = compute_gene_overlap(
        {"A", "B", "C"}, {"B", "C", "D"}, universe_size=100,
        disorder_a="X", disorder_b="Y",
    )
    assert res.shared_genes == ["B", "C"]
    assert res.n_shared == 2
    assert res.jaccard == 2 / 4
    assert 0.0 <= res.hypergeometric_p <= 1.0


def test_hypergeometric_more_overlap_lower_p():
    # Larger overlap in same-size sets should be more surprising (smaller p).
    p_small = compute_hypergeometric_p_value(shared=1, n_a=10, n_b=10, universe_size=1000)
    p_large = compute_hypergeometric_p_value(shared=8, n_a=10, n_b=10, universe_size=1000)
    assert p_large < p_small


def test_hypergeometric_edge_cases():
    assert compute_hypergeometric_p_value(0, 5, 5, 100) == 1.0
    assert compute_hypergeometric_p_value(1, 0, 5, 100) == 1.0
    assert compute_hypergeometric_p_value(1, 5, 5, 0) == 1.0


def test_full_overlap_is_significant():
    # complete overlap of two 10-gene sets in a 1000-gene universe.
    p = compute_hypergeometric_p_value(shared=10, n_a=10, n_b=10, universe_size=1000)
    assert p < 1e-6


def test_fdr_correction_monotone_and_ordered():
    pvals = [0.001, 0.01, 0.02, 0.5]
    res = apply_fdr_correction(pvals, alpha=0.05)
    q = res["qvalues"]
    assert len(q) == 4
    # q-values are non-decreasing in the same order as sorted p-values here
    assert q[0] <= q[1] <= q[2] <= q[3]
    assert all(0.0 <= x <= 1.0 for x in q)


def test_fdr_known_values():
    # Classic BH example
    pvals = [0.01, 0.02, 0.03, 0.04, 0.05]
    res = apply_fdr_correction(pvals)
    # smallest q = 0.01 * 5 / 1 = 0.05
    assert res["qvalues"][0] == pytest.approx(0.05, abs=1e-9)


def test_fdr_empty():
    res = apply_fdr_correction([])
    assert res["qvalues"] == []
