import { Card, LimitationsNote } from "@/components/ui";

export default function MethodsPage() {
  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-xl font-semibold text-ink">Methods & limitations</h1>
        <p className="text-sm text-ink-muted mt-1">
          How GeneGauge PGC processes GWAS summary statistics, and what its
          results can and cannot support.
        </p>
      </div>

      <Card title="1. Data loading & normalization">
        <p className="text-sm text-ink-muted">
          Datasets are loaded from Hugging Face (OpenMed/PGC) via streaming, or
          from bundled mock data in demo mode. Provider schemas differ in column
          naming and effect encoding, so each dataset is normalized to a common
          schema. Odds ratios are converted to beta via natural log; betas yield
          odds ratios via exponentiation. A missing p-value column is a hard
          error rather than a silent empty result.
        </p>
      </Card>

      <Card title="2. Significance thresholds">
        <ul className="text-sm text-ink-muted list-disc pl-5 space-y-1">
          <li>Genome-wide significant: <span className="coord">p &lt; 5e-8</span></li>
          <li>Suggestive: <span className="coord">p &lt; 1e-5</span></li>
          <li>Top-k by ascending p-value</li>
          <li>Custom threshold</li>
        </ul>
      </Card>

      <Card title="3. Variant-to-gene mapping">
        <p className="text-sm text-ink-muted">
          Positional mapping only: gene body, gene body ±10 kb, gene body ±50 kb,
          or nearest gene on the same chromosome. Range joins run in DuckDB.
          Positional proximity identifies <em>candidate</em> genes; it does not
          identify causal genes.
        </p>
      </Card>

      <Card title="4. Overlap & enrichment statistics">
        <ul className="text-sm text-ink-muted list-disc pl-5 space-y-1">
          <li>Variant overlap: shared rsIDs, shared chromosome:position, Jaccard.</li>
          <li>
            Effect-direction concordance for shared variants (with allele-flip
            alignment).
          </li>
          <li>Gene overlap: shared genes, Jaccard, hypergeometric enrichment.</li>
          <li>Pathway ORA against GO:BP and Reactome gene sets.</li>
          <li>Multiple testing controlled with Benjamini-Hochberg FDR.</li>
        </ul>
      </Card>

      <Card title="5. Reproducibility">
        <p className="text-sm text-ink-muted">
          Every analysis records its dataset configs, source references,
          significance method and threshold, mapping method, annotation and
          gene-set files, tool version, and timestamp. The Markdown report
          embeds this metadata so a result can be regenerated and audited.
        </p>
      </Card>

      <LimitationsNote
        items={[
          "These are GWAS summary statistics, not curated gene lists.",
          "Positional variant-to-gene mapping does not establish causality.",
          "Overlap between disorders does not imply shared biology or clinical relationship.",
          "No clinical or diagnostic claims are made; individual risk is never predicted.",
          "Demo mode uses small mock datasets and a tiny annotation — results are illustrative only.",
          "Enrichment depends on the chosen gene-set collection and gene universe.",
        ]}
      />
    </div>
  );
}
