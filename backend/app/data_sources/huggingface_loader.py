"""Load PGC GWAS summary-statistic datasets from Hugging Face or local mock data.

Design goals:
  * Never load billions of rows into pandas. Loading returns a Polars LazyFrame
    (or DataFrame) so that downstream steps can push filters/projections down.
  * Degrade gracefully to bundled mock data when Hugging Face is unavailable
    or no HF token is configured (demo mode).
  * Provide raw schema inspection without normalization so the UI can show the
    provider's original column names.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

from app import config


@dataclass
class LoadedDataset:
    """Container for a loaded (raw, un-normalized) GWAS dataset."""

    dataset_id: str
    config_id: str
    disorder: str
    publication: str
    source: str  # "huggingface" | "mock"
    source_ref: str  # HF repo or mock file path
    frame: pl.DataFrame

    @property
    def n_rows(self) -> int:
        return self.frame.height


def _load_mock(dataset_id: str, config_id: str) -> LoadedDataset:
    entry = config.get_dataset(dataset_id)
    cfg = config.get_config(dataset_id, config_id)
    path = config.MOCK_DIR / cfg.mock_file
    if not path.exists():
        raise FileNotFoundError(f"Mock data file not found: {path}")
    # Read all columns as strings first; the normalizer handles typing so that
    # heterogeneous provider schemas do not break parsing.
    frame = pl.read_csv(path, infer_schema_length=0)
    return LoadedDataset(
        dataset_id=dataset_id,
        config_id=config_id,
        disorder=entry.disorder,
        publication=entry.publication,
        source="mock",
        source_ref=str(path),
        frame=frame,
    )


def _load_huggingface(dataset_id: str, config_id: str, limit: int | None) -> LoadedDataset:
    """Load a config from Hugging Face using streaming to avoid huge memory use.

    Raises ImportError/Exception if the ``datasets`` package or network is not
    available; callers fall back to mock data.
    """
    from datasets import load_dataset  # imported lazily; heavy optional dep

    entry = config.get_dataset(dataset_id)
    # Stream to avoid materializing the full (potentially >1e8 row) dataset.
    stream = load_dataset(entry.hf_repo, config_id, split="train", streaming=True)
    rows: list[dict[str, Any]] = []
    cap = limit if limit is not None else 500_000
    for i, row in enumerate(stream):
        if i >= cap:
            break
        rows.append(row)
    frame = pl.DataFrame(rows)
    return LoadedDataset(
        dataset_id=dataset_id,
        config_id=config_id,
        disorder=entry.disorder,
        publication=entry.publication,
        source="huggingface",
        source_ref=f"{entry.hf_repo}:{config_id}",
        frame=frame,
    )


def load_pgc_dataset(
    dataset_id: str,
    config_id: str,
    *,
    limit: int | None = None,
    force_mock: bool | None = None,
) -> LoadedDataset:
    """Load a PGC dataset config as a raw Polars DataFrame.

    Parameters
    ----------
    dataset_id, config_id:
        Catalog identifiers (see :mod:`app.config`).
    limit:
        Optional cap on the number of rows read (useful for previews).
    force_mock:
        If True, always use bundled mock data. If None, the decision follows
        :func:`app.config.is_demo_mode`.
    """
    use_mock = config.is_demo_mode() if force_mock is None else force_mock
    if not use_mock:
        try:
            return _load_huggingface(dataset_id, config_id, limit)
        except Exception:
            # Network/credential/dependency failure -> transparent mock fallback.
            pass
    loaded = _load_mock(dataset_id, config_id)
    if limit is not None:
        loaded.frame = loaded.frame.head(limit)
    return loaded


def inspect_schema(loaded: LoadedDataset) -> dict[str, Any]:
    """Return raw schema information for a loaded dataset (pre-normalization)."""
    frame = loaded.frame
    columns = []
    for name, dtype in frame.schema.items():
        non_null = int(frame[name].is_not_null().sum())
        sample_values = [
            v for v in frame[name].head(3).to_list() if v is not None
        ]
        columns.append(
            {
                "name": name,
                "dtype": str(dtype),
                "non_null": non_null,
                "sample_values": [str(v) for v in sample_values],
            }
        )
    return {
        "dataset_id": loaded.dataset_id,
        "config_id": loaded.config_id,
        "disorder": loaded.disorder,
        "source": loaded.source,
        "source_ref": loaded.source_ref,
        "n_rows": loaded.n_rows,
        "n_columns": len(columns),
        "columns": columns,
    }


def list_datasets() -> list[dict[str, Any]]:
    """Return the dataset catalog as serializable dicts."""
    out = []
    for entry in config.DATASET_CATALOG.values():
        out.append(
            {
                "dataset_id": entry.dataset_id,
                "disorder": entry.disorder,
                "publication": entry.publication,
                "hf_repo": entry.hf_repo,
                "description": entry.description,
                "n_configs": len(entry.configs),
                "demo_mode": config.is_demo_mode(),
            }
        )
    return out


def list_configs(dataset_id: str) -> list[dict[str, Any]]:
    entry = config.get_dataset(dataset_id)
    return [
        {
            "config_id": cfg.config_id,
            "description": cfg.description,
            "build": cfg.build,
            "dataset_id": dataset_id,
            "disorder": entry.disorder,
        }
        for cfg in entry.configs
    ]
