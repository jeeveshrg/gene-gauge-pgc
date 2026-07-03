"""Pathway / gene-set over-representation analysis (ORA).

For a query gene list, each gene set is tested for over-representation using the
hypergeometric distribution, then p-values are FDR-corrected (Benjamini-Hochberg).

This is a self-contained ORA equivalent to Enrichr/gseapy's hypergeometric test,
so demo mode has no heavy external dependency. If ``gseapy`` is installed and a
network is available, richer libraries can be swapped in behind the same API.

Gene-set sources supported via bundled GMT: GO Biological Process, Reactome.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app import config
from app.analysis.gene_overlap import (
    apply_fdr_correction,
    compute_hypergeometric_p_value,
)


@dataclass
class GeneSet:
    name: str
    description: str
    genes: set[str]

    @property
    def source(self) -> str:
        n = self.name.upper()
        if n.startswith("GOBP") or n.startswith("GO_") or n.startswith("GOBP_"):
            return "GO:BP"
        if n.startswith("REACTOME"):
            return "Reactome"
        if n.startswith("KEGG"):
            return "KEGG"
        return "Other"


def load_genesets(path: str | Path | None = None) -> list[GeneSet]:
    """Parse a GMT file into gene sets (name<TAB>description<TAB>gene1<TAB>...)."""
    path = Path(path) if path else config.GENESET_GMT_FILE
    if not Path(path).exists():
        raise FileNotFoundError(f"Gene-set GMT file not found: {path}")
    sets: list[GeneSet] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            name, desc, *genes = parts
            gene_set = {g.strip().upper() for g in genes if g.strip()}
            if gene_set:
                sets.append(GeneSet(name=name, description=desc, genes=gene_set))
    return sets


def _default_universe(genesets: list[GeneSet]) -> set[str]:
    universe: set[str] = set()
    for gs in genesets:
        universe |= gs.genes
    return universe


def run_pathway_enrichment(
    gene_list: list[str],
    genesets: list[GeneSet] | None = None,
    *,
    universe: set[str] | None = None,
    alpha: float = 0.05,
    min_overlap: int = 1,
) -> dict[str, Any]:
    """Run hypergeometric over-representation analysis on a query gene list.

    Returns a dict with per-term results (sorted by ascending p-value, then
    q-value) plus metadata describing the test.
    """
    if genesets is None:
        genesets = load_genesets()
    if universe is None:
        universe = _default_universe(genesets)

    query = {g.strip().upper() for g in gene_list if g and g.strip()}
    # Restrict query to the annotated universe (standard ORA practice).
    query_in_universe = query & universe
    universe_size = len(universe)

    rows: list[dict[str, Any]] = []
    for gs in genesets:
        overlap = sorted(query_in_universe & gs.genes)
        if len(overlap) < min_overlap:
            continue
        p = compute_hypergeometric_p_value(
            shared=len(overlap),
            n_a=len(gs.genes & universe),
            n_b=len(query_in_universe),
            universe_size=universe_size,
        )
        rows.append(
            {
                "term": gs.name,
                "source": gs.source,
                "description": gs.description,
                "n_term_genes": len(gs.genes & universe),
                "overlap_genes": overlap,
                "overlap_size": len(overlap),
                "p_value": p,
            }
        )

    # FDR correction across tested terms.
    if rows:
        fdr = apply_fdr_correction([r["p_value"] for r in rows], alpha=alpha)
        for r, q, rej in zip(rows, fdr["qvalues"], fdr["rejected"]):
            r["q_value"] = q
            r["significant"] = bool(rej)
    rows.sort(key=lambda r: (r["p_value"], r.get("q_value", 1.0)))

    return {
        "n_query_genes": len(query),
        "n_query_in_universe": len(query_in_universe),
        "universe_size": universe_size,
        "n_terms_tested": len(rows),
        "alpha": alpha,
        "results": rows,
    }
