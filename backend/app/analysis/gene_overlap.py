"""Gene-level overlap statistics between disorders.

Provides:
  * Jaccard similarity of mapped-gene sets (re-exported from variant_overlap).
  * Hypergeometric enrichment p-value for observing >= k shared genes by chance.
  * Benjamini-Hochberg FDR correction across a set of p-values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import numpy as np
from scipy.stats import hypergeom

from app.analysis.variant_overlap import compute_jaccard

__all__ = [
    "compute_jaccard",
    "compute_gene_overlap",
    "compute_hypergeometric_p_value",
    "apply_fdr_correction",
    "GeneOverlapResult",
]


@dataclass
class GeneOverlapResult:
    disorder_a: str
    disorder_b: str
    n_genes_a: int
    n_genes_b: int
    shared_genes: list[str]
    n_shared: int
    jaccard: float
    universe_size: int
    hypergeometric_p: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "disorder_a": self.disorder_a,
            "disorder_b": self.disorder_b,
            "n_genes_a": self.n_genes_a,
            "n_genes_b": self.n_genes_b,
            "shared_genes": self.shared_genes,
            "n_shared": self.n_shared,
            "jaccard": self.jaccard,
            "universe_size": self.universe_size,
            "hypergeometric_p": self.hypergeometric_p,
        }


def compute_hypergeometric_p_value(
    shared: int, n_a: int, n_b: int, universe_size: int
) -> float:
    """P(X >= shared) of overlap between two gene sets drawn from a universe.

    Uses the survival function of the hypergeometric distribution:
    drawing ``n_b`` genes from a universe of ``universe_size`` that contains
    ``n_a`` "successes", the probability of at least ``shared`` hits.
    """
    if universe_size <= 0 or n_a <= 0 or n_b <= 0:
        return 1.0
    if shared <= 0:
        return 1.0
    n_a = min(n_a, universe_size)
    n_b = min(n_b, universe_size)
    shared = min(shared, n_a, n_b)
    # sf(k-1) = P(X >= k)
    p = float(hypergeom.sf(shared - 1, universe_size, n_a, n_b))
    return max(0.0, min(1.0, p))


def apply_fdr_correction(
    pvalues: Sequence[float], alpha: float = 0.05
) -> dict[str, Any]:
    """Benjamini-Hochberg FDR correction.

    Returns adjusted q-values (monotone, capped at 1.0) and a rejection mask
    at level ``alpha``. Order of inputs is preserved in the output.
    """
    p = np.asarray(list(pvalues), dtype=float)
    n = p.size
    if n == 0:
        return {"qvalues": [], "rejected": [], "alpha": alpha}

    order = np.argsort(p, kind="mergesort")
    ranked = p[order]
    ranks = np.arange(1, n + 1)
    q_sorted = ranked * n / ranks
    # Enforce monotonicity from the largest p-value downward.
    q_sorted = np.minimum.accumulate(q_sorted[::-1])[::-1]
    q_sorted = np.clip(q_sorted, 0.0, 1.0)

    qvalues = np.empty(n, dtype=float)
    qvalues[order] = q_sorted
    rejected = qvalues <= alpha
    return {
        "qvalues": qvalues.tolist(),
        "rejected": rejected.tolist(),
        "alpha": alpha,
    }


def compute_gene_overlap(
    genes_a: Iterable[str],
    genes_b: Iterable[str],
    universe_size: int,
    *,
    disorder_a: str = "A",
    disorder_b: str = "B",
) -> GeneOverlapResult:
    """Compute gene-set overlap statistics for a pair of disorders."""
    set_a = {g for g in genes_a if g}
    set_b = {g for g in genes_b if g}
    shared = sorted(set_a & set_b)

    universe_size = max(universe_size, len(set_a | set_b))
    hyper_p = compute_hypergeometric_p_value(
        len(shared), len(set_a), len(set_b), universe_size
    )
    return GeneOverlapResult(
        disorder_a=disorder_a,
        disorder_b=disorder_b,
        n_genes_a=len(set_a),
        n_genes_b=len(set_b),
        shared_genes=shared,
        n_shared=len(shared),
        jaccard=compute_jaccard(set_a, set_b),
        universe_size=universe_size,
        hypergeometric_p=hyper_p,
    )
