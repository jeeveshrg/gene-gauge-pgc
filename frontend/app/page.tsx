import { Card, LinkButton, Badge } from "@/components/ui";

const FEATURES = [
  ["Dataset browser", "Browse available OpenMed/PGC psychiatric GWAS datasets and configs."],
  ["Schema normalization", "Map heterogeneous provider schemas (OR / beta / log-odds) to one common GWAS schema."],
  ["Significant variants", "Genome-wide (p<5e-8), suggestive (p<1e-5), or top-k selection."],
  ["Variant overlap", "Shared rsIDs, position matches, Jaccard, and effect-direction concordance."],
  ["Gene mapping", "Positional mapping: gene body, ±10kb, ±50kb, or nearest gene."],
  ["Gene & pathway overlap", "Hypergeometric enrichment with Benjamini-Hochberg FDR; GO/Reactome ORA."],
  ["Reproducible reports", "Markdown reports documenting configs, thresholds, mapping, and metadata."],
  ["Demo mode", "Runs fully offline on bundled mock data when no external services are configured."],
];

export default function HomePage() {
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="max-w-2xl">
          <h1 className="text-xl font-semibold text-ink">
            Psychiatric GWAS overlap explorer
          </h1>
          <p className="mt-2 text-sm text-ink-muted">
            GeneGauge PGC loads Psychiatric Genomics Consortium GWAS summary
            statistics, normalizes their schemas, extracts significant variants,
            maps them to positional candidate genes, and compares overlap across
            disorders — with explicit limitations on every result.
          </p>
          <div className="mt-4 flex gap-2">
            <LinkButton href="/new">Start a new analysis</LinkButton>
            <LinkButton href="/examples">See an example</LinkButton>
          </div>
        </div>
        <Badge tone="info">GWAS summary statistics — not gene lists</Badge>
      </div>

      <Card title="What this tool does" subtitle="Twelve core capabilities">
        <div className="grid gap-3 sm:grid-cols-2">
          {FEATURES.map(([title, desc]) => (
            <div key={title} className="border border-line rounded-sm p-3">
              <div className="text-sm font-medium text-ink">{title}</div>
              <div className="text-xs text-ink-muted mt-1">{desc}</div>
            </div>
          ))}
        </div>
      </Card>

      <div className="border border-amber-200 bg-amber-50 rounded-sm p-4 text-xs text-amber-900">
        <strong>Scientific scope.</strong> These datasets are GWAS summary
        statistics, not curated gene lists. Positional variant-to-gene mapping
        does not establish causality, and overlap between disorders does not
        imply shared biology or clinical relationship. No clinical claims are
        made and individual risk is never predicted.
      </div>
    </div>
  );
}
