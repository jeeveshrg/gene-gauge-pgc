import polars as pl

from app.analysis.variant_overlap import compare_variant_overlap, compute_jaccard


def test_compute_jaccard_basic():
    assert compute_jaccard({1, 2, 3}, {2, 3, 4}) == 2 / 4
    assert compute_jaccard(set(), set()) == 0.0
    assert compute_jaccard({1}, set()) == 0.0
    assert compute_jaccard({1, 2}, {1, 2}) == 1.0


def _frame(rsids, chrom, pos, beta, ea, oa):
    return pl.DataFrame(
        {
            "rsid": rsids,
            "chromosome": chrom,
            "position": pos,
            "beta": beta,
            "effect_allele": ea,
            "other_allele": oa,
        }
    )


def test_variant_overlap_shared_rsids_and_positions():
    a = _frame(["rs1", "rs2", "rs3"], ["1", "1", "2"], [10, 20, 30],
               [0.1, 0.2, 0.3], ["A", "A", "A"], ["G", "G", "G"])
    b = _frame(["rs2", "rs3", "rs4"], ["1", "2", "3"], [20, 30, 40],
               [0.2, -0.3, 0.4], ["A", "A", "A"], ["G", "G", "G"])
    res = compare_variant_overlap(a, b, disorder_a="A", disorder_b="B")
    assert res.shared_rsids == ["rs2", "rs3"]
    assert res.overlap_count == 2
    assert res.jaccard_rsid == 2 / 4
    assert "1:20" in res.shared_positions and "2:30" in res.shared_positions


def test_direction_concordance_with_flip():
    # rs1: same alleles, both positive -> concordant
    # rs2: flipped alleles, signs opposite raw but aligned -> concordant
    # rs3: same alleles, opposite signs -> discordant
    a = _frame(["rs1", "rs2", "rs3"], ["1", "1", "1"], [1, 2, 3],
               [0.5, 0.5, 0.5], ["A", "A", "A"], ["G", "G", "G"])
    b = _frame(["rs1", "rs2", "rs3"], ["1", "1", "1"], [1, 2, 3],
               [0.5, -0.5, -0.5], ["A", "G", "A"], ["G", "A", "G"])
    res = compare_variant_overlap(a, b)
    dc = res.direction
    assert dc.n_comparable == 3
    assert dc.n_concordant == 2  # rs1 and flipped rs2
    assert dc.n_discordant == 1
    assert dc.concordance_rate == 2 / 3


def test_no_shared_variants():
    a = _frame(["rs1"], ["1"], [10], [0.1], ["A"], ["G"])
    b = _frame(["rs9"], ["9"], [90], [0.1], ["A"], ["G"])
    res = compare_variant_overlap(a, b)
    assert res.overlap_count == 0
    assert res.jaccard_rsid == 0.0
    assert res.direction.concordance_rate is None
