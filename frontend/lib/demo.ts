import type {
  AnalysisResult,
  AnalysisSummary,
  ConfigInfo,
  DatasetInfo,
  EnrichmentTerm,
  GeneOverlap,
  PerDataset,
  VariantOverlap,
  VariantRecord,
} from "./api";

type Method = "genome_wide" | "suggestive" | "top_k" | "custom";
type Mapping = "gene_body" | "window_10kb" | "window_50kb" | "nearest";

type DemoSelection = {
  dataset_id: string;
  config_id: string;
};

type DemoPayload = {
  name: string | null;
  selections: DemoSelection[];
  significance_method: Method;
  top_k: number | null;
  custom_threshold: number | null;
  mapping_method: Mapping;
  run_enrichment: boolean;
  enrichment_alpha: number;
  created_at: string;
};

type DemoVariant = VariantRecord & {
  gene: string;
  nearby_genes?: string[];
};

const VERSION = "1.0.0-vercel-demo";
const GENOME_WIDE = 5e-8;
const SUGGESTIVE = 1e-5;

const DATASETS: DatasetInfo[] = [
  {
    dataset_id: "pgc-schizophrenia",
    disorder: "Schizophrenia",
    publication: "Fake teaching dataset inspired by PGC-style GWAS tables",
    hf_repo: "demo/pgc-schizophrenia",
    description: "Demo markers for a schizophrenia-style research dataset.",
    n_configs: 1,
    demo_mode: true,
  },
  {
    dataset_id: "pgc-bipolar",
    disorder: "Bipolar Disorder",
    publication: "Fake teaching dataset inspired by PGC-style GWAS tables",
    hf_repo: "demo/pgc-bipolar",
    description: "Demo markers for a bipolar disorder-style research dataset.",
    n_configs: 1,
    demo_mode: true,
  },
  {
    dataset_id: "pgc-mdd",
    disorder: "Major Depressive Disorder",
    publication: "Fake teaching dataset inspired by PGC-style GWAS tables",
    hf_repo: "demo/pgc-mdd",
    description: "Demo markers for a depression-style research dataset.",
    n_configs: 1,
    demo_mode: true,
  },
];

const CONFIGS: Record<string, ConfigInfo[]> = {
  "pgc-schizophrenia": [
    {
      config_id: "scz2022",
      description: "Small fake schizophrenia demo table",
      build: "demo",
      dataset_id: "pgc-schizophrenia",
      disorder: "Schizophrenia",
    },
  ],
  "pgc-bipolar": [
    {
      config_id: "bip2021",
      description: "Small fake bipolar disorder demo table",
      build: "demo",
      dataset_id: "pgc-bipolar",
      disorder: "Bipolar Disorder",
    },
  ],
  "pgc-mdd": [
    {
      config_id: "mdd2019",
      description: "Small fake major depression demo table",
      build: "demo",
      dataset_id: "pgc-mdd",
      disorder: "Major Depressive Disorder",
    },
  ],
};

