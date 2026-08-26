"use client";

/**
 * INFINITUM — volet de lecture : le dossier (ou rapport système) ouvert
 * comme un email. Chaque bloc provient de l'API réelle ; les absences
 * sont dites, jamais comblées.
 */
import { useEffect, useState } from "react";
import {
  ArrowLeft,
  BookOpen,
  ExternalLink,
  Loader2,
  Scale,
  ShieldAlert,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { VerdictBadge, ZBadge, fmtPct } from "@/components/analytics/shared";
import type { DigestDetail, DossierDetail, MailItem } from "@/lib/matrix/mailbox";
import {
  AUTHOR_METHOD_LABELS,
  DeptChip,
  MailAvatar,
  SignalBadge,
  fmtFullDate,
} from "./mail-shared";

type Detail = DossierDetail | DigestDetail;

function Section({
  title,
  children,
  hint,
}: {
  title: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <section className="border-t border-border/60 px-4 py-5 md:px-6">
      <h3
        className="mono mb-3 text-[10px] font-medium tracking-[0.14em] text-muted-foreground uppercase"
        title={hint}
      >
        {title}
      </h3>
      {children}
    </section>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-sm border bg-card px-3 py-2">
      <div className="mono text-sm font-medium">{value}</div>
      <div className="mt-0.5 text-[11px] leading-tight text-muted-foreground">{label}</div>
    </div>
  );
}

function RunCard({ run }: { run: DossierDetail["runs"][number] }) {
  return (
    <div className="rounded-sm border bg-card px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="mono text-[11px] text-muted-foreground">
          Délibération #{run.id} · {fmtFullDate(run.createdAt)}
        </span>
        <VerdictBadge verdict={run.aiVerdict} />
        {run.aiConfidence !== null && (
          <span className="mono text-[11px] text-muted-foreground">
            confiance {fmtPct(run.aiConfidence, 0)}
          </span>
        )}
        {run.agreement !== null && (
          <span
            className={cn(
              "mono rounded-sm border px-1.5 py-0.5 text-[10px] font-medium",
              run.agreement
                ? "border-pos/40 bg-pos-subtle text-pos"
                : "border-neg/40 bg-neg-subtle text-neg",
            )}
          >
            {run.agreement ? "ACCORD AVEC LA COUR" : "DIVERGENCE AVEC LA COUR"}
          </span>
        )}
      </div>
      {run.status !== "ok" && run.error && (
        <p className="mono mt-2 text-[11px] leading-relaxed text-neg">{run.error}</p>
      )}
      {(run.prosecutorOutput || run.defenderOutput || run.judgeOutput) && (
        <details className="mt-2">
          <summary className="cursor-pointer text-[11px] text-muted-foreground hover:text-foreground">
            Journal de délibération (verbatim, tel qu'archivé)
          </summary>
          <div className="mt-2 space-y-2">
            {(
              [
                ["Procureur", run.prosecutorOutput],
                ["Défense", run.defenderOutput],
                ["Juge-IA", run.judgeOutput],
              ] as const
            ).map(([role, raw]) =>
              raw ? (
                <pre
                  key={role}
                  className="mono max-h-64 overflow-y-auto rounded-sm border bg-secondary/40 p-3 text-[11px] leading-relaxed whitespace-pre-wrap"
                >
                  {`[${role}]\n${raw}`}
                </pre>
              ) : null,
            )}
          </div>
        </details>
      )}
    </div>
  );
}

function DossierBody({ d }: { d: DossierDetail }) {
  const author = d.authorMethod ? AUTHOR_METHOD_LABELS[d.authorMethod] : null;
  return (
    <div>
      <Section title="Issue de l'appel">
        <div className="flex flex-wrap items-center gap-3">
          <span className="font-serif text-2xl">
            {d.dispositionBinary === "affirmed"
              ? "Confirmé"
              : d.dispositionBinary === "reversed_vacated"
                ? "Infirmé / annulé"
                : "Issue non classée"}
          </span>
          <VerdictBadge verdict={d.dispositionBinary} />
          {d.dispositionPrimary && (
            <span className="mono rounded-sm border bg-secondary/50 px-2 py-1 text-[11px] text-muted-foreground">
              disposition source : {d.dispositionPrimary}
            </span>
          )}
        </div>
        {!d.binaryEligible && (
          <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
            Cette affaire n'est pas classable en binaire (issue mixte, renvoi, rejet ou
            disposition non standard) — l'index la conserve sans la forcer dans une
            catégorie. Elle est exclue des taux de confirmation.
          </p>
        )}
      </Section>

      <Section title="Recital officiel des faits" hint="Extrait verbatim de l'opinion source">
        {d.factsExcerpt ? (
          <blockquote className="border-l-2 border-primary/40 pl-4 font-serif text-[15px] leading-relaxed text-foreground/90">
            {d.factsExcerpt}
          </blockquote>
        ) : (
          <p className="text-sm leading-relaxed text-muted-foreground">
            Aucun recital extrait dans la source officielle — l'interface ne le reconstitue
            pas. Ouvrez l'opinion intégrale via la pièce jointe « Source officielle ».
          </p>
        )}
      </Section>

      {d.charge && (
        <Section title="Chef d'accusation">
          <p className="text-sm leading-relaxed">{d.charge}</p>
        </Section>
      )}

      <Section title="Attribution de la plume (règle R7)" hint="Méthode d'attribution d'auteur appliquée au texte officiel">
        <div className="flex flex-wrap items-center gap-2">
          {author ? (
            <span
              className="mono rounded-sm border bg-secondary/50 px-2 py-1 text-[11px]"
              title={author.hint}
            >
              {author.label}
            </span>
          ) : (
            <span className="mono rounded-sm border bg-secondary/50 px-2 py-1 text-[11px] text-muted-foreground">
              attribution non dérivable
            </span>
          )}
          {d.authorJudgeName && (
            <span className="text-sm">
              Plume : <span className="font-medium">{d.authorJudgeName}, J.</span>
            </span>
          )}
          {d.authorRaw && (
            <span className="mono text-[11px] text-muted-foreground">
              signature source : « {d.authorRaw} »
            </span>
          )}
        </div>
      </Section>

      <Section
        title="Panel et métriques réelles"
        hint="Taux de confirmation binaires calculés sur les décisions où ce juge a siégé — rien d'extrapolé"
      >
        {d.panel.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Panel non identifiable dans la preuve officielle — aucun siège inventé.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left">
                  <th className="mono py-1.5 pr-3 text-[10px] font-medium tracking-wider text-muted-foreground uppercase">
                    Juge
                  </th>
                  <th className="mono py-1.5 pr-3 text-[10px] font-medium tracking-wider text-muted-foreground uppercase">
                    Rôle
                  </th>
                  <th className="mono py-1.5 pr-3 text-right text-[10px] font-medium tracking-wider text-muted-foreground uppercase">
                    n binaires
                  </th>
                  <th className="mono py-1.5 pr-3 text-right text-[10px] font-medium tracking-wider text-muted-foreground uppercase">
                    Taux confirmation
                  </th>
                  <th className="mono py-1.5 pr-3 text-right text-[10px] font-medium tracking-wider text-muted-foreground uppercase">
                    z
                  </th>
                  <th className="mono py-1.5 text-right text-[10px] font-medium tracking-wider text-muted-foreground uppercase">
                    Écrits
                  </th>
                </tr>
              </thead>
              <tbody>
                {d.panel.map((p) => (
                  <tr key={p.name} className="border-b border-border/40">
                    <td className="py-2 pr-3 font-medium whitespace-nowrap">
                      {p.name}, J.{" "}
                      {(p.deviatesUp || p.deviatesDown) && <SignalBadge />}
                    </td>
                    <td className="mono py-2 pr-3 text-xs text-muted-foreground">
                      {p.role === "presiding" ? "président" : "panel"}
                    </td>
                    <td className="mono py-2 pr-3 text-right text-muted-foreground">
                      {p.nBinary}
                    </td>
                    <td className="mono py-2 pr-3 text-right">
                      {p.nBinary > 0 ? fmtPct(p.rate) : "—"}
                    </td>
                    <td className="py-2 pr-3 text-right">
                      {p.nBinary > 0 ? <ZBadge z={p.z} /> : <span className="mono text-xs">—</span>}
                    </td>
                    <td className="mono py-2 text-right text-muted-foreground">
                      {p.authoredTotal || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
              n binaires = décisions où le juge a siégé et qui étaient classables ; taux et
              z calculés sur ces décisions réelles. « Écrits » = opinions dont ce juge est
              l'auteur attribué (R7). |z| ≥ 2 avec n ≥ 30 = écart significatif à la base du
              corpus.
            </p>
          </div>
        )}
      </Section>

      {d.authorities.length > 0 && (
        <Section title="Autorités citées dans cette opinion">
          <div className="flex flex-wrap gap-1.5">
            {d.authorities.map((a) => (
              <span
                key={a.target}
                className="mono inline-flex items-center gap-1.5 rounded-sm border bg-card px-2 py-1 text-[11px]"
              >
                {a.kind === "statute" ? (
                  <BookOpen className="h-3 w-3 text-muted-foreground" />
                ) : (
                  <Scale className="h-3 w-3 text-muted-foreground" />
                )}
                {a.target}
                {a.count > 1 && (
                  <span className="text-muted-foreground">×{a.count}</span>
                )}
              </span>
            ))}
          </div>
        </Section>
      )}

      <Section
        title="Délibérations multi-agents archivées"
        hint="Sessions LLM réelles, verbatim, journalisées avec leurs échecs"
      >
        {d.runs.length === 0 ? (
          <p className="text-sm leading-relaxed text-muted-foreground">
            Aucune délibération archivée pour cette affaire. L'index n'en simule aucune —
            seules des sessions réellement exécutées y figurent.
          </p>
        ) : (
          <div className="space-y-2">
            {d.runs.map((r) => (
              <RunCard key={r.id} run={r} />
            ))}
          </div>
        )}
      </Section>

      <Section title="Stylométrie du texte source">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          <MiniStat label="caractères" value={d.stylometry.textChars.toLocaleString("fr-FR")} />
          <MiniStat label="phrases" value={d.stylometry.sentenceCount.toLocaleString("fr-FR")} />
          <MiniStat label="mots (approx.)" value={d.stylometry.tokenCount.toLocaleString("fr-FR")} />
          <MiniStat label="lexèmes punitifs" value={String(d.stylometry.punitiveHits)} />
          <MiniStat label="lexèmes réhabilitatifs" value={String(d.stylometry.rehabHits)} />
          <MiniStat label="citations comptées" value={String(d.stylometry.citationMentions)} />
        </div>
      </Section>
    </div>
  );
}

function DigestBody({ d }: { d: DigestDetail }) {
  return (
    <div>
      {d.sections.map((s, i) => (
        <Section key={i} title={s.title}>
          <div className="space-y-4">
            {s.paragraphs.map((p, j) => (
              <p key={j} className="text-sm leading-7 text-foreground/90">
                {p}
              </p>
            ))}
          </div>
          {s.table && (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    {s.table.headers.map((h) => (
                      <th
                        key={h}
                        className="mono py-1.5 pr-4 text-[10px] font-medium tracking-wider text-muted-foreground uppercase"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {s.table.rows.map((row, ri) => (
                    <tr key={ri} className="border-b border-border/40">
                      {row.map((cell, ci) => (
                        <td
                          key={ci}
                          className={cn(
                            "py-2 pr-4",
                            ci === 0 ? "font-medium" : "mono",
                            ci > 0 && "text-foreground/80",
                          )}
                        >
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Section>
      ))}
    </div>
  );
}

export function MailDetail({
  item,
  onBack,
}: {
  item: MailItem | null;
  onBack?: () => void;
}) {
  const [detail, setDetail] = useState<Detail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!item) {
      setDetail(null);
      setError(null);
      return;
    }
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/mail/dossier/${encodeURIComponent(item.id)}`, {
          signal: controller.signal,
        });
        const json = await res.json();
        if (!res.ok) throw new Error(json?.message ?? `HTTP ${res.status}`);
        setDetail(json as Detail);
        setLoading(false);
      } catch (e) {
        if (controller.signal.aborted) return;
        setError((e as Error).message);
        setLoading(false);
      }
    }
    load();
    return () => controller.abort();
  }, [item]);

  if (!item) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 px-8 text-center">
        <div className="mono text-[11px] tracking-[0.3em] text-muted-foreground uppercase">
          INFINITUM
        </div>
        <p className="font-serif text-lg">Sélectionnez un dossier pour le lire</p>
        <p className="max-w-sm text-xs leading-relaxed text-muted-foreground">
          Chaque « email » est une décision criminelle réelle de la Division d'appel de
          New York (2015–2023), avec son panel, ses métriques et ses sources.
        </p>
      </div>
    );
  }

  const isDigest = item.kind === "digest";
  const d = detail && detail.kind === "dossier" ? detail : null;
  const g = detail && detail.kind === "digest" ? detail : null;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="shrink-0 border-b bg-card/70 px-4 py-4 md:px-6">
        <div className="flex items-start gap-4">
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              aria-label="Retour à la liste"
              className="mt-1 rounded-sm border p-1.5 transition-colors hover:bg-secondary md:hidden"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
          )}
          <MailAvatar
            initials={item.avatar}
            department={item.department}
            kind={item.kind}
            size="lg"
          />
          <div className="min-w-0 flex-1">
            <h2 className="font-serif text-xl leading-snug break-words md:text-2xl">
              {isDigest && g ? g.subject : item.subject}
            </h2>
            <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
              {item.kind === "dossier" && <VerdictBadge verdict={item.disposition} />}
              {item.department && <DeptChip department={item.department} />}
              {item.flagged && <SignalBadge />}
              {d && d.runs.length > 0 && (
                <span className="mono rounded-sm border border-primary/30 bg-accent px-1.5 py-0.5 text-[10px] font-medium text-accent-foreground">
                  délibérée ×{d.runs.length}
                </span>
              )}
            </div>
            <div className="mt-3 space-y-1 text-[13px]">
              <p className="text-muted-foreground">
                <span className="mono mr-2 text-[10px] tracking-wider uppercase">De</span>
                <span className="text-foreground">{item.fromDetail}</span>
              </p>
              <p className="text-muted-foreground">
                <span className="mono mr-2 text-[10px] tracking-wider uppercase">À</span>
                {isDigest
                  ? "Lecteurs du rapport d'accueil — vous"
                  : "Parties à la procédure d'appel"}
              </p>
              <p className="text-muted-foreground">
                <span className="mono mr-2 text-[10px] tracking-wider uppercase">Date</span>
                {fmtFullDate(item.date)}
              </p>
            </div>
            {d && (d.docketNumber || d.citation || d.sourceUrl) && (
              <div className="mt-3 flex flex-wrap items-center gap-1.5">
                {d.sourceUrl && (
                  <a
                    href={d.sourceUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mono inline-flex items-center gap-1.5 rounded-sm border border-primary/30 bg-accent px-2 py-1 text-[11px] font-medium text-accent-foreground transition-colors hover:bg-accent/70"
                  >
                    <ExternalLink className="h-3 w-3" /> Opinion officielle (CourtListener)
                  </a>
                )}
                {d.docketNumber && (
                  <span className="mono rounded-sm border bg-card px-2 py-1 text-[11px] text-muted-foreground">
                    docket {d.docketNumber}
                  </span>
                )}
                {d.citation && (
                  <span className="mono rounded-sm border bg-card px-2 py-1 text-[11px] text-muted-foreground">
                    {d.citation}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Ouverture du dossier réel…
          </div>
        ) : error ? (
          <div className="flex flex-col items-center gap-3 px-6 py-16 text-center">
            <ShieldAlert className="h-6 w-6 text-neg" />
            <p className="max-w-md text-sm leading-relaxed text-muted-foreground">{error}</p>
          </div>
        ) : d ? (
          <DossierBody d={d} />
        ) : g ? (
          <DigestBody d={g} />
        ) : null}

        {d && (
          <footer className="border-t px-4 py-4 md:px-6">
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              Dossier {d.caseId} · source : opinion officielle de la Division d'appel de
              l'État de New York, collectée et vérifiée document par document (nycourts.gov
              via CourtListener). Aucun champ de cette fiche n'est extrapolé — ce que la
              preuve ne porte pas, la fiche ne l'affiche pas.
            </p>
          </footer>
        )}
      </div>
    </div>
  );
}
