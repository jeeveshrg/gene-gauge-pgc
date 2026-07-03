#!/usr/bin/env python3
"""Run a demo GeneGauge PGC analysis end-to-end and write a Markdown report.

Usage:
    python scripts/run_demo_analysis.py

Runs a 3-disorder (SCZ / BIP / MDD) overlap analysis on the bundled mock data
and writes `demo_report.md` next to this script's parent directory.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make the backend root importable and force demo mode.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("GENEGAUGE_DEMO_MODE", "1")

from app.pipeline import run_analysis  # noqa: E402
from app.reports.report_generator import write_markdown_report  # noqa: E402


def main() -> None:
    result = run_analysis(
        "demo-scz-bip-mdd",
        [
            {"dataset_id": "pgc-schizophrenia", "config_id": "scz2022"},
            {"dataset_id": "pgc-bipolar", "config_id": "bip2021"},
            {"dataset_id": "pgc-mdd", "config_id": "mdd2019"},
        ],
        significance_method="genome_wide",
        mapping_method="window_10kb",
        run_enrichment=True,
    )

    print("Disorders analyzed:")
    for d in result["per_dataset"]:
        print(f"  - {d['disorder']}: {d['n_significant']} significant variants, "
              f"{d['n_genes']} mapped genes")

    print("\nGene overlaps:")
    for o in result["gene_overlaps"]:
        print(f"  - {o['disorder_a']} vs {o['disorder_b']}: "
              f"{o['n_shared']} shared "
              f"(p={o['hypergeometric_p']:.3e}, q={o.get('q_value'):.3e}) "
              f"{o['shared_genes']}")

    out = BACKEND_ROOT / "demo_report.md"
    write_markdown_report(result, out)
    print(f"\nMarkdown report written to: {out}")


if __name__ == "__main__":
    main()
