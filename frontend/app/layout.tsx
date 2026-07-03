import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "GeneGauge PGC — Psychiatric GWAS Overlap Explorer",
  description:
    "Reproducible exploration of psychiatric GWAS summary-statistic overlap across disorders.",
};

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/datasets", label: "Datasets" },
  { href: "/new", label: "New analysis" },
  { href: "/history", label: "History" },
  { href: "/examples", label: "Examples" },
  { href: "/methods", label: "Methods" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <header className="border-b border-line bg-surface">
          <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between">
            <Link href="/" className="flex items-baseline gap-2">
              <span className="font-mono text-sm font-bold tracking-tight text-ink">
                GeneGauge
              </span>
              <span className="font-mono text-xs text-ink-muted">PGC</span>
            </Link>
            <nav className="flex flex-wrap gap-4 text-sm">
              {NAV.map((n) => (
                <Link
                  key={n.href}
                  href={n.href}
                  className="text-ink-muted hover:text-ink"
                >
                  {n.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
        <footer className="border-t border-line bg-surface mt-12">
          <div className="mx-auto max-w-6xl px-4 py-4 text-xs text-ink-faint">
            GeneGauge PGC is a research/education tool for exploring GWAS summary
            statistics. It makes no clinical or diagnostic claims and does not
            predict disorder risk.
          </div>
        </footer>
      </body>
    </html>
  );
}