const VARIANTS: Record<string, DemoVariant[]> = {
  "pgc-schizophrenia": [
    marker("rs1000004", "6", 31955000, "G", "A", 0.1823, 1.2, 1e-15, "C4A", ["C4B"]),
    marker("rs1000001", "12", 2350000, "A", "G", 0.1133, 1.12, 2.5e-12, "CACNA1C"),
    marker("rs1000002", "11", 113450000, "C", "T", -0.1054, 0.9, 8e-10, "DRD2"),
    marker("rs1000003", "16", 9900000, "T", "C", 0.077, 1.08, 3e-9, "CACNB2"),
    marker("rs1000006", "2", 184700000, "C", "T", 0.0583, 1.06, 6e-9, "ZNF804A"),
    marker("rs1000007", "10", 18500000, "T", "C", 0.0488, 1.05, 2e-8, "GRIN2A"),
    marker("rs1000005", "18", 55400000, "A", "G", 0.0677, 1.07, 4.5e-8, "TCF4"),
    marker("rs1000010", "12", 2360000, "C", "T", 0.0953, 1.1, 1e-6, "CACNA1C"),
    marker("rs1000012", "16", 9950000, "G", "T", 0.0392, 1.04, 9e-4, "CACNB2"),
    marker("rs1000009", "1", 71900000, "G", "A", 0.01, 1.01, 0.4, "NEGR1"),
  ],
  "pgc-bipolar": [
    marker("rs1000001", "12", 2350000, "A", "G", 0.11, 1.1163, 5e-11, "CACNA1C"),
    marker("rs2000001", "10", 60300000, "G", "A", 0.09, 1.0942, 1e-9, "ANK3"),
    marker("rs2000002", "12", 2500000, "C", "T", 0.08, 1.0833, 5e-9, "CACNA1C"),
    marker("rs1000003", "16", 9900000, "T", "C", 0.07, 1.0725, 2e-8, "CACNB2"),
    marker("rs1000005", "18", 55400000, "A", "G", 0.06, 1.0618, 3e-8, "TCF4"),
    marker("rs1000007", "10", 18500000, "T", "C", -0.05, 0.9512, 4e-8, "GRIN2A"),
    marker("rs2000004", "16", 10000000, "T", "C", 0.05, 1.0513, 3e-6, "CACNB2"),
    marker("rs2000003", "5", 1000000, "A", "G", 0.01, 1.0101, 0.2, "CLOCK"),
    marker("rs2000005", "4", 8000000, "G", "C", 0.005, 1.005, 0.85, "BDNF"),
  ],
  "pgc-mdd": [
    marker("rs1000001", "12", 2350000, "A", "G", 0.05, 1.0513, 1e-8, "CACNA1C"),
    marker("rs1000002", "11", 113450000, "C", "T", -0.04, 0.9608, 2e-8, "DRD2"),
    marker("rs3000001", "1", 72000000, "G", "A", 0.03, 1.0305, 5e-9, "NEGR1"),
    marker("rs3000002", "17", 30210000, "C", "T", 0.03, 1.0305, 1e-8, "SLC6A4"),
    marker("rs3000003", "11", 27680000, "A", "G", 0.025, 1.0253, 3e-8, "BDNF"),
    marker("rs3000005", "1", 72010000, "C", "T", 0.02, 1.0202, 2e-6, "NEGR1"),
    marker("rs3000004", "3", 6000000, "T", "C", 0.005, 1.005, 0.6, "CRHR1"),
    marker("rs3000006", "8", 3000000, "A", "G", 0.002, 1.002, 0.9, "FKBP5"),
  ],
};

const GENESETS = [
  {
    term: "CALCIUM_CHANNEL_SIGNALING",
    source: "teaching set",
    description: "Genes involved in calcium-channel signaling",
    genes: ["CACNA1C", "CACNB2", "ANK3"],
  },
  {
    term: "SYNAPTIC_SIGNALING",
    source: "teaching set",
    description: "Genes involved in neuron-to-neuron communication",
    genes: ["DRD2", "GRIN2A", "BDNF", "SLC6A4", "TCF4"],
  },
  {
    term: "MOOD_STRESS_RESPONSE",
    source: "teaching set",
    description: "Genes used here to illustrate mood/stress biology themes",
    genes: ["BDNF", "SLC6A4", "CRHR1", "FKBP5", "NEGR1"],
  },
  {
    term: "IMMUNE_REGION_DEMO",
    source: "teaching set",
    description: "A fake immune-region teaching set",
    genes: ["C4A", "C4B", "DRD2"],
  },
];

const LIMITATIONS = [
  "This Vercel demo uses tiny fake datasets. The numbers are for learning the workflow only.",
  "A shared marker means two fake tables contain the same marker ID. It is not a diagnosis.",
  "Nearby-gene mapping is a rough pointer, not proof that a gene causes anything.",
  "The app never predicts personal risk and is not a medical tool.",
];

export function demoDatasets() {
  return DATASETS;
}

export function demoConfigs(datasetId: string) {
  const configs = CONFIGS[datasetId];
  if (!configs) throw new Error(`Unknown dataset: ${datasetId}`);
  return configs;
}

