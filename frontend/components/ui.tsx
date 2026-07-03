// Lightweight shadcn/ui-style primitives, hand-rolled to keep the serious,
// neutral scientific aesthetic (thin borders, dense layout, no gradients).
import clsx from "clsx";
import Link from "next/link";
import { ReactNode } from "react";

export function Card({
  children,
  className,
  title,
  subtitle,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
}) {
  return (
    <section className={clsx("border border-line bg-surface rounded-sm", className)}>
      {(title || subtitle) && (
        <header className="border-b border-line px-4 py-3">
          {title && <h2 className="text-sm font-semibold text-ink">{title}</h2>}
          {subtitle && <p className="text-xs text-ink-muted mt-0.5">{subtitle}</p>}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "ok" | "warn" | "info";
}) {
  const tones: Record<string, string> = {
    neutral: "bg-panel text-ink-muted border-line",
    ok: "bg-green-50 text-green-800 border-green-200",
    warn: "bg-amber-50 text-amber-800 border-amber-200",
    info: "bg-blue-50 text-blue-800 border-blue-200",
  };
  return (
    <span
      className={clsx(
        "inline-flex items-center border rounded px-1.5 py-0.5 text-xs font-medium",
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}

export function Button({
  children,
  onClick,
  type = "button",
  variant = "primary",
  disabled,
}: {
  children: ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
  variant?: "primary" | "secondary";
  disabled?: boolean;
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        "inline-flex items-center justify-center rounded-sm border px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
        variant === "primary"
          ? "bg-ink text-white border-ink hover:bg-black"
          : "bg-surface text-ink border-line hover:bg-panel",
      )}
    >
      {children}
    </button>
  );
}

export function LinkButton({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center justify-center rounded-sm border border-line bg-surface px-3 py-1.5 text-sm font-medium text-ink hover:bg-panel"
    >
      {children}
    </Link>
  );
}

export function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="border border-line rounded-sm bg-surface px-3 py-2">
      <div className="text-xs uppercase tracking-wide text-ink-faint">{label}</div>
      <div className="text-lg font-semibold text-ink tabular-nums">{value}</div>
    </div>
  );
}

export function LimitationsNote({ items }: { items: string[] }) {
  return (
    <div className="border border-amber-200 bg-amber-50 rounded-sm p-4">
      <h3 className="text-sm font-semibold text-amber-900">Limitations & scientific scope</h3>
      <ul className="mt-2 list-disc pl-5 space-y-1 text-xs text-amber-900">
        {items.map((it, i) => (
          <li key={i}>{it}</li>
        ))}
      </ul>
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="text-sm text-ink-muted italic">{children}</p>;
}
