import Link from "next/link";
import { api } from "@/lib/api";
import { Badge, Card, Empty } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function HistoryPage() {
  let analyses;
  let error: string | null = null;
  try {
    analyses = (await api.listAnalyses()).analyses;
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink">Analysis history</h1>
        <p className="text-sm text-ink-muted mt-1">Previously run analyses.</p>
      </div>

      {error && (
        <Card>
          <Empty>Could not load history: {error}</Empty>
        </Card>
      )}

      {analyses && analyses.length === 0 && (
        <Card>
          <Empty>
            No analyses yet. <Link className="text-accent underline" href="/new">Start one.</Link>
          </Empty>
        </Card>
      )}

      {analyses && analyses.length > 0 && (
        <Card>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>Disorders</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {analyses.map((a) => (
                  <tr key={a.id}>
                    <td className="coord">{a.id}</td>
                    <td>{a.name || "—"}</td>
                    <td>{a.disorders.join(", ")}</td>
                    <td>
                      {a.status === "completed" ? (
                        <Badge tone="ok">completed</Badge>
                      ) : a.status === "failed" ? (
                        <Badge tone="warn">failed</Badge>
                      ) : (
                        <Badge>{a.status}</Badge>
                      )}
                    </td>
                    <td className="coord">{a.created_at?.slice(0, 19).replace("T", " ")}</td>
                    <td>
                      <Link className="text-accent underline" href={`/analysis/${a.id}`}>
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
