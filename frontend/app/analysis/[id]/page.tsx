"use client";

import { useEffect, useState } from "react";
import { AnalysisResult, api, fmtP } from "@/lib/api";
import { Badge, Card, Empty, LimitationsNote, Stat } from "@/components/ui";

export default function AnalysisPage({ params }: { params: { id: string } }) {
  const [data, setData] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setData(await api.getAnalysis(params.id));
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    })();
  }, [params.id]);

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

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink">
            {data.name || "Analysis"}{" "}
            <span className="coord text-ink-faint text-sm">{data.id}</span>
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
            Markdown report
          </a>
          <a
            className="text-sm text-accent underline"
            href={api.reportUrl(data.id, "pdf")}
            target="_blank"
            rel="noreferrer"
          >
            PDF
          </a>
        </div>
      </div>

      <div className="grid gap-3 grid-cols-2 sm:grid-cols-4">
        <Stat label="Disorders" value={data.per_dataset.length} />
        <Stat label="Significance" value={sig.method} />
        <Stat label="Threshold" value={sig.threshold ? fmtP(sig.threshold) : sig.k ?? "—"} />
        <Stat label="Mapping" value={mapp.method} />
      </div>

      {/* Per-dataset significant variants */}
      {data.per_dataset.map((d) => (
        <Card
          key={d.disorder}
          title={`${d.disorder}`}
          subtitle={`${d.n_significant} significant of ${d.n_total_variants} variants · ${d.n_genes} mapped genes · source: ${d.source}`}
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
        <Card title="Pairwise variant overlap" subtitle="Shared significant variants between disorders">
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
          title="Pairwise gene overlap"
          subtitle="Positional candidate genes; hypergeometric enrichment with BH FDR"
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
          <Card title="Pathway enrichment" subtitle="Over-representation (GO:BP / Reactome), BH FDR">
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