export function demoSchema(datasetId: string, configId: string) {
  const dataset = getDataset(datasetId);
  const config = demoConfigs(datasetId).find((item) => item.config_id === configId);
  if (!config) throw new Error(`Unknown config: ${configId}`);
  return {
    dataset_id: datasetId,
    config_id: configId,
    raw_columns: ["rsid", "chromosome", "position", "effect_allele", "other_allele", "beta", "p_value"],
    normalized_columns: [
      "dataset_id",
      "disorder",
      "variant_id",
      "rsid",
      "chromosome",
      "position",
      "effect_allele",
      "other_allele",
      "beta",
      "odds_ratio",
      "p_value",
    ],
    preview: VARIANTS[datasetId].slice(0, 5),
    normalization: {
      column_mapping: {
        rsid: "rsid",
        chromosome: "chromosome",
        position: "position",
        beta: "beta",
        p_value: "p_value",
      },
      warnings: ["Demo route: this schema preview is generated from fake teaching data."],
      effect_encoding: "beta",
      normalized_preview: VARIANTS[datasetId].slice(0, 5),
    },
    disorder: dataset.disorder,
  };
}

export function createDemoAnalysisId(input: unknown) {
  const payload = normalizePayload(input);
  const encoded = encode(payload);
  return `demo-${hash(encoded)}-${encoded}`;
}

export function runDemoAnalysis(id: string): AnalysisResult {
  const payload = decodeAnalysisId(id);
  if (!payload) throw new Error("Analysis not found");

  const perDataset = payload.selections.map((selection) =>
    buildPerDataset(selection, payload.significance_method, payload.top_k, payload.custom_threshold, payload.mapping_method),
  );
  const variantOverlaps = buildVariantOverlaps(perDataset);
  const geneOverlaps = buildGeneOverlaps(perDataset);
  const enrichment = buildEnrichment(perDataset, payload.run_enrichment, payload.enrichment_alpha);

  return {
    id,
    name: payload.name,
    status: "completed",
    created_at: payload.created_at,
    params: {
      demo_mode: true,
      significance: {
        method: payload.significance_method,
        threshold: thresholdFor(payload.significance_method, payload.custom_threshold),
        k: payload.top_k,
      },
      mapping: {
        method: payload.mapping_method,
        window: windowFor(payload.mapping_method),
      },
      enrichment: { enabled: payload.run_enrichment, alpha: payload.enrichment_alpha },
    },
    per_dataset: perDataset,
    variant_overlaps: variantOverlaps,
    gene_overlaps: geneOverlaps,
    enrichment,
    reproducibility: {
      app_version: VERSION,
      generated_at: payload.created_at,
      significance_method: payload.significance_method,
      mapping_method: payload.mapping_method,
      demo_mode: true,
      dataset_sources: perDataset.map((item) => item.source_ref),
    },
    limitations: LIMITATIONS,
    plain_language: plainLanguageSummary(perDataset, variantOverlaps, geneOverlaps),
  };
}

export function listDemoAnalyses(): AnalysisSummary[] {
  return [];
}

export function demoMethods() {
  return {
    significance_thresholds: {
      genome_wide: GENOME_WIDE,
      suggestive: SUGGESTIVE,
    },
    mapping_methods: {
      gene_body: "Use markers that sit inside a known gene.",
      window_10kb: "Also count genes within about 10,000 DNA letters of a marker.",
      window_50kb: "Use a wider teaching window around each marker.",
      nearest: "Attach each marker to the nearest teaching gene.",
    },
    demo_mode: true,
    limitations: LIMITATIONS,
  };
}

