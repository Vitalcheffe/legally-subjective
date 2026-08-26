"use client";

/**
 * MODULE 09 — BOUCLIER DE COMPARAISON IA NEUTRE.
 * Side-by-side: the REAL human disposition of a real case vs the verdict of
 * a multi-agent LLM session (Prosecutor / Defender / AI-Judge) bound to the
 * real case recital via z-ai-web-dev-sdk. Verbatim outputs are stored and
 * displayed — no fabricated agent reasoning, ever.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Accordion, AccordionContent, AccordionItem, AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Gavel, ScrollText, ShieldCheck, Swords } from "lucide-react";
import {
  useMatrixData, ModulePanel, ModuleBody, ReloadButton, fmtPct,
  VerdictBadge, MethodNote, deptColor, DEPT_LABELS, TerminalLoader, fmtSigned,
} from "./shared";

interface CaseRow {
  caseId: string; caseName: string; citation: string | null; charge: string | null;
  dateFiled: string; department: string; dispositionPrimary: string | null;
  dispositionBinary: string | null; binaryEligible: boolean; factsExcerpt: string | null;
}
interface CasesPayload {
  empty: boolean; total: number; cases: CaseRow[]; message?: string;
}
interface AgentVerdict {
  role: string; key_arguments: string[]; verdict: "affirmed" | "reversed";
  confidence: number; summary: string;
}
interface SessionPayload {
  runId: number; status: "ok" | "error"; error?: string;
  case: {
    caseId: string; caseName: string; charge: string | null; department: string;
    dateFiled: string; factsExcerpt: string | null; humanDisposition: string | null;
    humanBinary: string | null; binaryEligible: boolean;
  };
  prosecutor?: AgentVerdict; defender?: AgentVerdict; judge?: AgentVerdict;
  agreement?: boolean | null; delta?: number | null; model?: string;
}
interface RunsPayload {
  empty: boolean;
  runs: {
    id: number; createdAt: string; caseId: string; caseName: string | null;
    department: string | null; year: number | null; humanDisposition: string | null;
    aiVerdict: string | null; aiConfidence: number | null; agreement: boolean | null;
    status: string; error: string | null;
  }[];
}

function AgentCard({
  icon, title, agent, tone,
}: {
  icon: React.ReactNode; title: string; agent?: AgentVerdict;
  tone: "emerald" | "red" | "amber";
}) {
  const color = tone === "emerald" ? "text-emerald-400" : tone === "red" ? "text-red-400" : "text-amber-400";
  return (
    <AccordionItem value={title}>
      <AccordionTrigger className="py-2 hover:no-underline">
        <div className="flex items-center gap-2">
          <span className={color}>{icon}</span>
          <span className="label-caps text-foreground/90">{title}</span>
          {agent ? (
            <span className="mono text-[10px] text-muted-foreground">
              · {agent.verdict === "affirmed" ? "CONFIRMER" : "INFIRMER"} · conf. {(agent.confidence * 100).toFixed(0)} %
            </span>
          ) : (
            <span className="mono text-[10px] text-red-400">· SORTIE INVALIDE (conservée brute)</span>
          )}
        </div>
      </AccordionTrigger>
      <AccordionContent>
        {agent ? (
          <div className="space-y-2 text-xs">
            <p className="text-foreground/90 leading-relaxed">{agent.summary}</p>
            <div>
              <div className="label-caps text-muted-foreground mb-1">ARGUMENTS CLÉS</div>
              <ol className="list-decimal list-inside space-y-1 mono text-[11px] text-muted-foreground">
                {agent.key_arguments.map((a, i) => <li key={i}>{a}</li>)}
              </ol>
            </div>
            <div>
              <div className="label-caps text-muted-foreground mb-1">CONFIANCE AUTO-DÉCLARÉE</div>
              <div className="h-1.5 bg-secondary rounded-sm overflow-hidden max-w-xs">
                <div
                  className={tone === "emerald" ? "h-full bg-emerald-400" : tone === "red" ? "h-full bg-red-400" : "h-full bg-amber-400"}
                  style={{ width: `${agent.confidence * 100}%` }}
                />
              </div>
            </div>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            La sortie de cet agent n'a pas pu être interprétée en JSON structuré — aucune
            reconstruction ne sera affichée à sa place.
          </p>
        )}
      </AccordionContent>
    </AccordionItem>
  );
}

export function ComparisonShield() {
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebounced(search), 350);
    return () => clearTimeout(t);
  }, [search]);

  const cases = useMatrixData<CasesPayload>(
    `/api/matrix/cases?limit=25${debounced ? `&search=${encodeURIComponent(debounced)}` : ""}`,
  );
  const runs = useMatrixData<RunsPayload>("/api/agents/runs?limit=15");

  const [selected, setSelected] = useState<CaseRow | null>(null);
  useEffect(() => {
    if (!selected && cases.data && !cases.data.empty && cases.data.cases.length > 0) {
      // only preselect a binary-eligible case with an extract (first page)
      const first = cases.data.cases.find((c) => c.binaryEligible && c.factsExcerpt) ?? null;
      if (first) setSelected(first);
    }
  }, [cases.data, selected]);

  const [running, setRunning] = useState(false);
  const [session, setSession] = useState<SessionPayload | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);

  const launch = useCallback(async () => {
    if (!selected) return;
    setRunning(true);
    setSession(null);
    setSessionError(null);
    try {
      const res = await fetch("/api/agents/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ caseId: selected.caseId }),
      });
      const json = await res.json();
      setSession(json as SessionPayload);
      runs.reload();
    } catch (e) {
      setSessionError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }, [selected, runs]);

  const deltaPct = useMemo(() => {
    if (!session || session.delta === null || session.delta === undefined) return null;
    return session.delta; // -1..+1
  }, [session]);

  return (
    <div className="space-y-4">
      <ModulePanel
        code="09"
        title="BOUCLIER DE COMPARAISON — HUMAIN vs IA NEUTRE"
        subtitle="Session multi-agents liée au recital officiel réel · z-ai-web-dev-sdk · sorties verbatim archivées"
        source="api/agents/session"
        actions={<ReloadButton onClick={() => { cases.reload(); runs.reload(); }} />}
      >
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {/* LEFT — case picker + real recital */}
          <div className="space-y-3 min-w-0">
            <Input
              placeholder="RECHERCHER UNE AFFAIRE (NOM, CITATION, ACCUSATION)…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-8 text-xs mono"
              aria-label="Rechercher une affaire"
            />
            <ModuleBody
              loading={cases.loading}
              error={cases.error}
              isEmpty={cases.isEmpty}
              emptyMessage="Index d'affaires vide — aucune affaire réelle disponible."
              data={cases.data}
            >
              {(d) => (
                <div className="max-h-56 overflow-y-auto space-y-1 pr-1 border border-border/60 rounded-sm p-1.5">
                  {d.cases.map((c) => (
                    <button
                      key={c.caseId}
                      onClick={() => { setSelected(c); setSession(null); setSessionError(null); }}
                      className={`w-full flex items-center justify-between gap-2 px-2 py-1.5 rounded-sm border text-left transition-colors ${
                        selected?.caseId === c.caseId ? "border-primary/50 bg-primary/10" : "border-transparent hover:bg-secondary/60"
                      }`}
                    >
                      <div className="min-w-0">
                        <div className="mono text-[11px] truncate">{c.caseName}</div>
                        <div className="mono text-[9px] text-muted-foreground truncate">
                          {c.dateFiled} · <span style={{ color: deptColor(c.department) }}>{DEPT_LABELS[c.department] ?? c.department}</span>
                          {c.charge ? ` · ${c.charge.slice(0, 42)}` : ""}
                        </div>
                      </div>
                      <VerdictBadge verdict={c.dispositionPrimary} />
                    </button>
                  ))}
                  {d.cases.length === 0 ? (
                    <p className="mono text-[10px] text-muted-foreground p-2">AUCUNE AFFAIRE CORRESPONDANTE.</p>
                  ) : null}
                </div>
              )}
            </ModuleBody>

            {selected ? (
              <div className="panel rounded-sm p-3 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="mono text-xs text-foreground truncate">{selected.caseName}</h3>
                  <VerdictBadge verdict={selected.dispositionPrimary} />
                </div>
                <div className="mono text-[10px] text-muted-foreground flex flex-wrap gap-x-3">
                  <span>{selected.dateFiled}</span>
                  <span style={{ color: deptColor(selected.department) }}>{DEPT_LABELS[selected.department] ?? selected.department}</span>
                  {selected.citation ? <span>{selected.citation}</span> : null}
                </div>
                {selected.charge ? (
                  <p className="mono text-[10px] text-amber-400/90">ACCUSATION : {selected.charge}</p>
                ) : null}
                <div>
                  <div className="label-caps text-muted-foreground mb-1">RECITAL OFFICIEL — VERBATIM</div>
                  <div className="max-h-44 overflow-y-auto mono text-[10px] leading-relaxed text-foreground/80 whitespace-pre-wrap border-l-2 border-border pl-3">
                    {selected.factsExcerpt ?? "Aucun recital extrait par le pipeline source — session refusée par conception (aucune donnée inventée)."}
                  </div>
                </div>
              </div>
            ) : null}
          </div>

          {/* RIGHT — agent session */}
          <div className="min-w-0">
            <div className="flex flex-col h-full gap-3">
              <Button
                onClick={launch}
                disabled={running || !selected || !selected.factsExcerpt}
                className="h-9 label-caps gap-2 bg-primary/15 border border-primary/40 text-primary hover:bg-primary/25"
              >
                <Swords className="h-3.5 w-3.5" aria-hidden />
                {running ? "SESSION EN COURS — 3 AGENTS…" : "LANCER LA SESSION MULTI-AGENTS"}
              </Button>

              {running ? (
                <TerminalLoader label="PROCUREUR → DÉFENSE → JUGE-IA · LIAISON LLM RÉELLE" />
              ) : sessionError ? (
                <div className="border border-destructive/40 bg-destructive/5 rounded-sm p-4">
                  <p className="label-caps text-red-400">ÉCHEC DE LIAISON</p>
                  <p className="mono text-[10px] text-muted-foreground mt-1 break-all">{sessionError}</p>
                </div>
              ) : session ? (
                session.status === "error" ? (
                  <div className="border border-destructive/40 bg-destructive/5 rounded-sm p-4 space-y-1">
                    <p className="label-caps text-red-400">SESSION EN ÉCHEC — ÉTAT EXPLICITE</p>
                    <p className="mono text-[10px] text-muted-foreground break-all">{session.error}</p>
                    <p className="mono text-[9px] text-muted-foreground/70">
                      Aucune réponse simulée n'est affichée à la place du moteur. Run #{session.runId} archivé.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {/* comparison */}
                    <div className="grid grid-cols-[1fr_auto_1fr] items-stretch gap-2">
                      <div className="panel rounded-sm p-3 text-center">
                        <div className="label-caps text-muted-foreground mb-1">DÉCISION HUMAINE</div>
                        <VerdictBadge verdict={session.case.humanBinary ?? session.case.humanDisposition} />
                        <div className="mono text-[9px] text-muted-foreground mt-1">cour d'appel réelle</div>
                      </div>
                      <div className="flex items-center px-2">
                        <span className="mono text-[10px] text-muted-foreground">VS</span>
                      </div>
                      <div className="panel rounded-sm p-3 text-center">
                        <div className="label-caps text-muted-foreground mb-1">JUGE-IA</div>
                        <VerdictBadge verdict={session.judge?.verdict} />
                        <div className="mono text-[9px] text-muted-foreground mt-1">
                          conf. {session.judge ? fmtPct(session.judge.confidence, 0) : "—"}
                        </div>
                      </div>
                    </div>

                    {/* delta gauge */}
                    {session.agreement !== null && session.agreement !== undefined ? (
                      <div className="panel rounded-sm p-3 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="label-caps text-muted-foreground">DELTA_HUMAIN</span>
                          <span className={`mono text-lg ${deltaPct !== null && deltaPct >= 0 ? "text-emerald-400 glow-emerald" : "text-red-400 glow-red"}`}>
                            {deltaPct !== null ? fmtSigned(deltaPct * 100, 1) : "—"}
                          </span>
                        </div>
                        <div className="relative h-2 bg-secondary rounded-sm">
                          <div className="absolute left-1/2 top-0 bottom-0 w-px bg-muted-foreground/40" />
                          <div
                            className={`absolute top-0 bottom-0 rounded-sm ${deltaPct !== null && deltaPct >= 0 ? "bg-emerald-400/80" : "bg-red-400/80"}`}
                            style={
                              deltaPct !== null && deltaPct >= 0
                                ? { left: "50%", width: `${(deltaPct * 50)}%` }
                                : { right: "50%", width: `${((-deltaPct ?? 0) * 50)}%` }
                            }
                          />
                        </div>
                        <p className="mono text-[9px] text-muted-foreground leading-relaxed">
                          {session.agreement
                            ? "ACCORD IA/HUMAIN — la barre mesure la force d'alignement (confiance du Juge-IA)."
                            : "DIVERGENCE IA/HUMAIN — la barre mesure la force du désaccord (confiance du Juge-IA). C'est l'écart que la psychologie humaine introduit sur les faits bruts, selon le modèle."}
                          {" "}Échelle −100 (divergence totale) à +100 (alignement total).
                        </p>
                      </div>
                    ) : (
                      <p className="mono text-[10px] text-amber-400/90">
                        Affaire non binaire ({session.case.humanDisposition ?? "non classée"}) —
                        comparaison stricte accord/divergence indisponible, verdicts affichés à titre d'analyse.
                      </p>
                    )}

                    {/* agent outputs */}
                    <Accordion type="multiple" className="border border-border/70 rounded-sm px-3">
                      <AgentCard icon={<ScrollText className="h-3.5 w-3.5" />} title="PROCUREUR (AGENT D'ACCUSATION)" agent={session.prosecutor} tone="red" />
                      <AgentCard icon={<ShieldCheck className="h-3.5 w-3.5" />} title="DÉFENSE (AGENT DE DÉFENSE)" agent={session.defender} tone="emerald" />
                      <AgentCard icon={<Gavel className="h-3.5 w-3.5" />} title="JUGE-IA (ARBITRE NEUTRE)" agent={session.judge} tone="amber" />
                    </Accordion>
                    <p className="mono text-[9px] text-muted-foreground/70">
                      Run #{session.runId} · {session.model} · sorties verbatim archivées dans l'index (audit de raisonnement).
                    </p>
                  </div>
                )
              ) : (
                <div className="flex-1 flex items-center justify-center border border-dashed border-border rounded-sm min-h-48 p-6">
                  <p className="mono text-[10px] text-muted-foreground text-center max-w-xs leading-relaxed">
                    Sélectionnez une affaire réelle puis lancez la session. Le Juge-IA ne voit
                    JAMAIS la décision humaine — il statue à l'aveugle sur le recital officiel.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </ModulePanel>

      {/* history */}
      <ModulePanel code="09·B" title="JOURNAL DES SESSIONS — AUDIT DE RAISONNEMENT" source="api/agents/runs">
        <ModuleBody
          loading={runs.loading}
          error={runs.error}
          isEmpty={runs.isEmpty}
          emptyMessage="Aucune session enregistrée. Les sessions futures seront archivées ici avec leurs métadonnées complètes."
          data={runs.data}
        >
          {(d) => (
            <div className="max-h-64 overflow-y-auto">
              <table className="w-full text-xs mono">
                <thead className="sticky top-0 bg-zinc-950/95 border-b border-border/70">
                  <tr>
                    {["#", "HORODATAGE", "AFFAIRE", "HUMAIN", "IA", "ACCORD", "ÉTAT"].map((h) => (
                      <th key={h} className="label-caps text-muted-foreground px-2 py-1.5 text-left">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {d.runs.map((r) => (
                    <tr key={r.id} className="border-b border-border/40 hover:bg-secondary/40">
                      <td className="px-2 py-1.5 text-muted-foreground">{r.id}</td>
                      <td className="px-2 py-1.5 text-muted-foreground">{new Date(r.createdAt).toLocaleString("fr-FR")}</td>
                      <td className="px-2 py-1.5 truncate max-w-48">{r.caseName ?? r.caseId}</td>
                      <td className="px-2 py-1.5"><VerdictBadge verdict={r.humanDisposition} /></td>
                      <td className="px-2 py-1.5"><VerdictBadge verdict={r.aiVerdict} /></td>
                      <td className="px-2 py-1.5">
                        {r.agreement === null || r.agreement === undefined ? (
                          <span className="text-muted-foreground">n/a</span>
                        ) : r.agreement ? (
                          <span className="text-emerald-400">OUI</span>
                        ) : (
                          <span className="text-red-400">NON</span>
                        )}
                      </td>
                      <td className="px-2 py-1.5">
                        {r.status === "ok" ? (
                          <span className="text-emerald-400">OK</span>
                        ) : (
                          <span className="text-red-400" title={r.error ?? ""}>ERREUR</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </ModuleBody>
      </ModulePanel>

      <MethodNote>
        Pipeline de session : le recital officiel de l'affaire (extrait Phase 2, verbatim) est
        transmis à trois agents distincts — Procureur (plaide la confirmation), Défense (plaide
        l'annulation), puis Juge-IA (arbitre neutre qui reçoit les arguments des deux parties mais
        JAMAIS la décision humaine réelle). Liaison réelle z-ai-web-dev-sdk, température basse,
        format de sortie JSON strict ; toute sortie non conforme est conservée brute et signalée,
        jamais complétée. Le Δ_humain est la confiance signée du Juge-IA (+accord / −divergence) :
        une mesure d'écart modèle-vs-humain, pas une preuve de biais.
      </MethodNote>
    </div>
  );
}
