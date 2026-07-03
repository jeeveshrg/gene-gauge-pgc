"""Reproducible Markdown (and optional PDF) report generation.

A report always documents: datasets + configs used, significance thresholds,
the variant-to-gene mapping method, all overlap/enrichment results, explicit
limitations, and reproducibility metadata. This is required so results can be
audited and regenerated.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

LIMITATIONS = [
    "These are GWAS summary statistics, not curated gene lists. All gene-level "
    "results derive from positional mapping of significant variants.",
    "Positional variant-to-gene mapping does NOT establish causality. A mapped "
    "gene is a positional candidate; the true causal gene may differ (e.g. via "
    "long-range regulatory effects).",
    "Overlap between disorders at the SNP, gene, or pathway level does not imply "
    "shared biology, shared causal mechanism, or clinical relationship.",
    "No clinical or diagnostic claims are made. This tool does not predict "
    "individual disorder risk.",
    "Demo mode uses small bundled mock datasets and a tiny gene annotation; "
    "results are illustrative only and must not be interpreted biologically.",
    "Enrichment uses a limited bundled gene-set collection and a restricted gene "
    "universe; p-values are conditional on these choices.",
]


def _fmt_p(p: float | None) -> str:
    if p is None:
        return "NA"
    if p == 0:
        return "0"
    if p < 1e-3 or p > 1e3:
        return f"{p:.3e}"
    return f"{p:.4g}"


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def generate_markdown_report(analysis: dict[str, Any]) -> str:
    """Render a full analysis result dict to a Markdown report string."""
    params = analysis.get("params", {})
    repro = analysis.get("reproducibility", {})
    lines: list[str] = []

    lines.append("# GeneGauge PGC — Psychiatric GWAS Overlap Report")
    lines.append("")
    lines.append(f"**Analysis ID:** `{analysis.get('id', 'NA')}`  ")
    lines.append(f"**Generated:** {analysis.get('created_at', 'NA')}  ")
    lines.append(f"**Mode:** {'DEMO (mock data)' if params.get('demo_mode') else 'live'}  ")
    lines.append("")
    lines.append(
        "> ⚠️ **Scientific scope.** These are GWAS summary statistics, not gene "
        "lists. Gene- and pathway-level results derive from positional mapping "
        "and do not establish causality or clinical relevance."
    )
    lines.append("")

    # --- Datasets ---------------------------------------------------------
    lines.append("## 1. Datasets & Configurations")
    lines.append("")
    ds_rows = [
        [
            d.get("disorder"),
            f"`{d.get('dataset_id')}`",
            f"`{d.get('config_id')}`",
            d.get("source", "NA"),
            d.get("publication", "NA"),
        ]
        for d in analysis.get("per_dataset", [])
    ]
    lines.append(
        _md_table(
            ["Disorder", "Dataset", "Config", "Source", "Publication"], ds_rows
        )
    )
    lines.append("")

    # --- Thresholds / methods --------------------------------------------
    sig = params.get("significance", {})
    mapp = params.get("mapping", {})
    lines.append("## 2. Methods & Thresholds")
    lines.append("")
    lines.append(f"- **Significance method:** `{sig.get('method')}`")
    lines.append(f"- **P-value threshold:** {_fmt_p(sig.get('threshold'))}")
    if sig.get("k"):
        lines.append(f"- **Top-k:** {sig.get('k')}")
    lines.append(f"- **Variant-to-gene mapping:** `{mapp.get('method')}`"
                 + (f" (window ±{mapp.get('window')} bp)" if mapp.get("window") else ""))
    lines.append(f"- **Enrichment:** {'enabled' if params.get('enrichment', {}).get('enabled') else 'disabled'}")
    lines.append("")

    # --- Per-dataset significant variants --------------------------------
    lines.append("## 3. Significant Variants & Mapped Genes")
    lines.append("")
    per_rows = [
        [
            d.get("disorder"),
            d.get("n_total_variants"),
            d.get("n_significant"),
            d.get("n_genes"),
        ]
        for d in analysis.get("per_dataset", [])
    ]
    lines.append(
        _md_table(
            ["Disorder", "Total variants", "Significant", "Mapped genes"], per_rows
        )
    )
    lines.append("")
    for d in analysis.get("per_dataset", []):
        genes = d.get("genes", [])
        lines.append(f"**{d.get('disorder')} mapped genes ({len(genes)}):** "
                     + (", ".join(f"`{g}`" for g in genes) if genes else "_none_"))
    lines.append("")

    # --- Variant overlap --------------------------------------------------
    v_overlaps = analysis.get("variant_overlaps", [])
    if v_overlaps:
        lines.append("## 4. Pairwise Variant Overlap")
        lines.append("")
        rows = []
        for o in v_overlaps:
            dc = o.get("direction_concordance", {})
            rate = dc.get("concordance_rate")
            rows.append(
                [
                    f"{o['disorder_a']} vs {o['disorder_b']}",
                    o["overlap_count"],
                    f"{o['jaccard_rsid']:.3f}",
                    f"{o['jaccard_position']:.3f}",
                    f"{dc.get('n_concordant', 0)}/{dc.get('n_comparable', 0)}"
                    + (f" ({rate:.0%})" if rate is not None else ""),
                ]
            )
        lines.append(
            _md_table(
                ["Pair", "Shared rsIDs", "Jaccard (rsID)", "Jaccard (pos)", "Concordant dir."],
                rows,
            )
        )
        lines.append("")

    # --- Gene overlap -----------------------------------------------------
    g_overlaps = analysis.get("gene_overlaps", [])
    if g_overlaps:
        lines.append("## 5. Pairwise Gene Overlap")
        lines.append("")
        rows = []
        for o in g_overlaps:
            rows.append(
                [
                    f"{o['disorder_a']} vs {o['disorder_b']}",
                    o["n_shared"],
                    f"{o['jaccard']:.3f}",
                    _fmt_p(o["hypergeometric_p"]),
                    _fmt_p(o.get("q_value")),
                    ", ".join(f"`{g}`" for g in o["shared_genes"]) or "_none_",
                ]
            )
        lines.append(
            _md_table(
                ["Pair", "Shared genes", "Jaccard", "Hypergeom. p", "FDR q", "Genes"],
                rows,
            )
        )
        lines.append("")

    # --- Enrichment -------------------------------------------------------
    enr = analysis.get("enrichment", {})
    per_disorder = enr.get("per_disorder", {})
    if per_disorder:
        lines.append("## 6. Pathway Enrichment (over-representation)")
        lines.append("")
        for disorder, res in per_disorder.items():
            lines.append(f"### {disorder}")
            results = res.get("results", [])[:10]
            if not results:
                lines.append("_No enriched terms._")
                lines.append("")
                continue
            rows = [
                [
                    f"`{r['term']}`",
                    r["source"],
                    r["overlap_size"],
                    r["n_term_genes"],
                    _fmt_p(r["p_value"]),
                    _fmt_p(r.get("q_value")),
                ]
                for r in results
            ]
            lines.append(
                _md_table(
                    ["Term", "Source", "Overlap", "Term size", "p", "FDR q"], rows
                )
            )
            lines.append("")

    # --- Limitations ------------------------------------------------------
    lines.append("## 7. Limitations")
    lines.append("")
    for lim in analysis.get("limitations", LIMITATIONS):
        lines.append(f"- {lim}")
    lines.append("")

    # --- Reproducibility --------------------------------------------------
    lines.append("## 8. Reproducibility Metadata")
    lines.append("")
    for key in [
        "app_version",
        "python_version",
        "generated_at",
        "significance_method",
        "significance_threshold",
        "mapping_method",
        "annotation_file",
        "geneset_file",
        "demo_mode",
    ]:
        if key in repro:
            lines.append(f"- **{key}:** `{repro[key]}`")
    if repro.get("dataset_sources"):
        lines.append("- **dataset_sources:**")
        for s in repro["dataset_sources"]:
            lines.append(f"    - `{s}`")
    lines.append("")

    return "\n".join(lines)


def write_markdown_report(analysis: dict[str, Any], path: str | Path) -> Path:
    md = generate_markdown_report(analysis)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(md, encoding="utf-8")
    return path


def generate_pdf_report(analysis: dict[str, Any], path: str | Path) -> Path | None:
    """Optional PDF export. Returns None if no PDF backend is available.

    Uses matplotlib as a lightweight, dependency-light PDF writer when present.
    """
    md = generate_markdown_report(analysis)
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
    except Exception:
        return None

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Paginate the markdown text into simple text pages.
    lines = md.splitlines()
    per_page = 48
    with PdfPages(path) as pdf:
        for start in range(0, len(lines), per_page):
            chunk = lines[start : start + per_page]
            fig = plt.figure(figsize=(8.27, 11.69))  # A4
            fig.text(
                0.05,
                0.98,
                "\n".join(chunk),
                va="top",
                ha="left",
                family="monospace",
                fontsize=7,
            )
            plt.axis("off")
            pdf.savefig(fig)
            plt.close(fig)
    return path
