import polars as pl
import pytest

from app.data_sources.huggingface_loader import LoadedDataset, load_pgc_dataset
from app.normalization.schema_normalizer import (
    MissingPValueError,
    NORMALIZED_COLUMNS,
    detect_columns,
    normalize_gwas_schema,
)


def _loaded(frame: pl.DataFrame) -> LoadedDataset:
    return LoadedDataset(
        dataset_id="test",
        config_id="cfg",
        disorder="Test Disorder",
        publication="Test et al.",
        source="mock",
        source_ref="mem",
        frame=frame,
    )


def test_detect_columns_prefers_canonical_names():
    cols = ["effect_allele", "a1", "P", "chr", "bp"]
    mapping = detect_columns(cols)
    assert mapping["effect_allele"] == "effect_allele"  # canonical beats a1
    assert mapping["p_value"] == "P"
    assert mapping["chromosome"] == "chr"
    assert mapping["position"] == "bp"


def test_normalize_odds_ratio_dataset_produces_all_columns():
    loaded = load_pgc_dataset("pgc-schizophrenia", "scz2022", force_mock=True)
    result = normalize_gwas_schema(loaded)
    assert result.frame.columns == NORMALIZED_COLUMNS
    assert result.effect_encoding == "odds_ratio"
    # beta derived from OR = ln(OR)
    row = result.frame.filter(pl.col("rsid") == "rs1000001").to_dicts()[0]
    assert row["odds_ratio"] == pytest.approx(1.12, rel=1e-6)
    assert row["beta"] == pytest.approx(0.11333, abs=1e-3)


def test_normalize_beta_dataset_derives_odds_ratio():
    loaded = load_pgc_dataset("pgc-bipolar", "bip2021", force_mock=True)
    result = normalize_gwas_schema(loaded)
    assert result.effect_encoding in {"beta", "log_odds"}
    row = result.frame.filter(pl.col("rsid") == "rs1000001").to_dicts()[0]
    assert row["beta"] == pytest.approx(0.11, rel=1e-6)
    # odds_ratio = exp(beta)
    assert row["odds_ratio"] == pytest.approx(1.1163, abs=1e-3)


def test_chromosome_prefix_stripped_and_alleles_uppercased():
    frame = pl.DataFrame(
        {
            "SNP": ["rsX"],
            "chr": ["chr7"],
            "bp": ["100"],
            "a1": ["a"],
            "a2": ["g"],
            "beta": ["0.1"],
            "se": ["0.01"],
            "P": ["1e-9"],
            "N": ["1000"],
        }
    )
    result = normalize_gwas_schema(_loaded(frame))
    row = result.frame.to_dicts()[0]
    assert row["chromosome"] == "7"
    assert row["effect_allele"] == "A"
    assert row["other_allele"] == "G"
    assert row["variant_id"] == "7:100:G:A"


def test_missing_p_value_column_raises():
    frame = pl.DataFrame(
        {"SNP": ["rs1"], "chr": ["1"], "bp": ["10"], "beta": ["0.1"]}
    )
    with pytest.raises(MissingPValueError):
        normalize_gwas_schema(_loaded(frame))


def test_out_of_range_pvalue_warning():
    frame = pl.DataFrame(
        {
            "SNP": ["rs1", "rs2"],
            "chr": ["1", "1"],
            "bp": ["10", "20"],
            "a1": ["A", "A"],
            "a2": ["G", "G"],
            "or": ["1.1", "1.2"],
            "P": ["0.5", "5"],  # second is out of range
        }
    )
    result = normalize_gwas_schema(_loaded(frame))
    assert any("out-of-range" in w for w in result.warnings)
