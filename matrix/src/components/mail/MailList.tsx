"use client";

/**
 * INFINITUM — colonne de liste des dossiers (anatomie email, données réelles).
 */
import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { VerdictBadge } from "@/components/analytics/shared";
import type { MailItem, MailboxPage } from "@/lib/matrix/mailbox";
import { DeptChip, MailAvatar, StarToggle, fmtMailDate } from "./mail-shared";

export function MailList({
  page,
  loading,
  selectedId,
  stars,
  onToggleStar,
  onSelect,
  onPage,
}: {
  page: MailboxPage | null;
  loading: boolean;
  selectedId: string | null;
  stars: Set<string>;
  onToggleStar: (id: string) => void;
  onSelect: (item: MailItem) => void;
  onPage: (p: number) => void;
}) {
  const rangeStart = page ? (page.page - 1) * page.pageSize + 1 : 0;
  const rangeEnd = page ? Math.min(page.page * page.pageSize, page.total) : 0;

  return (
    <div className="flex h-full min-h-0 flex-col">
      {loading && page === null ? (
        <div className="flex flex-1 items-center justify-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Interrogation de l'index réel…
        </div>
      ) : page?.empty ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 px-6 text-center">
          <p className="font-serif text-base">Aucun dossier ne correspond</p>
          <p className="text-xs leading-relaxed text-muted-foreground">
            L'index ne contient que des décisions réelles — il ne fabrique aucun
            résultat pour combler une recherche vide. Modifiez la requête ou le libellé.
          </p>
        </div>
      ) : (
        <ul className="min-h-0 flex-1 overflow-y-auto" role="listbox" aria-label="Dossiers">
          {page?.items.map((item) => {
            const selected = item.id === selectedId;
            return (
              <li key={item.id} role="option" aria-selected={selected}>
                <div
                  className={cn(
                    "flex cursor-pointer items-start gap-3 border-b border-border/60 px-3 py-3 transition-colors md:px-4",
                    selected ? "bg-accent" : "hover:bg-secondary/60",
                  )}
                  onClick={() => onSelect(item)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelect(item);
                    }
                  }}
                  tabIndex={0}
                  role="button"
                  aria-label={`Ouvrir ${item.subject}`}
                >
                  <StarToggle
                    starred={stars.has(item.id)}
                    onToggle={() => onToggleStar(item.id)}
                    label={item.subject}
                  />
                  <MailAvatar
                    initials={item.avatar}
                    department={item.department}
                    kind={item.kind}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className={cn(
                          "truncate text-sm",
                          item.kind === "digest" ? "font-medium text-primary" : "font-medium",
                        )}
                        title={item.fromDetail}
                      >
                        {item.fromName}
                      </span>
                      <span className="mono shrink-0 self-center rounded-sm bg-secondary/60 px-1.5 py-0.5 text-[11px] whitespace-nowrap text-muted-foreground">
                        {fmtMailDate(item.date)}
                      </span>
                    </div>
                    <div className="mt-0.5 flex min-w-0 items-center gap-1.5">
                      <span
                        className={cn(
                          "truncate text-sm",
                          item.kind === "digest" ? "text-foreground" : "text-foreground/90",
                        )}
                      >
                        {item.subject}
                      </span>
                      {item.kind === "dossier" && <VerdictBadge verdict={item.disposition} />}
                    </div>
                    <div className="mt-0.5 flex items-center gap-1.5">
                      {item.kind === "dossier" && item.department && (
                        <span className="shrink-0">
                          <DeptChip department={item.department} />
                        </span>
                      )}
                      {item.flagged && (
                        <span
                          className="mono shrink-0 text-[10px] font-medium text-mix"
                          title="Président ou auteur en écart statistique significatif"
                        >
                          ⚑ signal
                        </span>
                      )}
                      <span className="truncate text-xs text-muted-foreground">{item.snippet}</span>
                    </div>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {page && !page.empty && (
        <div className="flex shrink-0 items-center justify-between gap-2 border-t bg-card/60 px-3 py-2 md:px-4">
          <span className="mono text-[11px] text-muted-foreground">
            {rangeStart.toLocaleString("fr-FR")}–{rangeEnd.toLocaleString("fr-FR")} sur{" "}
            {page.total.toLocaleString("fr-FR")}
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              aria-label="Page précédente"
              disabled={page.page <= 1 || loading}
              onClick={() => onPage(page.page - 1)}
              className="rounded-sm border p-1 transition-colors hover:bg-secondary disabled:opacity-30"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="mono text-[11px] text-muted-foreground">
              {page.page} / {page.pages}
            </span>
            <button
              type="button"
              aria-label="Page suivante"
              disabled={page.page >= page.pages || loading}
              onClick={() => onPage(page.page + 1)}
              className="rounded-sm border p-1 transition-colors hover:bg-secondary disabled:opacity-30"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
