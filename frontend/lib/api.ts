// Typed client for GeneGauge PGC. In Vercel demo mode, requests go to the
// same-origin Next API routes. Set NEXT_PUBLIC_API_BASE_URL to use a live
// Python backend instead.

function getApiBase() {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
  if (configured) return configured;
  if (typeof window !== "undefined") return "";
  if (process.env.VERCEL_URL) return `https://${process.env.VERCEL_URL}`;
  return "http://localhost:3000";
}

export const API_BASE = getApiBase();

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export interface DatasetInfo {
  dataset_id: string;
  disorder: string;
  publication: string;
  hf_repo: string;
  description: string;
  n_configs: number;
  demo_mode: boolean;
}

export interface ConfigInfo {
  config_id: string;
  description: string;
  build: string;
  dataset_id: string;
  disorder: string;
}

export interface Selection {
  dataset_id: string;
  config_id: string;
}

export interface AnalysisSummary {
  id: string;
  name: string | null;
  status: string;
  created_at: string;
  disorders: string[];
  n_datasets: number;
  demo_mode: boolean;
}

export interface VariantRecord {
  rsid: string | null;
  chromosome: string | null;
  position: number | null;
  effect_allele: string | null;
  other_allele: string | null;
  beta: number | null;
  odds_ratio: number | null;
  p_value: number | null;
  [key: string]: unknown;
}

export interface PerDataset {
  dataset_id: string;
  config_id: string;
  disorder: string;
  publication: string;
  source: string;
  source_ref: string;
  n_total_variants: number;
  n_significant: number;
  n_genes: number;
  genes: string[];
  significant_variants: VariantRecord[];
  mapping_summary: Record<string, unknown>;
  normalization: {
    column_mapping: Record<string, string>;
    warnings: string[];
    effect_encoding: string;
  };
}

export interface VariantOverlap {
  disorder_a: string;
  disorder_b: string;
  overlap_count: number;
  shared_rsids: string[];
  shared_positions: string[];
  jaccard_rsid: number;
  jaccard_position: number;
  direction_concordance: {
    n_comparable: number;
    n_concordant: number;
    n_discordant: number;
    concordance_rate: number | null;
    details: Array<Record<string, unknown>>;
  };
}

export interface GeneOverlap {
  disorder_a: string;
  disorder_b: string;
  n_shared: number;
  shared_genes: string[];
  jaccard: number;
  hypergeometric_p: number;
  q_value?: number;
  significant?: boolean;
}

export interface EnrichmentTerm {
  term: string;
  source: string;
  description: string;
  overlap_size: number;
  n_term_genes: number;
  overlap_genes: string[];
  p_value: number;
  q_value?: number;
  significant?: boolean;
}

export interface AnalysisResult {
  id: string;
  name: string | null;
  status: string;
  created_at: string;
  params: {
    demo_mode: boolean;
    significance: { method: string; threshold: number | null; k: number | null };
    mapping: { method: string; window: number | null };
    enrichment: { enabled: boolean; alpha: number };
  };
  per_dataset: PerDataset[];
  variant_overlaps: VariantOverlap[];
  gene_overlaps: GeneOverlap[];
  enrichment: {
    enabled: boolean;
    per_disorder: Record<string, { results: EnrichmentTerm[]; universe_size: number }>;
  };
  reproducibility: Record<string, unknown>;
  limitations: string[];
  plain_language?: {
    headline: string;
    bullets: string[];
    caveat: string;
  };
  error?: string;
}

// ---------------------------------------------------------------------------
// Fetch helpers
// ---------------------------------------------------------------------------
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; demo_mode: boolean; version: string }>("/api/health"),
  datasets: () => request<{ datasets: DatasetInfo[]; demo_mode: boolean }>("/api/datasets"),
  configs: (datasetId: string) =>
    request<{ configs: ConfigInfo[] }>(`/api/datasets/${datasetId}/configs`),
  schema: (datasetId: string, configId: string) =>
    request<Record<string, unknown>>(`/api/datasets/${datasetId}/configs/${configId}/schema`),
  createAnalysis: (payload: unknown) =>
    request<{ id: string; status: string }>("/api/analyses", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  runAnalysis: (id: string) =>
    request<AnalysisResult>(`/api/analyses/${id}/run`, { method: "POST" }),
  getAnalysis: (id: string) => request<AnalysisResult>(`/api/analyses/${id}`),
  listAnalyses: () => request<{ analyses: AnalysisSummary[] }>("/api/analyses"),
  methods: () => request<Record<string, unknown>>("/api/methods"),
  reportUrl: (id: string, format: "markdown" | "pdf" = "markdown") =>
    `${API_BASE}/api/analyses/${id}/report?format=${format}`,
};

// Formatting helpers shared across pages.
export function fmtP(p: number | null | undefined): string {
  if (p === null || p === undefined) return "NA";
  if (p === 0) return "0";
  if (p < 1e-3 || p > 1e3) return p.toExponential(2);
  return p.toPrecision(3);
}
