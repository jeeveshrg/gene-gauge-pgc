import { api } from "@/lib/api";
import { Badge, Card, Empty, LinkButton } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function DatasetsPage() {
  let datasets;
  let demo = false;
  let error: string | null = null;
  try {
    const res = await api.datasets();
    datasets = res.datasets;
    demo = res.demo_mode;
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Datasets</h1>
          <p className="text-sm text-ink-muted mt-1">
            Fake teaching datasets available in the public Vercel demo.
          </p>
        </div>
        {demo && <Badge tone="warn">Demo mode — fake data</Badge>}
      </div>

      {error && (
        <Card>
          <Empty>
            Could not load the demo API ({error}). Try refreshing the page.
          </Empty>
        </Card>
      )}

      {datasets && (
        <div className="grid gap-4 sm:grid-cols-2">
          {datasets.map((d) => (
            <Card key={d.dataset_id} title={d.disorder} subtitle={d.description}>
              <dl className="text-xs space-y-1">
                <div className="flex justify-between gap-2">
                  <dt className="text-ink-faint">Dataset ID</dt>
                  <dd className="coord">{d.dataset_id}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-ink-faint">HF repo</dt>
                  <dd className="coord">{d.hf_repo}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-ink-faint">Configs</dt>
                  <dd>{d.n_configs}</dd>
                </div>
                <div className="pt-1">
                  <dt className="text-ink-faint">Publication</dt>
                  <dd className="text-ink-muted">{d.publication}</dd>
                </div>
              </dl>
              <div className="mt-3">
                <LinkButton href="/new">Use in analysis</LinkButton>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
