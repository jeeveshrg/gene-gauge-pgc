"""End-to-end analysis pipeline orchestration.

Given a set of dataset/config selections and analysis parameters, this runs:
    load -> normalize -> extract significant -> map to genes ->
    pairwise variant overlap -> pairwise gene overlap (+FDR) -> enrichment
and assembles a fully serializable result dict (consumed by the API and the
report generator).
"""

from __future__ import annotations

import itertools
import platform
from datetime import datetime, timezone
from typing import Any

from app import __version__, config
from app.analysis import gene_mapping
from app.analysis.enrichment import load_genesets, run_pathway_enrichment
from app.analysis.gene_overlap import apply_fdr_correction, compute_gene_overlap
from app.analysis.significant_variants import extract_significant_variants
from app.analysis.variant_overlap import compare_variant_overlap
from app.data_sources.huggingface_loader import load_pgc_dataset
from app.normalization.schema_normalizer import normalize_gwas_schema
from app.reports.report_generator import LIMITATIONS

MAX_VARIANT_PREVIEW = 100


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _selection_frame_to_records(frame, limit: int = MAX_VARIANT_PREVIEW) -> list[dict[str, Any]]:
    return frame.head(limit).to_dicts()


def run_analysis(
    analysis_id: str,
    selections: list[dict[str, str]],
    *,
    significance_method: str = "genome_wide",
    top_k: int | None = None,
    custom_threshold: float | None = None,
    mapping_method: str = "window_10kb",
    run_enrichment: bool = True,
    enrichment_alpha: float = 0.05,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Execute the full analysis for a list of {dataset_id, config_id} selections."""
    created_at = created_at or _now()
    annotation = gene_mapping.load_gene_annotation()
    universe_genes = set(annotation.get_column("gene_symbol").to_list())
    genesets = load_genesets() if run_enrichment else []

    per_dataset: list[dict[str, Any]] = []
    sig_frames: dict[str, Any] = {}  # disorder_key -> significant frame
    gene_sets_by_disorder: dict[str, set[str]] = {}
    threshold_used: float | None = None

    for sel in selections:
        dataset_id = sel["dataset_id"]
        config_id = sel["config_id"]
        loaded = load_pgc_dataset(dataset_id, config_id)
        norm = normalize_gwas_schema(loaded)

        sig = extract_significant_variants(
            norm.frame,
            method=significance_method,
            k=top_k,
            custom_threshold=custom_threshold,
        )
        threshold_used = sig.threshold

        mapres = gene_mapping.map_variants_to_genes(
            sig.frame, annotation=annotation, method=mapping_method
        )

        disorder = loaded.disorder
        # Disambiguate if two selections share a disorder label.
        key = disorder
        i = 2
        while key in sig_frames:
            key = f"{disorder} ({config_id})"
            if key in sig_frames:
                key = f"{disorder} #{i}"
                i += 1
        sig_frames[key] = sig.frame
        gene_sets_by_disorder[key] = set(mapres.genes)

        per_dataset.append(
            {
                "dataset_id": dataset_id,
                "config_id": config_id,
                "disorder": key,
                "publication": loaded.publication,
                "source": loaded.source,
                "source_ref": loaded.source_ref,
                "n_total_variants": loaded.n_rows,
                "n_significant": sig.n_selected,
                "n_genes": len(mapres.genes),
                "genes": mapres.genes,
                "significant_variants": _selection_frame_to_records(sig.frame),
                "mapping_summary": mapres.to_summary(),
                "normalization": {
                    "column_mapping": norm.column_mapping,
                    "warnings": norm.warnings,
                    "effect_encoding": norm.effect_encoding,
                },
            }
        )

    # --- pairwise overlaps ------------------------------------------------
    variant_overlaps: list[dict[str, Any]] = []
    gene_overlaps: list[dict[str, Any]] = []
    keys = list(sig_frames.keys())
    for a, b in itertools.combinations(keys, 2):
        vo = compare_variant_overlap(
            sig_frames[a], sig_frames[b], disorder_a=a, disorder_b=b
        )
        variant_overlaps.append(vo.to_dict())

        go = compute_gene_overlap(
            gene_sets_by_disorder[a],
            gene_sets_by_disorder[b],
            universe_size=len(universe_genes),
            disorder_a=a,
            disorder_b=b,
        )
        gene_overlaps.append(go.to_dict())

    # FDR across all gene-overlap pair p-values.
    if gene_overlaps:
        fdr = apply_fdr_correction(
            [g["hypergeometric_p"] for g in gene_overlaps], alpha=enrichment_alpha
        )
        for g, q, rej in zip(gene_overlaps, fdr["qvalues"], fdr["rejected"]):
            g["q_value"] = q
            g["significant"] = bool(rej)

    # --- enrichment per disorder -----------------------------------------
    enrichment: dict[str, Any] = {"enabled": run_enrichment, "per_disorder": {}}
    if run_enrichment:
        for key, genes in gene_sets_by_disorder.items():
            enrichment["per_disorder"][key] = run_pathway_enrichment(
                sorted(genes), genesets=genesets, universe=universe_genes, alpha=enrichment_alpha
            )

    reproducibility = {
        "app_version": __version__,
        "python_version": platform.python_version(),
        "generated_at": created_at,
        "significance_method": significance_method,
        "significance_threshold": threshold_used,
        "mapping_method": mapping_method,
        "annotation_file": str(config.GENE_ANNOTATION_FILE.name),
        "geneset_file": str(config.GENESET_GMT_FILE.name),
        "demo_mode": config.is_demo_mode(),
        "dataset_sources": [d["source_ref"] for d in per_dataset],
    }

    return {
        "id": analysis_id,
        "created_at": created_at,
        "status": "completed",
        "params": {
            "selections": selections,
            "demo_mode": config.is_demo_mode(),
            "significance": {
                "method": significance_method,
                "threshold": threshold_used,
                "k": top_k,
            },
            "mapping": {
                "method": mapping_method,
                "window": gene_mapping._METHOD_WINDOWS.get(mapping_method),
            },
            "enrichment": {"enabled": run_enrichment, "alpha": enrichment_alpha},
        },
        "per_dataset": per_dataset,
        "variant_overlaps": variant_overlaps,
        "gene_overlaps": gene_overlaps,
        "enrichment": enrichment,
        "reproducibility": reproducibility,
        "limitations": LIMITATIONS,
    }
