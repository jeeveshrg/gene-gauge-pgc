"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Button, Card, Empty } from "@/components/ui";

const EXAMPLE = {
  name: "Demo: SCZ vs BIP vs MDD (genome-wide, ±10kb)",
  selections: [
    { dataset_id: "pgc-schizophrenia", config_id: "scz2022" },
    { dataset_id: "pgc-bipolar", config_id: "bip2021" },
    { dataset_id: "pgc-mdd", config_id: "mdd2019" },
  ],
  significance_method: "genome_wide",
  mapping_method: "window_10kb",
  run_enrichment: true,
};

export default function ExamplesPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runExample = async () => {
    setBusy(true);
    setError(null);
    try {
      const created = await api.createAnalysis(EXAMPLE);
      await api.runAnalysis(created.id);
      router.push(`/analysis/${created.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-xl font-semibold text-ink">Examples</h1>
        <p className="text-sm text-ink-muted mt-1">
          Run a pre-configured demo analysis on the bundled mock data.
        </p>
      </div>

      <Card
        title="Three-disorder psychiatric overlap"
        subtitle="Schizophrenia · Bipolar Disorder · Major Depressive Disorder"
      >
        <ul className="text-sm text-ink-muted list-disc pl-5 space-y-1">
          <li>Significance: genome-wide (p &lt; 5e-8)</li>
          <li>Mapping: gene body ±10 kb</li>
          <li>Pathway enrichment enabled (GO:BP / Reactome)</li>
        </ul>
        <div className="mt-4">
          <Button onClick={runExample} disabled={busy}>
            {busy ? "Running…" : "Run example analysis"}
          </Button>
        </div>
        {error && (
          <div className="mt-3">
            <Empty>Could not run example: {error}</Empty>
          </div>
        )}
      </Card>

      <div className="border border-amber-200 bg-amber-50 rounded-sm p-4 text-xs text-amber-900">
        This example uses small bundled mock datasets. Results are illustrative
        of the workflow only and carry no biological or clinical meaning.
      </div>
    </div>
  );
}
