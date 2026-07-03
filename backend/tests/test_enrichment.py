from app.analysis.enrichment import load_genesets, run_pathway_enrichment


def test_load_genesets():
    sets = load_genesets()
    assert len(sets) >= 4
    names = {s.name for s in sets}
    assert "GOBP_SYNAPTIC_SIGNALING" in names
    sources = {s.source for s in sets}
    assert "GO:BP" in sources and "Reactome" in sources


def test_enrichment_detects_calcium_pathway():
    # CACNA1C, CACNB2, ANK3 are the full calcium ion transport set.
    res = run_pathway_enrichment(["CACNA1C", "CACNB2", "ANK3"])
    terms = {r["term"]: r for r in res["results"]}
    assert "GOBP_CALCIUM_ION_TRANSPORT" in terms
    ca = terms["GOBP_CALCIUM_ION_TRANSPORT"]
    assert ca["overlap_size"] == 3
    assert ca["p_value"] <= 1.0
    # results sorted ascending by p-value
    pvals = [r["p_value"] for r in res["results"]]
    assert pvals == sorted(pvals)


def test_enrichment_reports_qvalues():
    res = run_pathway_enrichment(["CACNA1C", "DRD2", "GRIN2A"])
    for r in res["results"]:
        assert "q_value" in r
        assert 0.0 <= r["q_value"] <= 1.0


def test_enrichment_empty_query():
    res = run_pathway_enrichment([])
    assert res["n_query_genes"] == 0
    assert res["results"] == []
