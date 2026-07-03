"""FastAPI application exposing the GeneGauge PGC analysis engine.

Endpoints:
    GET  /health                          (plain health check, e.g. for Render)
    GET  /api/health
    GET  /api/datasets
    GET  /api/datasets/{dataset_id}/configs
    GET  /api/datasets/{dataset_id}/configs/{config_id}/schema
    POST /api/analyses
    POST /api/analyses/{id}/run
    GET  /api/analyses
    GET  /api/analyses/{id}
    GET  /api/analyses/{id}/report        (Markdown or ?format=pdf)
    GET  /api/methods
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response

from app import __version__, config
from app.data_sources.huggingface_loader import (
    inspect_schema,
    list_configs,
    list_datasets,
    load_pgc_dataset,
)
from app.models import AnalysisCreateRequest
from app.normalization.schema_normalizer import normalize_gwas_schema
from app.pipeline import run_analysis
from app.reports.report_generator import (
    LIMITATIONS,
    generate_markdown_report,
    generate_pdf_report,
)
from app.store import store, supabase_enabled

app = FastAPI(
    title="GeneGauge PGC API",
    version=__version__,
    description="Reproducible psychiatric GWAS overlap explorer.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "demo_mode": config.is_demo_mode(),
        "supabase": supabase_enabled(),
    }


@app.get("/health")
def health_root() -> dict:
    """Plain health-check path for Render (and other platform) health checks."""
    return {"status": "ok"}


@app.get("/api/datasets")
def get_datasets() -> dict:
    return {"datasets": list_datasets(), "demo_mode": config.is_demo_mode()}


@app.get("/api/datasets/{dataset_id}/configs")
def get_configs(dataset_id: str) -> dict:
    try:
        return {"configs": list_configs(dataset_id)}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/datasets/{dataset_id}/configs/{config_id}/schema")
def get_schema(dataset_id: str, config_id: str, limit: int = Query(200, ge=1, le=5000)) -> dict:
    try:
        loaded = load_pgc_dataset(dataset_id, config_id, limit=limit)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    raw = inspect_schema(loaded)
    try:
        norm = normalize_gwas_schema(loaded)
        raw["normalization"] = {
            "column_mapping": norm.column_mapping,
            "warnings": norm.warnings,
            "effect_encoding": norm.effect_encoding,
            "normalized_preview": norm.frame.head(10).to_dicts(),
        }
    except Exception as e:  # surface normalization failure without 500-ing
        raw["normalization"] = {"error": str(e)}
    return raw


@app.post("/api/analyses", status_code=201)
def create_analysis(req: AnalysisCreateRequest) -> dict:
    # Validate selections against the catalog before persisting.
    for s in req.selections:
        try:
            config.get_config(s.dataset_id, s.config_id)
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e))

    analysis_id = uuid.uuid4().hex[:12]
    record = {
        "id": analysis_id,
        "name": req.name,
        "status": "created",
        "created_at": _now(),
        "request": req.model_dump(),
        "per_dataset": [],
        "params": {"demo_mode": config.is_demo_mode()},
    }
    store.save(record)
    return {"id": analysis_id, "status": "created"}


@app.post("/api/analyses/{analysis_id}/run")
def run(analysis_id: str) -> dict:
    record = store.get(analysis_id)
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found")
    req = AnalysisCreateRequest(**record["request"])
    try:
        result = run_analysis(
            analysis_id,
            [s.model_dump() for s in req.selections],
            significance_method=req.significance_method,
            top_k=req.top_k,
            custom_threshold=req.custom_threshold,
            mapping_method=req.mapping_method,
            run_enrichment=req.run_enrichment,
            enrichment_alpha=req.enrichment_alpha,
            created_at=record.get("created_at"),
        )
    except Exception as e:
        record["status"] = "failed"
        record["error"] = str(e)
        store.save(record)
        raise HTTPException(status_code=422, detail=f"Analysis failed: {e}")

    result["name"] = req.name
    result["request"] = record["request"]
    store.save(result)
    return result


@app.get("/api/analyses")
def list_analyses() -> dict:
    return {"analyses": store.list_summaries()}


@app.get("/api/analyses/{analysis_id}")
def get_analysis(analysis_id: str) -> dict:
    record = store.get(analysis_id)
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return record


@app.get("/api/analyses/{analysis_id}/report")
def get_report(analysis_id: str, format: str = Query("markdown", pattern="^(markdown|md|pdf)$")):
    record = store.get(analysis_id)
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if record.get("status") != "completed":
        raise HTTPException(status_code=409, detail="Analysis has not completed; run it first.")

    if format == "pdf":
        import tempfile
        from pathlib import Path

        out = Path(tempfile.gettempdir()) / f"genegauge_{analysis_id}.pdf"
        result = generate_pdf_report(record, out)
        if result is None:
            raise HTTPException(status_code=501, detail="PDF backend unavailable; use Markdown.")
        return Response(
            content=out.read_bytes(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="genegauge_{analysis_id}.pdf"'},
        )

    md = generate_markdown_report(record)
    return PlainTextResponse(md, media_type="text/markdown")


@app.get("/api/methods")
def methods() -> dict:
    return {
        "significance_thresholds": {
            "genome_wide": config.GENOME_WIDE_SIGNIFICANCE,
            "suggestive": config.SUGGESTIVE_SIGNIFICANCE,
        },
        "mapping_methods": {
            "gene_body": "Variant within gene start-end.",
            "window_10kb": "Variant within +/-10 kb of the gene body.",
            "window_50kb": "Variant within +/-50 kb of the gene body.",
            "nearest": "Single closest gene on the same chromosome.",
        },
        "overlap_metrics": [
            "Shared rsIDs",
            "Shared chromosome:position",
            "Jaccard similarity",
            "Direction (effect-sign) concordance for shared variants",
            "Gene-set Jaccard",
            "Hypergeometric enrichment p-value",
            "Benjamini-Hochberg FDR correction",
        ],
        "enrichment": {
            "method": "Hypergeometric over-representation analysis (ORA)",
            "sources": ["GO Biological Process", "Reactome"],
            "correction": "Benjamini-Hochberg FDR",
        },
        "limitations": LIMITATIONS,
        "demo_mode": config.is_demo_mode(),
    }
