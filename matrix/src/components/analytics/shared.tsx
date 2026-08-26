"use client";

/**
 * Behavioral Matrix — shared institutional primitives.
 * Data states are honest: loading, error, empty ("aucune donnée
 * disponible") — never a fabricated placeholder value.
 */
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Database, Loader2, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

// ---------------------------------------------------------------------------
// Data hook
// ---------------------------------------------------------------------------
export function useMatrixData<T>(url: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(Boolean(url));
  const [error, setError] = useState<string | null>(null);
  const [isEmpty, setIsEmpty] = useState(false);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (!url) return;
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(url, { signal: controller.signal });
        const json = await res.json();
        if (!res.ok && json?.message) throw new Error(json.message);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setIsEmpty(Boolean(json?.empty));
        setData(json as T);
        setLoading(false);
      } catch (e) {
        if (controller.signal.aborted) return;
        setError((e as Error).message);
        setLoading(false);
      }
    }
    load();
    return () => {
      controller.abort();
    };
  }, [url, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { data, loading, error, isEmpty, reload };
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------
export function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${(v * 100).toFixed(digits)} %`;
}
export function fmtNum(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return new Intl.NumberFormat("fr-FR").format(Math.round(v));
}
export function fmtSigned(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}`;
}

/**
 * Categorical department palette — muted, print-grade hues that hold
 * contrast on ivory paper (Economist-register, never neon).
 */
export const DEPT_COLORS: Record<string, string> = {
  "1st": "#6E5380", // plum
  "2nd": "#B8863B", // ochre gold
  "3rd": "#4F7A5D", // sage
  "4th": "#A35555", // brick
  unknown: "#8B8577", // warm gray
};
export function deptColor(dept: string | null | undefined): string {
  return DEPT_COLORS[dept ?? "unknown"] ?? "#8B8577";
}
export const DEPT_LABELS: Record<string, string> = {
  "1st": "1er dép.",
  "2nd": "2e dép.",
  "3rd": "3e dép.",
  "4th": "4e dép.",
  unknown: "indét.",
};

// ---------------------------------------------------------------------------
// Layout primitives
// ---------------------------------------------------------------------------
export function ModulePanel({
  code,
  title,
  subtitle,
  source,
  actions,
  children,
  className,
}: {
  code: string;
  title: string;
  subtitle?: string;
  source?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("panel rounded-md flex flex-col min-h-0", className)} aria-label={title}>
      <header className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-border px-5 py-3.5">
        <span className="mono text-[11px] font-semibold text-primary border border-primary/25 rounded-sm px-1.5 py-0.5 bg-primary/[0.04]">
          {code}
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="serif-display text-[15px] font-semibold leading-snug text-foreground truncate text-balance">
            {title}
          </h2>
          {subtitle ? <p className="text-xs text-muted-foreground truncate">{subtitle}</p> : null}
        </div>
        {actions}
        {source ? (
          <span className="label-caps text-muted-foreground/80 hidden lg:inline">
            Source · {source}
          </span>
        ) : null}
      </header>
      <div className="p-5 min-h-0 flex-1">{children}</div>
    </section>
  );
}

