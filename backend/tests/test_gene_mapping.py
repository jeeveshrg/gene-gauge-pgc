import polars as pl
import pytest

from app.analysis.gene_mapping import load_gene_annotation, map_variants_to_genes


@pytest.fixture(scope="module")
def annotation():
    return load_gene_annotation()


def _variants(rows):
    return pl.DataFrame(
        {
            "variant_id": [r[0] for r in rows],
            "rsid": [r[0] for r in rows],
            "chromosome": [r[1] for r in rows],
            "position": [r[2] for r in rows],
        }
    )


def test_gene_body_mapping(annotation):
    # CACNA1C is chr12:2,000,000-2,700,000
    v = _variants([("rsA", "12", 2350000)])
    res = map_variants_to_genes(v, annotation, method="gene_body")
    assert "CACNA1C" in res.genes
    assert res.n_mapped_variants == 1
    dist = res.mappings.filter(pl.col("gene_symbol") == "CACNA1C")["distance"][0]
    assert dist == 0


def test_window_mapping_includes_flanking(annotation):
    # 5kb upstream of CACNA1C start (2,000,000) -> in +/-10kb but not gene body
    v = _variants([("rsB", "12", 1_995_000)])
    body = map_variants_to_genes(v, annotation, method="gene_body")
    win = map_variants_to_genes(v, annotation, method="window_10kb")
    assert "CACNA1C" not in body.genes
    assert "CACNA1C" in win.genes


def test_nearest_returns_single_gene(annotation):
    v = _variants([("rsC", "12", 5_000_000)])  # far from CACNA1C but same chrom
    res = map_variants_to_genes(v, annotation, method="nearest")
    assert res.mappings.height == 1
    assert res.mappings["gene_symbol"][0] == "CACNA1C"
    assert res.mappings["distance"][0] > 0


def test_unmapped_variant(annotation):
    # chromosome not in annotation
    v = _variants([("rsD", "22", 1000)])
    res = map_variants_to_genes(v, annotation, method="window_50kb")
    assert res.n_mapped_variants == 0
    assert res.n_unmapped_variants == 1


def test_invalid_method_raises(annotation):
    v = _variants([("rsE", "1", 100)])
    with pytest.raises(ValueError):
        map_variants_to_genes(v, annotation, method="telepathy")
