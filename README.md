# GeneGauge PGC — Reproducible Psychiatric GWAS Overlap Explorer

GeneGauge PGC loads Psychiatric Genomics Consortium (PGC / OpenMed) **GWAS
summary-statistic** datasets, normalizes their heterogeneous schemas, extracts
significant variants, maps them to positional candidate genes, compares overlap
across psychiatric disorders, runs pathway enrichment, and generates
reproducible reports.

> ⚠️ **Scientific scope.** These datasets are GWAS **summary statistics**, not
> curated gene lists. Positional variant-to-gene mapping does **not** establish
> causality, and overlap between disorders does **not** imply shared biology or
> a clinical relationship. No clinical or diagnostic claims are made and
> individual disorder risk is never predicted. Every result page and every
> generated report states its limitations.

The app runs **fully offline in demo mode** on bundled mock data — no Hugging
Face token or Supabase project is required to try it.

---

## Repository layout

```
.
├── backend/                     FastAPI + Python analysis engine
│   ├── app/
│   │   ├── config.py            Settings + dataset catalog
│   │   ├── main.py              FastAPI app (all /api endpoints)
│   │   ├── models.py            Pydantic request/response models
│   │   ├── pipeline.py          End-to-end analysis orchestration
│   │   ├── store.py             JSON-backed analysis history (Supabase optional)
│   │   ├── data_sources/
│   │   │   └── huggingface_loader.py   load_pgc_dataset / inspect_schema (+mock fallback)
│   │   ├── normalization/
│   │   │   └── schema_normalizer.py    normalize_gwas_schema
│   │   ├── analysis/
│   │   │   ├── significant_variants.py extract_significant_variants
│   │   │   ├── variant_overlap.py      compare_variant_overlap / compute_jaccard
│   │   │   ├── gene_mapping.py         map_variants_to_genes (DuckDB range joins)
│   │   │   ├── gene_overlap.py         compute_gene_overlap / hypergeometric / FDR
│   │   │   └── enrichment.py           run_pathway_enrichment (GO:BP / Reactome ORA)
│   │   └── reports/
│   │       └── report_generator.py     generate_markdown_report (+optional PDF)
│   ├── data/
│   │   ├── mock/                Sample mock GWAS CSVs + demo gene annotation
│   │   └── pathways/            Demo GMT gene-set collection
│   ├── scripts/run_demo_analysis.py    Demo analysis (writes Markdown report)
│   ├── tests/                   Unit tests (pytest)
│   └── requirements.txt
├── frontend/                    Next.js + TypeScript + Tailwind + RHF + Zod
│   ├── app/                     /, /datasets, /new, /analysis/[id], /history, /methods, /examples
│   ├── components/ui.tsx        shadcn-style primitives (neutral scientific UI)
│   └── lib/api.ts               Typed API client
├── .env.example
└── README.md
```

---

## Tech stack

**Backend:** FastAPI · Python · Polars · DuckDB · PyArrow · pandas (small tables
only) · SciPy · statsmodels · matplotlib (PDF) · `datasets` (optional live HF
loading). Enrichment uses a self-contained hypergeometric ORA (equivalent to
Enrichr/gseapy); `gseapy`/`goatools` can be swapped in behind the same API.

**Frontend:** Next.js (App Router) · TypeScript · Tailwind CSS · shadcn/ui-style
components · React Hook Form · Zod.

**Storage/deploy:** Supabase Postgres/Storage (optional) · Vercel (frontend) ·
Render/Railway/Fly.io (backend).

---

## Common normalized GWAS schema

Every dataset is normalized to:

```
dataset_id, disorder, publication, variant_id, rsid, chromosome, position,
effect_allele, other_allele, beta, odds_ratio, standard_error, p_value,
sample_size, source_config
```

Effect encodings are reconciled automatically: odds ratios → `beta = ln(OR)`;
betas → `odds_ratio = exp(beta)`; log-odds columns are treated as beta. A
missing p-value column raises a clear error rather than silently returning
nothing.

---

## Quick start

### 1. Backend (FastAPI)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # optional
pip install -r requirements.txt

