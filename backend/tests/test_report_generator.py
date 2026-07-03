from app.pipeline import run_analysis
from app.reports.report_generator import (
    generate_markdown_report,
    write_markdown_report,
)


def _run():
    return run_analysis(
        "test-analysis-1",
        [
            {"dataset_id": "pgc-schizophrenia", "config_id": "scz2022"},
            {"dataset_id": "pgc-bipolar", "config_id": "bip2021"},
        ],
        significance_method="genome_wide",
        mapping_method="window_10kb",
    )


def test_pipeline_produces_overlaps():
    result = _run()
    assert result["status"] == "completed"
    assert len(result["per_dataset"]) == 2
    assert len(result["variant_overlaps"]) == 1
    assert len(result["gene_overlaps"]) == 1
    go = result["gene_overlaps"][0]
    # SCZ and BIP share CACNA1C, GRIN2A, TCF4, CACNB2 in the mock data.
    assert "CACNA1C" in go["shared_genes"]
    assert go["n_shared"] >= 3
    assert "q_value" in go


def test_markdown_report_contains_required_sections():
    result = _run()
    md = generate_markdown_report(result)
    for heading in [
        "# GeneGauge PGC",
        "Datasets & Configurations",
        "Methods & Thresholds",
        "Significant Variants",
        "Pairwise Variant Overlap",
        "Pairwise Gene Overlap",
        "Limitations",
        "Reproducibility Metadata",
    ]:
        assert heading in md, f"missing section: {heading}"
    # reproducibility metadata present
    assert "app_version" in md
    assert "mapping_method" in md


def test_report_documents_thresholds_and_mapping():
    result = _run()
    md = generate_markdown_report(result)
    assert "genome_wide" in md
    assert "window_10kb" in md


def test_write_markdown_report(tmp_path):
    result = _run()
    path = write_markdown_report(result, tmp_path / "report.md")
    assert path.exists()
    assert path.read_text(encoding="utf-8").startswith("# GeneGauge PGC")


def test_direction_concordance_present():
    result = _run()
    vo = result["variant_overlaps"][0]
    dc = vo["direction_concordance"]
    # SCZ vs BIP share 4 rsIDs; 3 concordant, 1 discordant (CACNB2) in mock data.
    assert dc["n_comparable"] == 4
    assert dc["n_concordant"] == 3
    assert dc["n_discordant"] == 1