export function demoMarkdownReport(result: AnalysisResult) {
  const lines = [
    "# GeneGauge PGC demo report",
    "",
    `Analysis: ${result.name || "Untitled demo"}`,
    `Created: ${result.created_at}`,
    "",
    "## Plain-English takeaway",
    result.plain_language?.headline || "Demo results generated.",
    "",
    ...(result.plain_language?.bullets.map((item) => `- ${item}`) || []),
    "",
    "## Compared groups",
    ...result.per_dataset.map(
      (item) => `- ${item.disorder}: ${item.n_significant} fake markers, ${item.n_genes} nearby teaching genes`,
    ),
    "",
    "## Overlap",
    ...result.gene_overlaps.map(
      (item) =>
        `- ${item.disorder_a} vs ${item.disorder_b}: ${item.n_shared} shared genes (${item.shared_genes.join(", ") || "none"})`,
    ),
    "",
    "## Important caveat",
    result.plain_language?.caveat || LIMITATIONS[0],
  ];
  return `${lines.join("\n")}\n`;
}

function marker(
  rsid: string,
  chromosome: string,
  position: number,
  effectAllele: string,
  otherAllele: string,
  beta: number,
  oddsRatio: number,
  pValue: number,
  gene: string,
  nearbyGenes: string[] = [],
): DemoVariant {
  return {
    rsid,
    chromosome,
    position,
    effect_allele: effectAllele,
    other_allele: otherAllele,
    beta,
    odds_ratio: oddsRatio,
    p_value: pValue,
    gene,
    nearby_genes: nearbyGenes,
  };
}

function normalizePayload(input: unknown): DemoPayload {
  const raw = input && typeof input === "object" ? (input as Record<string, unknown>) : {};
  const selections = normalizeSelections(raw.selections);
  const significanceMethod = asMethod(raw.significance_method);
  const topK = significanceMethod === "top_k" ? positiveInt(raw.top_k, 5) : null;
  const customThreshold =
    significanceMethod === "custom" ? boundedNumber(raw.custom_threshold, 0.00001) : null;
  return {
    name: typeof raw.name === "string" && raw.name.trim() ? raw.name.trim().slice(0, 80) : "Simple demo comparison",
    selections,
    significance_method: significanceMethod,
    top_k: topK,
    custom_threshold: customThreshold,
    mapping_method: asMapping(raw.mapping_method),
    run_enrichment: raw.run_enrichment !== false,
    enrichment_alpha: boundedNumber(raw.enrichment_alpha, 0.05),
    created_at: new Date().toISOString(),
  };
}

function normalizeSelections(value: unknown): DemoSelection[] {
  const input = Array.isArray(value) ? value : [];
  const selections = input.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const record = item as Record<string, unknown>;
    const datasetId = typeof record.dataset_id === "string" ? record.dataset_id : "";
    if (!CONFIGS[datasetId]) return [];
    const configId =
      typeof record.config_id === "string" && CONFIGS[datasetId].some((config) => config.config_id === record.config_id)
        ? record.config_id
        : CONFIGS[datasetId][0].config_id;
    return [{ dataset_id: datasetId, config_id: configId }];
  });
  const unique = Array.from(new Map(selections.map((item) => [item.dataset_id, item])).values());
  return unique.length >= 2
    ? unique
    : [
        { dataset_id: "pgc-schizophrenia", config_id: "scz2022" },
        { dataset_id: "pgc-bipolar", config_id: "bip2021" },
      ];
}

function buildPerDataset(
  selection: DemoSelection,
  method: Method,
  topK: number | null,
  customThreshold: number | null,
  mapping: Mapping,
): PerDataset {
  const dataset = getDataset(selection.dataset_id);
  const variants = selectVariants(VARIANTS[selection.dataset_id], method, topK, customThreshold);
  const genes = sortedUnique(variants.flatMap((variant) => genesForVariant(variant, mapping)));
  return {
    dataset_id: selection.dataset_id,
    config_id: selection.config_id,
    disorder: dataset.disorder,
    publication: dataset.publication,
    source: "Vercel fake-data demo",
    source_ref: dataset.hf_repo,
    n_total_variants: VARIANTS[selection.dataset_id].length,
    n_significant: variants.length,
    n_genes: genes.length,
    genes,
    significant_variants: variants,
    mapping_summary: {
      method: mapping,
      explanation: "Each fake marker is attached to a nearby teaching gene.",
    },
    normalization: {
      column_mapping: {
        marker: "rsid",
        location: "chromosome:position",
        effect: "beta",
        p: "p_value",
      },
      warnings: ["Fake teaching data: numbers are illustrative and not biological findings."],
      effect_encoding: "beta",
    },
  };
}