export function KpiChip({
  label,
  value,
  sub,
  tone = "neutral",
  className,
}: {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  tone?: "neutral" | "pos" | "neg" | "mix";
  className?: string;
}) {
  const toneClass =
    tone === "pos" ? "text-pos"
    : tone === "neg" ? "text-neg"
    : tone === "mix" ? "text-mix"
    : "text-foreground";
  return (
    <div className={cn("rounded-md border border-border bg-card px-3.5 py-2.5 min-w-0", className)}>
      <div className="label-caps text-muted-foreground truncate">{label}</div>
      <div className={cn("mono text-lg font-medium leading-tight truncate", toneClass)}>{value}</div>
      {sub ? <div className="mono text-[10px] text-muted-foreground truncate">{sub}</div> : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Honest states
// ---------------------------------------------------------------------------
export function TerminalLoader({ label = "Interrogation de l'index" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-14 text-center" role="status">
      <Loader2 className="h-4 w-4 animate-spin text-primary" aria-hidden />
      <p className="label-caps text-muted-foreground">{label}…</p>
    </div>
  );
}

export function EmptyState({
  title = "Aucune donnée disponible",
  message,
  hint,
}: {
  title?: string;
  message?: string;
  hint?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 border border-dashed border-border rounded-md py-14 px-6 text-center max-w-2xl mx-auto">
      <Database className="h-5 w-5 text-muted-foreground" aria-hidden />
      <p className="label-caps text-mix">{title}</p>
      {message ? (
        <p className="text-xs text-muted-foreground leading-relaxed">{message}</p>
      ) : null}
      {hint ? <p className="mono text-[10px] text-muted-foreground/80">{hint}</p> : null}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 border border-destructive/30 bg-destructive/[0.04] rounded-md py-12 px-6 text-center max-w-2xl mx-auto" role="alert">
      <AlertTriangle className="h-5 w-5 text-neg" aria-hidden />
      <p className="label-caps text-neg">Erreur de chargement des données</p>
      <p className="text-xs text-muted-foreground leading-relaxed break-all">{message}</p>
    </div>
  );
}

export function ModuleBody<T>({
  loading,
  error,
  isEmpty,
  emptyMessage,
  data,
  children,
}: {
  loading: boolean;
  error: string | null;
  isEmpty: boolean;
  emptyMessage?: string;
  data: T | null;
  children: (data: T) => React.ReactNode;
}) {
  if (loading) return <TerminalLoader />;
  if (error) return <ErrorState message={error} />;
  if (isEmpty || !data) return <EmptyState message={emptyMessage} />;
  return <>{children(data)}</>;
}

export function ReloadButton({ onClick }: { onClick: () => void }) {
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={onClick}
      className="h-7 px-2.5 label-caps gap-1.5"
      aria-label="Recharger les données réelles"
    >
      <RefreshCw className="h-3 w-3" aria-hidden />
      Rafraîchir
    </Button>
  );
}

// ---------------------------------------------------------------------------
// Data visualization primitives
// ---------------------------------------------------------------------------
export function WilsonBar({
  rate,
  low,
  high,
  tone = "pos",
}: {
  rate: number;
  low: number;
  high: number;
  tone?: "pos" | "neg" | "mix";
}) {
  const barClass =
    tone === "pos" ? "bg-pos"
    : tone === "neg" ? "bg-neg"
    : "bg-mix";
  return (
    <div className="relative h-2 w-full min-w-16 bg-secondary rounded-sm overflow-hidden" title={`Intervalle de confiance 95 % (Wilson) : [${(low * 100).toFixed(1)} % ; ${(high * 100).toFixed(1)} %]`}>
      <div
        className="absolute inset-y-0 bg-foreground/15"
        style={{ left: `${low * 100}%`, width: `${Math.max(0.5, (high - low) * 100)}%` }}
      />
      <div
        className={cn("absolute inset-y-0 w-0.5", barClass)}
        style={{ left: `calc(${rate * 100}% - 1px)` }}
      />
    </div>
  );
}

export function VerdictBadge({ verdict }: { verdict: string | null | undefined }) {
  if (!verdict) {
    return <span className="mono text-[10px] text-muted-foreground">non classé</span>;
  }
  const map: Record<string, { label: string; cls: string }> = {
    affirmed: { label: "CONFIRMÉ", cls: "text-pos border-pos bg-pos-subtle" },
    reversed: { label: "INFIRMÉ", cls: "text-neg border-neg bg-neg-subtle" },
    reversed_vacated: { label: "INFIRMÉ/ANNULÉ", cls: "text-neg border-neg bg-neg-subtle" },
    modified: { label: "MODIFIÉ", cls: "text-mix border-mix bg-mix-subtle" },
    vacated: { label: "ANNULÉ", cls: "text-mix border-mix bg-mix-subtle" },
    dismissed: { label: "REJETÉ", cls: "text-mix border-mix bg-mix-subtle" },
    remitted: { label: "RENVOI", cls: "text-mix border-mix bg-mix-subtle" },
  };
  const m = map[verdict] ?? { label: verdict.toUpperCase(), cls: "text-muted-foreground border-border bg-secondary" };
  return (
    <span className={cn("mono text-[10px] font-medium border rounded-sm px-1.5 py-0.5 whitespace-nowrap", m.cls)}>
      {m.label}
    </span>
  );
}

export function ZBadge({ z }: { z: number }) {
  const significant = Math.abs(z) >= 2;
  const cls = !significant
    ? "text-muted-foreground border-border"
    : z > 0
      ? "text-pos border-pos bg-pos-subtle"
      : "text-neg border-neg bg-neg-subtle";
  return (
    <span className={cn("mono text-[11px] font-medium border rounded-sm px-1.5 py-0.5", cls)} title="Score z par rapport à la base du corpus (|z| ≥ 2 = écart significatif)">
      {fmtSigned(z)}
    </span>
  );
}

export function MethodNote({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] leading-[1.75] text-muted-foreground border-l-2 border-border pl-3.5 mt-4 max-w-4xl">
      <span className="label-caps text-muted-foreground/90">Méthode · </span>
      {children}
    </p>
  );
}
