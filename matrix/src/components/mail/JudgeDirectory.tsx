"use client";

/**
 * INFINITUM — Annuaire des juges (« contacts » de la boîte).
 * Métriques réelles par juge ; cliquer un contact filtre la boîte sur
 * ses décisions.
 */
import { useEffect, useState } from "react";
import { Loader2, Search, Users } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { ZBadge, fmtPct, deptColor, DEPT_LABELS } from "@/components/analytics/shared";
import type { JudgeCard } from "@/lib/matrix/mailbox";
import { initialsOf } from "./mail-shared";

export function JudgeDirectory({
  open,
  onOpenChange,
  onPick,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onPick: (name: string) => void;
}) {
  const [q, setQ] = useState("");
  const [judges, setJudges] = useState<JudgeCard[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `/api/mail/judges?q=${encodeURIComponent(q)}`,
          { signal: controller.signal },
        );
        const json = await res.json();
        if (!res.ok) throw new Error(json?.message ?? `HTTP ${res.status}`);
        setJudges(json.judges as JudgeCard[]);
        setLoading(false);
      } catch (e) {
        if (controller.signal.aborted) return;
        setError((e as Error).message);
        setLoading(false);
      }
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [open, q]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] max-w-xl overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 font-serif">
            <Users className="h-4 w-4" /> Contacts — juges de la Division d'appel
          </DialogTitle>
          <DialogDescription>
            {judges
              ? `${judges.length.toLocaleString("fr-FR")} magistrats identifiés par leurs noms normalisés depuis les preuves officielles. Cliquez pour ouvrir leurs décisions dans la boîte.`
              : "Chargement de l'annuaire réel…"}
          </DialogDescription>
        </DialogHeader>

        <div className="relative">
          <Search className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Rechercher un juge…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="pl-9"
            aria-label="Rechercher un juge"
          />
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          {loading && judges === null ? (
            <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Interrogation de l'annuaire réel…
            </div>
          ) : error ? (
            <p className="px-2 py-10 text-center text-sm text-neg">{error}</p>
          ) : judges && judges.length === 0 ? (
            <p className="px-2 py-10 text-center text-sm text-muted-foreground">
              Aucun juge ne correspond — l'annuaire ne devine aucun nom.
            </p>
          ) : (
            <ul className="space-y-1">
              {judges?.map((j) => {
                const color = deptColor(j.dominantDepartment);
                return (
                  <li key={j.name}>
                    <button
                      type="button"
                      onClick={() => {
                        onPick(j.name);
                        onOpenChange(false);
                      }}
                      className="flex w-full items-center gap-3 rounded-sm border border-transparent px-2 py-2 text-left transition-colors hover:border-border hover:bg-secondary/50"
                      aria-label={`Ouvrir les décisions de ${j.name}`}
                    >
                      <span
                        className="mono flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-[11px] font-medium"
                        style={{
                          color,
                          borderColor: `color-mix(in oklab, ${color} 35%, transparent)`,
                          backgroundColor: `color-mix(in oklab, ${color} 9%, transparent)`,
                        }}
                      >
                        {initialsOf(j.name)}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="flex flex-wrap items-center gap-1.5">
                          <span className="text-sm font-medium">{j.name}, J.</span>
                          <span className="mono text-[10px] text-muted-foreground">
                            {DEPT_LABELS[j.dominantDepartment] ?? j.dominantDepartment}
                          </span>
                          {(j.deviatesUp || j.deviatesDown) && (
                            <span className="mono rounded-sm border border-mix/40 bg-mix-subtle px-1 py-0.5 text-[9px] font-medium text-mix">
                              signal
                            </span>
                          )}
                        </span>
                        <span className="mono mt-0.5 block text-[11px] text-muted-foreground">
                          {j.nBinary} décisions binaires · {fmtPct(j.rate)} confirmations ·{" "}
                          {j.authoredTotal} écrits
                          {j.yearSpan ? ` · ${j.yearSpan[0]}–${j.yearSpan[1]}` : ""}
                        </span>
                      </span>
                      <span className="shrink-0">
                        {j.nBinary > 0 ? <ZBadge z={j.z} /> : null}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <p className="border-t pt-2 text-[10px] leading-relaxed text-muted-foreground">
          Annuaire public : les identités résiduelles d'artefacts de signature (ex.
          « Memorandum Order … ») en sont exclues pour la lisibilité — elles restent
          préservées dans l'index scientifique. Métriques calculées uniquement sur les
          décisions réelles où chaque juge a siégé.
        </p>
      </DialogContent>
    </Dialog>
  );
}
