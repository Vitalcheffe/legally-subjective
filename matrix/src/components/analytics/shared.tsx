"use client";

/**
 * Behavioral Matrix — shared terminal primitives.
 * Data states are honest: loading, error, empty ("EN ATTENTE DE FLUX DE
 * DONNÉES RÉELLES") — never a fabricated placeholder value.
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

export const DEPT_COLORS: Record<string, string> = {
  "1st": "#e879f9",
  "2nd": "#fbbf24",
  "3rd": "#a3e635",
  "4th": "#fb923c",
  unknown: "#71717a",
};
export function deptColor(dept: string | null | undefined): string {
  return DEPT_COLORS[dept ?? "unknown"] ?? "#71717a";
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
    <section className={cn("panel rounded-sm flex flex-col min-h-0", className)} aria-label={title}>
      <header className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-border/70 px-4 py-3">
        <span className="mono text-[11px] text-primary/90 tracking-widest border border-primary/30 rounded-sm px-1.5 py-0.5 bg-primary/5">
          {code}
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="label-caps text-foreground/90 truncate">{title}</h2>
          {subtitle ? <p className="text-[11px] text-muted-foreground truncate">{subtitle}</p> : null}
        </div>
        {actions}
        {source ? (
          <span className="label-caps text-muted-foreground/70 hidden lg:inline">
            SRC · {source}
          </span>
        ) : null}
      </header>
      <div className="p-4 min-h-0 flex-1">{children}</div>
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
  tone?: "neutral" | "emerald" | "red" | "amber";
  className?: string;
}) {
  const toneClass =
    tone === "emerald" ? "text-emerald-400 glow-emerald"
    : tone === "red" ? "text-red-400 glow-red"
    : tone === "amber" ? "text-amber-400 glow-amber"
    : "text-foreground";
  return (
    <div className={cn("panel rounded-sm px-3 py-2 min-w-0", className)}>
      <div className="label-caps text-muted-foreground truncate">{label}</div>
      <div className={cn("mono text-lg leading-tight truncate", toneClass)}>{value}</div>
      {sub ? <div className="mono text-[10px] text-muted-foreground truncate">{sub}</div> : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Honest states
// ---------------------------------------------------------------------------
export function TerminalLoader({ label = "INTERROGATION DE L'INDEX RÉEL" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-14 text-center" role="status">
      <Loader2 className="h-5 w-5 animate-spin text-primary" aria-hidden />
      <p className="label-caps text-muted-foreground">
        {label}
        <span className="blink-cursor text-primary">▌</span>
      </p>
    </div>
  );
}

export function EmptyState({
  title = "EN ATTENTE DE FLUX DE DONNÉES RÉELLES",
  message,
  hint,
}: {
  title?: string;
  message?: string;
  hint?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 border border-dashed border-border rounded-sm py-14 px-6 text-center max-w-2xl mx-auto">
      <Database className="h-6 w-6 text-muted-foreground" aria-hidden />
      <p className="label-caps text-amber-400">{title}</p>
      {message ? (
        <p className="text-xs text-muted-foreground leading-relaxed">{message}</p>
      ) : null}
      {hint ? <p className="mono text-[10px] text-muted-foreground/70">{hint}</p> : null}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 border border-destructive/40 bg-destructive/5 rounded-sm py-12 px-6 text-center max-w-2xl mx-auto" role="alert">
      <AlertTriangle className="h-6 w-6 text-red-400" aria-hidden />
      <p className="label-caps text-red-400">ERREUR SYSTÈME — FLUX INTERROMPU</p>
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
      className="h-7 px-2 label-caps gap-1.5 border-border/70"
      aria-label="Recharger les données réelles"
    >
      <RefreshCw className="h-3 w-3" aria-hidden />
      RAFRAÎCHIR
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
  tone = "emerald",
}: {
  rate: number;
  low: number;
  high: number;
  tone?: "emerald" | "red" | "amber";
}) {
  const color =
    tone === "emerald" ? "bg-emerald-400/80"
    : tone === "red" ? "bg-red-400/80"
    : "bg-amber-400/80";
  return (
    <div className="relative h-2 w-full min-w-16 bg-secondary rounded-sm overflow-hidden" title={`IC95 Wilson : [${(low * 100).toFixed(1)}% ; ${(high * 100).toFixed(1)}%]`}>
      <div
        className="absolute inset-y-0 bg-foreground/20"
        style={{ left: `${low * 100}%`, width: `${Math.max(0.5, (high - low) * 100)}%` }}
      />
      <div
        className={cn("absolute inset-y-0 w-0.5", color)}
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
    affirmed: { label: "CONFIRMÉ", cls: "text-emerald-400 border-emerald-400/40 bg-emerald-400/10" },
    reversed: { label: "INFIRMÉ", cls: "text-red-400 border-red-400/40 bg-red-400/10" },
    reversed_vacated: { label: "INFIRMÉ/ANNULÉ", cls: "text-red-400 border-red-400/40 bg-red-400/10" },
    modified: { label: "MODIFIÉ", cls: "text-amber-400 border-amber-400/40 bg-amber-400/10" },
    vacated: { label: "ANNULÉ", cls: "text-amber-400 border-amber-400/40 bg-amber-400/10" },
    dismissed: { label: "REJETÉ", cls: "text-amber-400 border-amber-400/40 bg-amber-400/10" },
    remitted: { label: "RENVOI", cls: "text-amber-400 border-amber-400/40 bg-amber-400/10" },
  };
  const m = map[verdict] ?? { label: verdict.toUpperCase(), cls: "text-muted-foreground border-border bg-secondary" };
  return (
    <span className={cn("mono text-[10px] border rounded-sm px-1.5 py-0.5 whitespace-nowrap", m.cls)}>
      {m.label}
    </span>
  );
}

export function ZBadge({ z }: { z: number }) {
  const significant = Math.abs(z) >= 2;
  const cls = !significant
    ? "text-muted-foreground border-border"
    : z > 0
      ? "text-emerald-400 border-emerald-400/40 bg-emerald-400/10"
      : "text-red-400 border-red-400/40 bg-red-400/10";
  return (
    <span className={cn("mono text-[11px] border rounded-sm px-1.5 py-0.5", cls)} title="Score z vs base du corpus (|z| ≥ 2 = écart significatif)">
      {fmtSigned(z)}
    </span>
  );
}

export function MethodNote({ children }: { children: React.ReactNode }) {
  return (
    <p className="mono text-[10px] leading-relaxed text-muted-foreground/80 border-l-2 border-border pl-3 mt-4">
      <span className="text-muted-foreground">MÉTHODE · </span>
      {children}
    </p>
  );
}