function buildVariantOverlaps(perDataset: PerDataset[]): VariantOverlap[] {
  return pairs(perDataset).map(([a, b]) => {
    const aByRsid = new Map(a.significant_variants.map((variant) => [variant.rsid, variant]));
    const bByRsid = new Map(b.significant_variants.map((variant) => [variant.rsid, variant]));
    const shared = sortedUnique([...aByRsid.keys()].filter((rsid): rsid is string => !!rsid && bByRsid.has(rsid)));
    const union = new Set([...aByRsid.keys(), ...bByRsid.keys()].filter(Boolean));
    const comparable = shared.map((rsid) => [aByRsid.get(rsid), bByRsid.get(rsid)] as const);
    const concordant = comparable.filter(([left, right]) => Math.sign(left?.beta || 0) === Math.sign(right?.beta || 0)).length;
    return {
      disorder_a: a.disorder,
      disorder_b: b.disorder,
      overlap_count: shared.length,
      shared_rsids: shared,
      shared_positions: shared.map((rsid) => {
        const variant = aByRsid.get(rsid);
        return `${variant?.chromosome}:${variant?.position}`;
      }),
      jaccard_rsid: ratio(shared.length, union.size),
      jaccard_position: ratio(shared.length, union.size),
      direction_concordance: {
        n_comparable: comparable.length,
        n_concordant: concordant,
        n_discordant: comparable.length - concordant,
        concordance_rate: comparable.length ? ratio(concordant, comparable.length) : null,
        details: shared.map((rsid) => ({ rsid })),
      },
    };
  });
}

function buildGeneOverlaps(perDataset: PerDataset[]): GeneOverlap[] {
  const overlaps = pairs(perDataset).map(([a, b]) => {
    const aGenes = new Set(a.genes);
    const bGenes = new Set(b.genes);
    const shared = sortedUnique([...aGenes].filter((gene) => bGenes.has(gene)));
    const union = new Set([...aGenes, ...bGenes]);
    const p = Math.max(0.0005, Math.pow(0.42, shared.length) * 1.8);
    return {
      disorder_a: a.disorder,
      disorder_b: b.disorder,
      n_shared: shared.length,
      shared_genes: shared,
      jaccard: ratio(shared.length, union.size),
      hypergeometric_p: Math.min(1, p),
      q_value: Math.min(1, p * 1.35),
      significant: p * 1.35 < 0.05,
    };
  });
  return overlaps.sort((a, b) => b.n_shared - a.n_shared);
}

function buildEnrichment(perDataset: PerDataset[], enabled: boolean, alpha: number) {
  if (!enabled) return { enabled: false, per_disorder: {} };
  return {
    enabled,
    per_disorder: Object.fromEntries(
      perDataset.map((dataset) => {
        const genes = new Set(dataset.genes);
        const terms: EnrichmentTerm[] = GENESETS.map((term) => {
          const overlap = term.genes.filter((gene) => genes.has(gene));
          const p = Math.min(1, Math.max(0.0005, Math.pow(0.5, overlap.length) * (term.genes.length / 4)));
          return {
            term: term.term,
            source: term.source,
            description: term.description,
            overlap_size: overlap.length,
            n_term_genes: term.genes.length,
            overlap_genes: overlap,
            p_value: p,
            q_value: Math.min(1, p * 1.4),
            significant: p * 1.4 < alpha,
          };
        })
          .filter((term) => term.overlap_size > 0)
          .sort((a, b) => a.p_value - b.p_value);
        return [dataset.disorder, { results: terms, universe_size: 14 }];
      }),
    ),
  };
}

