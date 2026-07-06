"use client";

import { use, useEffect, useState } from "react";
import { AnalysisResult, api, fmtP } from "@/lib/api";
import { Badge, Card, Empty, LimitationsNote, Stat } from "@/components/ui";

const SIGNAL_LABELS: Record<string, string> = {
  genome_wide: "Strongest signals",
  suggestive: "Exploratory signals",
  top_k: "Top markers",
  custom: "Custom cutoff",
};

const MAPPING_LABELS: Record<string, string> = {
  gene_body: "Inside genes",
  window_10kb: "Nearby genes",
  window_50kb: "Wider nearby window",
  nearest: "Nearest gene",
};

export default function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [data, setData] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setData(await api.getAnalysis(id));
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    })();
  }, [id]);

  if (error) return <Card><Empty>Could not load analysis: {error}</Empty></Card>;
  if (!data) return <Card><Empty>Loading analysis…</Empty></Card>;
  if (data.status !== "completed")
    return (
      <Card title={`Analysis ${data.id}`}>
        <Empty>Status: {data.status}. {data.error}</Empty>
      </Card>
    );

  const sig = data.params.significance;
  const mapp = data.params.mapping;
  const displayId = data.id.startsWith("demo-") ? data.id.slice(0, 17) : data.id;
  const strongestGenePair = data.gene_overlaps[0];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink">
            {data.name || "Analysis"}{" "}
            <span className="coord text-ink-faint text-sm">{displayId}</span>
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            {data.per_dataset.map((d) => d.disorder).join(" · ")}
          </p>
        </div>
        <div className="flex gap-2 items-center">
          {data.params.demo_mode && <Badge tone="warn">Demo mode</Badge>}
          <a
            className="text-sm text-accent underline"
            href={api.reportUrl(data.id, "markdown")}
            target="_blank"
            rel="noreferrer"
          >
            Plain report
          </a>
        </div>
      </div>

      <Card title="What happened?" subtitle="Plain-English takeaway">
        <div className="space-y-3">
          <p className="text-sm font-medium text-ink">
            {data.plain_language?.headline ||
              "The demo compared your selected fake research datasets."}
          </p>
          <ul className="list-disc pl-5 text-sm text-ink-muted space-y-1">
            {(data.plain_language?.bullets || buildFallbackBullets(data)).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <div className="border border-amber-200 bg-amber-50 rounded-sm p-3 text-xs text-amber-900">
            {data.plain_language?.caveat ||
              "These are teaching results from fake data. They are not medical or biological claims."}
          </div>
        </div>
      </Card>

      <div className="grid gap-3 grid-cols-2 sm:grid-cols-4">
        <Stat label="Groups compared" value={data.per_dataset.length} />
        <Stat label="Marker rule" value={SIGNAL_LABELS[sig.method] || sig.method} />
        <Stat label="Threshold" value={sig.threshold ? fmtP(sig.threshold) : sig.k ?? "—"} />
        <Stat label="Gene rule" value={MAPPING_LABELS[mapp.method] || mapp.method} />
      </div>

      {strongestGenePair && (
        <Card title="Most shared nearby genes" subtitle="A quick read before the tables">
          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <div className="text-xs uppercase text-ink-faint">Pair</div>
              <div className="text-sm font-medium text-ink">
                {strongestGenePair.disorder_a} vs {strongestGenePair.disorder_b}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase text-ink-faint">Shared genes</div>
              <div className="text-sm font-medium text-ink">{strongestGenePair.n_shared}</div>
            </div>
            <div>
              <div className="text-xs uppercase text-ink-faint">Names</div>
              <div className="coord text-ink-muted">
                {strongestGenePair.shared_genes.join(", ") || "none"}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Per-dataset significant variants */}
      {data.per_dataset.map((d) => (
        <Card
          key={d.disorder}
          title={`Signals found in ${d.disorder}`}
          subtitle={`${d.n_significant} fake markers passed the rule · ${d.n_genes} nearby teaching genes`}
        >
          {d.normalization.warnings.length > 0 && (
            <div className="mb-2 text-xs text-amber-800">
              {d.normalization.warnings.join(" ")}
            </div>
          )}
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>rsID</th>
                  <th>Chr:Pos</th>
                  <th>EA/OA</th>
                  <th>Beta</th>
                  <th>OR</th>
                  <th>P</th>
                </tr>
              </thead>
              <tbody>
                {d.significant_variants.slice(0, 25).map((v, i) => (
                  <tr key={i}>
                    <td className="coord">{v.rsid ?? "—"}</td>
                    <td className="coord">
                      {v.chromosome}:{v.position}
                    </td>
                    <td className="coord">
                      {v.effect_allele}/{v.other_allele}
                    </td>
                    <td className="coord">{v.beta?.toFixed(4) ?? "—"}</td>
                    <td className="coord">{v.odds_ratio?.toFixed(4) ?? "—"}</td>
                    <td className="coord">{fmtP(v.p_value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {d.genes.length > 0 && (
            <p className="mt-2 text-xs text-ink-muted">
              <span className="font-medium">Mapped genes:</span>{" "}
              {d.genes.map((g) => (
                <span key={g} className="coord mr-1">
                  {g}
                </span>
              ))}
            </p>
          )}
        </Card>
      ))}

      {/* Variant overlap */}
      {data.variant_overlaps.length > 0 && (
        <Card
          title="Shared marker IDs"
          subtitle="Marker IDs that appeared in more than one selected dataset"
        >
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Pair</th>
                  <th>Shared rsIDs</th>
                  <th>Jaccard (rsID)</th>
                  <th>Jaccard (pos)</th>
                  <th>Direction concordance</th>
                  <th>Shared variants</th>
                </tr>
              </thead>
              <tbody>
                {data.variant_overlaps.map((o, i) => {
                  const dc = o.direction_concordance;
                  return (
                    <tr key={i}>
                      <td>{o.disorder_a} vs {o.disorder_b}</td>
                      <td className="tabular-nums">{o.overlap_count}</td>
                      <td className="tabular-nums">{o.jaccard_rsid.toFixed(3)}</td>
                      <td className="tabular-nums">{o.jaccard_position.toFixed(3)}</td>
                      <td className="tabular-nums">
                        {dc.n_concordant}/{dc.n_comparable}
                        {dc.concordance_rate !== null &&
                          ` (${Math.round(dc.concordance_rate * 100)}%)`}
                      </td>
                      <td className="coord">{o.shared_rsids.join(", ") || "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Gene overlap */}
      {data.gene_overlaps.length > 0 && (
        <Card
          title="Shared nearby genes"
          subtitle="Teaching genes near the selected fake markers"
        >
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Pair</th>
                  <th>Shared</th>
                  <th>Jaccard</th>
                  <th>Hypergeom. p</th>
                  <th>FDR q</th>
                  <th>Shared genes</th>
                </tr>
              </thead>
              <tbody>
                {data.gene_overlaps.map((o, i) => (
                  <tr key={i}>
                    <td>{o.disorder_a} vs {o.disorder_b}</td>
                    <td className="tabular-nums">{o.n_shared}</td>
                    <td className="tabular-nums">{o.jaccard.toFixed(3)}</td>
                    <td className="tabular-nums">{fmtP(o.hypergeometric_p)}</td>
                    <td className="tabular-nums">
                      {fmtP(o.q_value)}{" "}
                      {o.significant && <Badge tone="ok">FDR&lt;α</Badge>}
                    </td>
                    <td className="coord">{o.shared_genes.join(", ") || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Enrichment */}
      {data.enrichment.enabled &&
        Object.keys(data.enrichment.per_disorder).length > 0 && (
          <Card
            title="Simple gene themes"
            subtitle="Teaching themes built from the nearby genes"
          >
            <div className="space-y-4">
              {Object.entries(data.enrichment.per_disorder).map(([disorder, res]) => (
                <div key={disorder}>
                  <h3 className="text-sm font-semibold text-ink mb-1">{disorder}</h3>
                  {res.results.length === 0 ? (
                    <Empty>No enriched terms.</Empty>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Term</th>
                            <th>Source</th>
                            <th>Overlap</th>
                            <th>Term size</th>
                            <th>p</th>
                            <th>FDR q</th>
                          </tr>
                        </thead>
                        <tbody>
                          {res.results.slice(0, 8).map((t, i) => (
                            <tr key={i}>
                              <td className="coord">{t.term}</td>
                              <td>{t.source}</td>
                              <td className="tabular-nums">{t.overlap_size}</td>
                              <td className="tabular-nums">{t.n_term_genes}</td>
                              <td className="tabular-nums">{fmtP(t.p_value)}</td>
                              <td className="tabular-nums">{fmtP(t.q_value)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        )}

      <LimitationsNote items={data.limitations} />
    </div>
  );
}

function buildFallbackBullets(data: AnalysisResult) {
  const best = data.gene_overlaps[0];
  return [
    `The app compared ${data.per_dataset.length} selected datasets.`,
    best
      ? `${best.disorder_a} and ${best.disorder_b} shared ${best.n_shared} nearby genes.`
      : "No nearby-gene overlap was found.",
    "Use the tables below for the detailed marker and gene lists.",
  ];
}
