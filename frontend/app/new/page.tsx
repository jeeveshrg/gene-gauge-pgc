"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api, DatasetInfo } from "@/lib/api";
import { Badge, Button, Card, Empty } from "@/components/ui";

const schema = z
  .object({
    name: z.string().optional(),
    datasets: z.array(z.string()).min(1, "Select at least one dataset."),
    significance_method: z.enum(["genome_wide", "suggestive", "top_k", "custom"]),
    top_k: z.coerce.number().int().positive().optional(),
    custom_threshold: z.coerce.number().gt(0).lte(1).optional(),
    mapping_method: z.enum(["gene_body", "window_10kb", "window_50kb", "nearest"]),
    run_enrichment: z.boolean(),
  })
  .refine((v) => v.significance_method !== "top_k" || !!v.top_k, {
    message: "top_k is required for the top-k method.",
    path: ["top_k"],
  })
  .refine((v) => v.significance_method !== "custom" || !!v.custom_threshold, {
    message: "A custom threshold is required for the custom method.",
    path: ["custom_threshold"],
  });

type FormValues = z.infer<typeof schema>;

export default function NewAnalysisPage() {
  const router = useRouter();
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [configMap, setConfigMap] = useState<Record<string, string>>({});
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      datasets: [],
      significance_method: "genome_wide",
      mapping_method: "window_10kb",
      run_enrichment: true,
    },
  });

  const sigMethod = watch("significance_method");

  useEffect(() => {
    (async () => {
      try {
        const res = await api.datasets();
        setDatasets(res.datasets);
        // Load the first config id per dataset for the selection payload.
        const map: Record<string, string> = {};
        for (const d of res.datasets) {
          const c = await api.configs(d.dataset_id);
          if (c.configs[0]) map[d.dataset_id] = c.configs[0].config_id;
        }
        setConfigMap(map);
      } catch (e) {
        setLoadError(e instanceof Error ? e.message : String(e));
      }
    })();
  }, []);

  const onSubmit = async (values: FormValues) => {
    setBusy(true);
    setSubmitError(null);
    try {
      const selections = values.datasets.map((dsId) => ({
        dataset_id: dsId,
        config_id: configMap[dsId],
      }));
      const payload = {
        name: values.name || null,
        selections,
        significance_method: values.significance_method,
        top_k: values.top_k ?? null,
        custom_threshold: values.custom_threshold ?? null,
        mapping_method: values.mapping_method,
        run_enrichment: values.run_enrichment,
      };
      const created = await api.createAnalysis(payload);
      await api.runAnalysis(created.id);
      router.push(`/analysis/${created.id}`);
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-xl font-semibold text-ink">New analysis</h1>
        <p className="text-sm text-ink-muted mt-1">
          Select two or more disorders to compare GWAS overlap. All parameters
          are recorded for reproducibility.
        </p>
      </div>

      {loadError && (
        <Card>
          <Empty>Could not load datasets: {loadError}</Empty>
        </Card>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <Card title="1. Datasets" subtitle="Choose the disorders to compare">
          <div className="space-y-2">
            {datasets.map((d) => (
              <label
                key={d.dataset_id}
                className="flex items-start gap-2 border border-line rounded-sm p-2 cursor-pointer hover:bg-panel"
              >
                <input
                  type="checkbox"
                  value={d.dataset_id}
                  className="mt-1"
                  {...register("datasets")}
                />
                <div>
                  <div className="text-sm font-medium text-ink">
                    {d.disorder}{" "}
                    <span className="coord text-ink-faint">{d.dataset_id}</span>
                  </div>
                  <div className="text-xs text-ink-muted">{d.publication}</div>
                </div>
              </label>
            ))}
          </div>
          {errors.datasets && (
            <p className="text-xs text-red-600 mt-2">{errors.datasets.message}</p>
          )}
        </Card>

        <Card title="2. Parameters">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="text-xs font-medium text-ink-muted">Analysis name</span>
              <input
                {...register("name")}
                placeholder="Optional label"
                className="mt-1 w-full border border-line rounded-sm px-2 py-1.5 text-sm"
              />
            </label>

            <label className="block">
              <span className="text-xs font-medium text-ink-muted">Significance</span>
              <select
                {...register("significance_method")}
                className="mt-1 w-full border border-line rounded-sm px-2 py-1.5 text-sm bg-surface"
              >
                <option value="genome_wide">Genome-wide (p &lt; 5e-8)</option>
                <option value="suggestive">Suggestive (p &lt; 1e-5)</option>
                <option value="top_k">Top-k by p-value</option>
                <option value="custom">Custom threshold</option>
              </select>
            </label>

            {sigMethod === "top_k" && (
              <label className="block">
                <span className="text-xs font-medium text-ink-muted">Top-k</span>
                <input
                  type="number"
                  {...register("top_k")}
                  className="mt-1 w-full border border-line rounded-sm px-2 py-1.5 text-sm"
                />
                {errors.top_k && (
                  <p className="text-xs text-red-600 mt-1">{errors.top_k.message}</p>
                )}
              </label>
            )}

            {sigMethod === "custom" && (
              <label className="block">
                <span className="text-xs font-medium text-ink-muted">P threshold</span>
                <input
                  type="number"
                  step="any"
                  {...register("custom_threshold")}
                  className="mt-1 w-full border border-line rounded-sm px-2 py-1.5 text-sm"
                />
                {errors.custom_threshold && (
                  <p className="text-xs text-red-600 mt-1">
                    {errors.custom_threshold.message}
                  </p>
                )}
              </label>
            )}

            <label className="block">
              <span className="text-xs font-medium text-ink-muted">
                Variant-to-gene mapping
              </span>
              <select
                {...register("mapping_method")}
                className="mt-1 w-full border border-line rounded-sm px-2 py-1.5 text-sm bg-surface"
              >
                <option value="gene_body">Gene body</option>
                <option value="window_10kb">Gene body ±10 kb</option>
                <option value="window_50kb">Gene body ±50 kb</option>
                <option value="nearest">Nearest gene</option>
              </select>
            </label>

            <label className="flex items-center gap-2 sm:col-span-2">
              <input type="checkbox" {...register("run_enrichment")} />
              <span className="text-sm text-ink">Run pathway enrichment (GO / Reactome)</span>
            </label>
          </div>
        </Card>

        {submitError && (
          <div className="border border-red-200 bg-red-50 text-red-800 text-sm rounded-sm p-3">
            {submitError}
          </div>
        )}

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={busy}>
            {busy ? "Running analysis…" : "Create & run analysis"}
          </Button>
          <Badge tone="info">Positional mapping ≠ causality</Badge>
        </div>
      </form>
    </div>
  );
}