function plainLanguageSummary(
  perDataset: PerDataset[],
  variantOverlaps: VariantOverlap[],
  geneOverlaps: GeneOverlap[],
) {
  const bestGene = geneOverlaps[0];
  const bestVariant = [...variantOverlaps].sort((a, b) => b.overlap_count - a.overlap_count)[0];
  const compared = perDataset.map((item) => item.disorder).join(", ");
  const headline = bestGene
    ? `${bestGene.disorder_a} and ${bestGene.disorder_b} had the most overlap in this fake demo.`
    : `Compared ${compared} with fake teaching data.`;
  const bullets = [
    `The app looked at ${perDataset.length} fake research tables and kept the strongest marker signals from each one.`,
    bestVariant
      ? `${bestVariant.disorder_a} and ${bestVariant.disorder_b} shared ${plural(bestVariant.overlap_count, "marker ID")}.`
      : "No shared marker IDs were found for this selection.",
    bestGene
      ? `The clearest nearby-gene overlap was ${plural(bestGene.n_shared, "shared teaching gene")}: ${bestGene.shared_genes.join(", ") || "none"}.`
      : "No nearby-gene overlap was found.",
  ];
  return {
    headline,
    bullets,
    caveat:
      "Use this as an interactive explanation of the workflow only. These fake results do not say anything about real people, risk, diagnosis, or treatment.",
  };
}

function selectVariants(
  variants: DemoVariant[],
  method: Method,
  topK: number | null,
  customThreshold: number | null,
) {
  const sorted = [...variants].sort((a, b) => (a.p_value || 1) - (b.p_value || 1));
  if (method === "top_k") return sorted.slice(0, topK || 5);
  const threshold = thresholdFor(method, customThreshold) || GENOME_WIDE;
  return sorted.filter((variant) => (variant.p_value || 1) <= threshold);
}

function genesForVariant(variant: DemoVariant, mapping: Mapping) {
  if (mapping === "window_50kb") return [variant.gene, ...(variant.nearby_genes || [])];
  return [variant.gene];
}

function decodeAnalysisId(id: string): DemoPayload | null {
  if (!id.startsWith("demo-")) return null;
  const encoded = id.replace(/^demo-[a-z0-9]+-/, "");
  try {
    return JSON.parse(Buffer.from(encoded, "base64url").toString("utf8")) as DemoPayload;
  } catch {
    return null;
  }
}

function encode(payload: DemoPayload) {
  return Buffer.from(JSON.stringify(payload), "utf8").toString("base64url");
}

function hash(value: string) {
  let output = 0;
  for (let index = 0; index < value.length; index += 1) {
    output = (output * 31 + value.charCodeAt(index)) | 0;
  }
  return Math.abs(output).toString(36);
}

function getDataset(datasetId: string) {
  const dataset = DATASETS.find((item) => item.dataset_id === datasetId);
  if (!dataset) throw new Error(`Unknown dataset: ${datasetId}`);
  return dataset;
}

function thresholdFor(method: Method, customThreshold: number | null) {
  if (method === "genome_wide") return GENOME_WIDE;
  if (method === "suggestive") return SUGGESTIVE;
  if (method === "custom") return customThreshold;
  return null;
}

function windowFor(mapping: Mapping) {
  if (mapping === "window_10kb") return 10000;
  if (mapping === "window_50kb") return 50000;
  return null;
}

function asMethod(value: unknown): Method {
  return value === "suggestive" || value === "top_k" || value === "custom" ? value : "genome_wide";
}

function asMapping(value: unknown): Mapping {
  return value === "gene_body" || value === "window_50kb" || value === "nearest" ? value : "window_10kb";
}

function positiveInt(value: unknown, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback;
}

function boundedNumber(value: unknown, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 && parsed <= 1 ? parsed : fallback;
}

function sortedUnique(values: string[]) {
  return Array.from(new Set(values)).sort((a, b) => a.localeCompare(b));
}

function pairs<T>(items: T[]) {
  const output: Array<[T, T]> = [];
  for (let left = 0; left < items.length; left += 1) {
    for (let right = left + 1; right < items.length; right += 1) {
      output.push([items[left], items[right]]);
    }
  }
  return output;
}

function ratio(numerator: number, denominator: number) {
  return denominator ? numerator / denominator : 0;
}

function plural(count: number, label: string) {
  return `${count} ${label}${count === 1 ? "" : "s"}`;
}
