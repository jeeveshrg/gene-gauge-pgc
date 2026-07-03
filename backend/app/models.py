"""Pydantic request/response models for the GeneGauge PGC API."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class DatasetSelection(BaseModel):
    dataset_id: str
    config_id: str


class AnalysisCreateRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="Human-friendly label.")
    selections: list[DatasetSelection] = Field(
        ..., min_length=1, description="Datasets/configs to analyze."
    )
    significance_method: Literal["genome_wide", "suggestive", "top_k", "custom"] = "genome_wide"
    top_k: Optional[int] = Field(default=None, ge=1)
    custom_threshold: Optional[float] = Field(default=None, gt=0, le=1)
    mapping_method: Literal["gene_body", "window_10kb", "window_50kb", "nearest"] = "window_10kb"
    run_enrichment: bool = True
    enrichment_alpha: float = Field(default=0.05, gt=0, le=1)

    @field_validator("selections")
    @classmethod
    def _unique_selections(cls, v: list[DatasetSelection]) -> list[DatasetSelection]:
        seen = {(s.dataset_id, s.config_id) for s in v}
        if len(seen) != len(v):
            raise ValueError("Duplicate dataset/config selections are not allowed.")
        return v


class AnalysisSummary(BaseModel):
    id: str
    name: Optional[str] = None
    status: str
    created_at: str
    disorders: list[str] = []
    n_datasets: int = 0
    demo_mode: bool = False
