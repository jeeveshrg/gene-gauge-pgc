import { Card, LinkButton, Badge } from "@/components/ui";

const FEATURES = [
  ["Pick conditions", "Choose two or three mental-health research datasets to compare."],
  ["Find strong signals", "Keep the fake genetic markers that look strongest in each dataset."],
  ["Compare overlap", "See which markers and nearby teaching genes appear in more than one dataset."],
  ["Read the takeaway", "Start with a plain-English summary, then inspect the detailed tables if you want."],
];

export default function HomePage() {
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="max-w-2xl">
          <h1 className="text-xl font-semibold text-ink">
            Compare mental-health research signals in plain English
          </h1>
          <p className="mt-2 text-sm text-ink-muted">
            GeneGauge PGC is a simple demo for understanding how researchers
            compare large genetics studies. Pick a few conditions, run the fake
            data, and see whether the strongest markers point near some of the
            same teaching genes.
          </p>
          <div className="mt-4 flex gap-2">
            <LinkButton href="/new">Start simple demo</LinkButton>
            <LinkButton href="/examples">Run ready-made example</LinkButton>
          </div>
        </div>
        <Badge tone="info">Fake data · no biology background needed</Badge>
      </div>

      <Card title="What happens" subtitle="The demo is intentionally small and readable">
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
        <strong>Important:</strong> this public Vercel demo uses fake teaching
        data. It does not diagnose anything, predict risk, or make claims about
        real biology. It is only meant to make the workflow easy to understand.
      </div>
    </div>
  );
}
