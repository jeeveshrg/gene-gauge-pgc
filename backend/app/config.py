"""Configuration and dataset catalog for GeneGauge PGC.

Environment variables (all optional — the app runs in demo/mock mode without them):
    GENEGAUGE_DEMO_MODE      "1"/"true" to force local mock data (default: auto)
    HF_TOKEN                 Hugging Face access token (enables real dataset loading)
    HF_HOME                  Hugging Face cache directory
    SUPABASE_URL             Supabase project URL (analysis persistence)
    SUPABASE_KEY             Supabase service/anon key
    GENEGAUGE_DATA_DIR       Override the bundled data directory
    GENEGAUGE_STORE_PATH     Path to the JSON analysis-history store
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("GENEGAUGE_DATA_DIR", BACKEND_ROOT / "data"))
MOCK_DIR = DATA_DIR / "mock"
PATHWAY_DIR = DATA_DIR / "pathways"

GENE_ANNOTATION_FILE = MOCK_DIR / "gene_annotation_demo.tsv"
GENESET_GMT_FILE = PATHWAY_DIR / "demo_genesets.gmt"

STORE_PATH = Path(
    os.environ.get("GENEGAUGE_STORE_PATH", BACKEND_ROOT / "data" / "analyses_store.json")
)

# ---------------------------------------------------------------------------
# Significance thresholds
# ---------------------------------------------------------------------------
GENOME_WIDE_SIGNIFICANCE = 5e-8
SUGGESTIVE_SIGNIFICANCE = 1e-5


def is_demo_mode() -> bool:
    """Return True when the app should use bundled mock data.

    Demo mode is forced by GENEGAUGE_DEMO_MODE, and is otherwise the default
    whenever no Hugging Face token is configured. This keeps the app fully
    functional offline while allowing real dataset access when credentials
    are supplied.
    """
    forced = os.environ.get("GENEGAUGE_DEMO_MODE", "").strip().lower()
    if forced in {"1", "true", "yes", "on"}:
        return True
    if forced in {"0", "false", "no", "off"}:
        return False
    # Auto: real mode only if a HF token is present.
    return not bool(os.environ.get("HF_TOKEN"))


# ---------------------------------------------------------------------------
# Dataset catalog
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DatasetConfig:
    config_id: str
    description: str
    mock_file: str
    build: str = "GRCh38"


@dataclass(frozen=True)
class DatasetEntry:
    dataset_id: str
    disorder: str
    publication: str
    hf_repo: str
    description: str
    configs: list[DatasetConfig] = field(default_factory=list)


DATASET_CATALOG: dict[str, DatasetEntry] = {
    "pgc-schizophrenia": DatasetEntry(
        dataset_id="pgc-schizophrenia",
        disorder="Schizophrenia",
        publication="Trubetskoy et al. 2022, Nature (PGC3 SCZ)",
        hf_repo="OpenMed/pgc-schizophrenia",
        description="PGC schizophrenia GWAS summary statistics.",
        configs=[
            DatasetConfig(
                config_id="scz2022",
                description="PGC3 schizophrenia meta-analysis (demo subset).",
                mock_file="pgc-scz_scz2022.csv",
            )
        ],
    ),
    "pgc-bipolar": DatasetEntry(
        dataset_id="pgc-bipolar",
        disorder="Bipolar Disorder",
        publication="Mullins et al. 2021, Nature Genetics (PGC BIP)",
        hf_repo="OpenMed/pgc-bipolar",
        description="PGC bipolar disorder GWAS summary statistics.",
        configs=[
            DatasetConfig(
                config_id="bip2021",
                description="PGC bipolar disorder meta-analysis (demo subset).",
                mock_file="pgc-bipolar_bip2021.csv",
            )
        ],
    ),
    "pgc-mdd": DatasetEntry(
        dataset_id="pgc-mdd",
        disorder="Major Depressive Disorder",
        publication="Howard et al. 2019, Nature Neuroscience (PGC MDD)",
        hf_repo="OpenMed/pgc-mdd",
        description="PGC major depressive disorder GWAS summary statistics.",
        configs=[
            DatasetConfig(
                config_id="mdd2019",
                description="PGC major depressive disorder meta-analysis (demo subset).",
                mock_file="pgc-mdd_mdd2019.csv",
            )
        ],
    ),
}


def get_dataset(dataset_id: str) -> DatasetEntry:
    if dataset_id not in DATASET_CATALOG:
        raise KeyError(f"Unknown dataset_id: {dataset_id!r}")
    return DATASET_CATALOG[dataset_id]


def get_config(dataset_id: str, config_id: str) -> DatasetConfig:
    entry = get_dataset(dataset_id)
    for cfg in entry.configs:
        if cfg.config_id == config_id:
            return cfg
    raise KeyError(f"Unknown config {config_id!r} for dataset {dataset_id!r}")