# Run the API (demo mode is auto-enabled without HF_TOKEN)
GENEGAUGE_DEMO_MODE=1 uvicorn app.main:app --reload --port 8000
```

API is now at `http://localhost:8000` (interactive docs at `/docs`).

### 2. Frontend (Next.js)

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local
npm run dev            # http://localhost:3000
```

### 3. Run the tests

```bash
cd backend
python -m pytest -q
```

### 4. Run the demo analysis (CLI, writes a Markdown report)

```bash
cd backend
python scripts/run_demo_analysis.py
# -> prints overlap results and writes backend/demo_report.md
```

---

## API endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/health` | Service status, demo/supabase flags |
| GET | `/api/datasets` | List available PGC datasets |
| GET | `/api/datasets/{dataset_id}/configs` | List configs for a dataset |
| GET | `/api/datasets/{dataset_id}/configs/{config_id}/schema` | Raw + normalized schema inspection |
| POST | `/api/analyses` | Create an analysis (validates selections) |
| POST | `/api/analyses/{id}/run` | Run the analysis pipeline |
| GET | `/api/analyses` | List analysis history |
| GET | `/api/analyses/{id}` | Get a full analysis result |
| GET | `/api/analyses/{id}/report?format=markdown\|pdf` | Reproducible report |
| GET | `/api/methods` | Methods, thresholds, and limitations |

---

## Analysis workflow

1. **Load** a dataset/config (Hugging Face streaming or bundled mock).
2. **Normalize** to the common GWAS schema.
3. **Extract** significant variants (`genome_wide` p<5e-8, `suggestive` p<1e-5,
   `top_k`, or `custom`).
4. **Map** variants to positional candidate genes (`gene_body`, `window_10kb`,
   `window_50kb`, `nearest`) via DuckDB range joins.
5. **Compare variants** pairwise: shared rsIDs, shared chr:pos, Jaccard, and
   effect-direction concordance (with allele-flip alignment).
6. **Compare genes** pairwise: shared genes, Jaccard, hypergeometric enrichment
   p-value, Benjamini-Hochberg FDR.
7. **Enrich** each disorder's gene set against GO:BP / Reactome (ORA + FDR).
8. **Report** everything as Markdown (optional PDF) with full reproducibility
   metadata and limitations.

---

## Performance & scalability

- Datasets load as **Polars** frames; live Hugging Face loading uses
  **streaming**, never materializing billions of rows into pandas.
- Variant-to-gene range joins run in **DuckDB** so they scale to large variant
  tables.
- pandas is reserved for small final tables only.
- The pipeline is structured so additional datasets/configs can be added to the
  catalog in `app/config.py` without touching analysis code.

---

## Demo mode & live mode

- **Demo mode** (default without `HF_TOKEN`): uses `backend/data/mock/*.csv` and
  the bundled gene annotation / GMT. Analysis history is a local JSON file.
- **Live mode** (`HF_TOKEN` set, `GENEGAUGE_DEMO_MODE=0`): loads real
  OpenMed/PGC datasets via `datasets.load_dataset(repo, config, streaming=True)`;
  falls back transparently to mock data on any network/credential failure.
- **Supabase** (optional): set `SUPABASE_URL` / `SUPABASE_KEY` to enable
  persistence beyond the local JSON store.

See `.env.example` for all variables.

---

## Deployment notes

- **Frontend → Vercel:** set `NEXT_PUBLIC_API_BASE_URL` to your backend URL.
- **Backend → Render/Railway/Fly.io:** run
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`; set `HF_TOKEN` /
  Supabase vars as needed. Restrict CORS origins for production.
- **Supabase:** create a project and provide `SUPABASE_URL` / `SUPABASE_KEY`.

---

## Tests

Unit tests (pytest) cover schema normalization, missing p-value handling,
threshold filtering, variant overlap, Jaccard, variant-to-gene mapping, gene
overlap, the hypergeometric test, FDR correction, enrichment, the full pipeline,
and report generation.

```bash
cd backend && python -m pytest -q
```

---

## License / disclaimer

Research and educational use only. GeneGauge PGC is **not** a medical device and
must not be used for clinical decision-making.
