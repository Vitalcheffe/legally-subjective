"use client";

/**
 * INFINITUM — « La Boîte de la Cour » : primitives partagées de
 * l'interface publique (système jmail). Thème Codex clair institutionnel.
 * Aucune valeur fabriquée : tous les affichages proviennent de l'API réelle.
 */
import { Star } from "lucide-react";
import { cn } from "@/lib/utils";
import { DEPT_LABELS, deptColor } from "@/components/analytics/shared";

export function initialsOf(name: string | null | undefined): string {
  if (!name) return "··";
  const parts = name.replace(/[^A-Za-zÀ-ÿ' -]/g, "").trim().split(/[\s-]+/).filter(Boolean);
  if (parts.length === 0) return "··";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function MailAvatar({
  initials,
  department,
  size = "md",
  kind = "dossier",
}: {
  initials: string;
  department?: string | null;
  size?: "md" | "lg";
  kind?: "dossier" | "digest";
}) {
  const color = kind === "digest" ? "var(--primary)" : deptColor(department);
  return (
    <div
      aria-hidden
      className={cn(
        "mono flex shrink-0 items-center justify-center rounded-full border font-medium select-none",
        size === "md" ? "h-9 w-9 text-[11px]" : "h-12 w-12 text-sm",
      )}
      style={{
        color,
        borderColor: `color-mix(in oklab, ${color} 35%, transparent)`,
        backgroundColor: `color-mix(in oklab, ${color} 9%, transparent)`,
      }}
    >
      {initials}
    </div>
  );
}

export function DeptChip({ department }: { department: string | null | undefined }) {
  if (!department) return null;
  const color = deptColor(department);
  return (
    <span
      className="mono inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 text-[10px] whitespace-nowrap"
      style={{
        color,
        borderColor: `color-mix(in oklab, ${color} 35%, transparent)`,
        backgroundColor: `color-mix(in oklab, ${color} 7%, transparent)`,
      }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
      {DEPT_LABELS[department] ?? department}
    </span>
  );
}

export function SignalBadge() {
  return (
    <span
      className="mono inline-flex items-center gap-1 rounded-sm border border-mix/40 bg-mix-subtle px-1.5 py-0.5 text-[10px] font-medium text-mix"
      title="Président du panel ou auteur en écart statistique significatif (|z| ≥ 2, n ≥ 30) par rapport à la base du corpus"
    >
      signal
    </span>
  );
}

export function StarToggle({
  starred,
  onToggle,
  label,
}: {
  starred: boolean;
  onToggle: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      aria-label={starred ? `Ne plus suivre ${label}` : `Suivre ${label}`}
      aria-pressed={starred}
      onClick={(e) => {
        e.stopPropagation();
        onToggle();
      }}
      className="mt-0.5 shrink-0 rounded-sm p-0.5 transition-colors hover:bg-secondary"
    >
      <Star
        className={cn("h-4 w-4", starred ? "fill-mix text-mix" : "text-muted-foreground/50")}
      />
    </button>
  );
}

export function fmtMailDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const now = new Date();
  const sameYear = d.getFullYear() === now.getFullYear();
  return d.toLocaleDateString("fr-FR", sameYear ? { day: "numeric", month: "short" } : { month: "short", year: "numeric" });
}

export function fmtFullDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "date inconnue";
  return d.toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
}

export const AUTHOR_METHOD_LABELS: Record<string, { label: string; hint: string }> = {
  explicit: {
    label: "Opinion signée",
    hint: "Signature d'auteur explicite dans le texte officiel (« NOM, J. »)",
  },
  "presumed-presiding": {
    label: "Mémo du président",
    hint: "Mémo non signé — auteur présumé : juge président, convention NY Law Reporting Bureau",
  },
  "per-curiam": {
    label: "Per curiam",
    hint: "Opinion institutionnelle sans auteur individuel",
  },
  unresolved: {
    label: "Attribution non résolue",
    hint: "Aucune attribution dérivable du document source — l'index ne devine pas",
  },
};

export const VERDICT_LABELS: Record<string, string> = {
  affirmed: "CONFIRMER",
  reversed: "INFIRMER",
};
