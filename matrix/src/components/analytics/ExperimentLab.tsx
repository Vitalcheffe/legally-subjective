"use client";

/**
 * MODULE 10 — LABORATOIRE EXPÉRIMENTAL (PROTOCOLE ZERO-SHOT).
 * Turns the console from an observatory into a laboratory: a seeded
 * stratified sample of REAL cases is drawn, the multi-agent engine renders
 * an AI verdict on each (the human decision is never shown to the agents),
 * and the protocol is scored against the human outcomes — agreement, Wilson
 * CI, Brier score, calibration curve and an exact McNemar test vs the
 * always-affirm baseline. Every failure is surfaced verbatim, never faked.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { FlaskConical, Pause, Play, Plus, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import {
  useMatrixData, ModulePanel, ModuleBody, ReloadButton, fmtPct, fmtNum,
  KpiChip, MethodNote, TerminalLoader, ErrorState, deptColor, DEPT_LABELS,
} from "./shared";

interface ExperimentStatePayload {
  empty: boolean;
  message?: string;
  experiment: {
    id: number;
    label: string;
    seed: number;
    targetN: number;
    status: string;
    progress: number;
    createdAt: string;
    completedAt: string | null;
  };
  protocol: {
    poolSize: number;
    binaryEligibleTotal: number;
    excludedNoRecital: number;
    minRecitalChars: number;
  };
  pending: number;
  errors: { caseId: string; note: string }[];
  results: {
    nScored: number;
    nError: number;
    agreement: number;
    agreementK: number;
    wilson: { low: number; high: number };
    baseRate: number;
    baselineAccuracy: number;
    confusion: {
      aiAffirmedHumanAffirmed: number;
      aiAffirmedHumanReversed: number;
      aiReversedHumanAffirmed: number;
      aiReversedHumanReversed: number;
    };
    brier: number;
    brierBaseline: number;
    calibration: { label: string; n: number; meanConfidence: number; observedRate: number }[];
    mcnemar: { b: number; c: number; exactP: number };
    perDepartment: { department: string; n: number; agreement: number }[];
    runs: {
      runId: number; caseId: string; caseName: string; department: string;
      human: string; ai: string; confidence: number; agreement: boolean;
    }[];
  };
}

interface ExperimentsListPayload {
  empty: boolean;
  experiments: {
    id: number; label: string; seed: number; targetN: number;
    status: string; progress: number; createdAt: string;
    completedAt: string | null; runs: number;
  }[];
}

// ---------------------------------------------------------------------------
// Calibration curve (custom SVG — reliability diagram)
// ---------------------------------------------------------------------------
function CalibrationCurve({
  buckets,
}: {
  buckets: { label: string; n: number; meanConfidence: number; observedRate: number }[];
}) {
  const size = 260;
  const pad = 34;
  const plot = size - pad * 2;
  const active = buckets.filter((b) => b.n > 0);
  const maxN = Math.max(1, ...buckets.map((b) => b.n));
  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      className="w-full h-auto max-w-[300px] mx-auto"
      role="img"
      aria-label="Courbe de calibration : confiance IA vs fréquence observée"
    >
      {/* grid */}
      {[0.25, 0.5, 0.75].map((g) => (
        <g key={g}>
          <line x1={pad + g * plot} y1={pad} x2={pad + g * plot} y2={size - pad} stroke="#D8D3C8" strokeDasharray="2 4" />
          <line x1={pad} y1={size - pad - g * plot} x2={size - pad} y2={size - pad - g * plot} stroke="#D8D3C8" strokeDasharray="2 4" />
        </g>
      ))}
      {/* frame */}
      <rect x={pad} y={pad} width={plot} height={plot} fill="none" stroke="#B8B2A6" />
      {/* diagonal = perfect calibration */}
      <line x1={pad} y1={size - pad} x2={size - pad} y2={pad} stroke="#B8863B" strokeDasharray="4 3" strokeWidth={1.2} />
      <text x={size - pad - 4} y={pad + 10} fill="#B8863B" fontSize={8} textAnchor="end">calibration parfaite</text>
      {/* points */}
      {active.map((b) => {
        const cx = pad + b.meanConfidence * plot;
        const cy = size - pad - b.observedRate * plot;
        const r = 3 + Math.sqrt(b.n / maxN) * 6;
        return (
          <g key={b.label}>
            <line x1={cx} y1={cy} x2={cx} y2={size - pad} stroke="#2F7D51" strokeOpacity={0.25} />
            <circle cx={cx} cy={cy} r={r} fill="#2F7D51" fillOpacity={0.75} stroke="#FFFFFF" strokeWidth={1}>
              <title>{`${b.label} · n=${b.n} · confiance ${(b.meanConfidence * 100).toFixed(0)}% vs observé ${(b.observedRate * 100).toFixed(0)}%`}</title>
            </circle>
          </g>
        );
      })}
      {/* axis labels */}
      <text x={size / 2} y={size - 8} fill="#756F65" fontSize={9} textAnchor="middle">confiance IA (Pconfirmé)</text>
      <text x={10} y={size / 2} fill="#756F65" fontSize={9} textAnchor="middle" transform={`rotate(-90 10 ${size / 2})`}>fréquence humaine observée</text>
      {[0, 0.5, 1].map((t) => (
        <g key={`t${t}`}>
          <text x={pad + t * plot} y={size - pad + 12} fill="#756F65" fontSize={8} textAnchor="middle">{t.toFixed(1)}</text>
          <text x={pad - 8} y={size - pad - t * plot + 3} fill="#756F65" fontSize={8} textAnchor="end">{t.toFixed(1)}</text>
        </g>
      ))}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Confusion matrix 2×2
// ---------------------------------------------------------------------------
function ConfusionMatrix({
  confusion,
}: {
  confusion: ExperimentStatePayload["results"]["confusion"];
}) {
  const cells: { label: string; value: number; cls: string; title: string }[][] = [
    [
      { label: "IA CONFIRME", value: confusion.aiAffirmedHumanAffirmed, cls: "text-pos", title: "IA et humain confirment" },
      { label: "IA CONFIRME", value: confusion.aiAffirmedHumanReversed, cls: "text-neg", title: "IA confirme, humain infirme" },
    ],
    [
      { label: "IA INFIRME", value: confusion.aiReversedHumanAffirmed, cls: "text-neg", title: "IA infirme, humain confirme" },
      { label: "IA INFIRME", value: confusion.aiReversedHumanReversed, cls: "text-pos", title: "IA et humain infirment" },
    ],
  ];
  return (
    <div className="grid grid-cols-[auto_1fr_1fr] gap-px bg-border/60 border border-border/70 rounded-sm text-center">
      <div />
      <div className="label-caps text-[9px] text-muted-foreground bg-card px-1 py-1.5">HUMAIN CONFIRME</div>
      <div className="label-caps text-[9px] text-muted-foreground bg-card px-1 py-1.5">HUMAIN INFIRME</div>
      {cells.map((row, i) => (
        <div key={i} className="contents">
          <div className="label-caps text-[9px] text-muted-foreground bg-card px-1.5 py-2 flex items-center justify-end">{row[0].label}</div>
          {row.map((c, j) => (
            <div key={j} title={c.title} className="bg-card px-1 py-2.5">
              <div className={cn("mono text-xl leading-none", c.cls)}>{c.value}</div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main module
// ---------------------------------------------------------------------------
export function ExperimentLab() {
  const list = useMatrixData<ExperimentsListPayload>("/api/matrix/experiments");
  const [targetN, setTargetN] = useState("10");
  const [seed, setSeed] = useState("42");
  const [label, setLabel] = useState("");
  const [state, setState] = useState<ExperimentStatePayload | null>(null);
  const [launching, setLaunching] = useState(false);
  const [stepping, setStepping] = useState(false);
  const [autoRun, setAutoRun] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const stopRef = useRef(false);

// loadState declared before the mount effect that uses it (TDZ safety)

  const loadState = useCallback(async (id: number) => {
    try {
      const res = await fetch(`/api/matrix/experiments?id=${id}`);
      const json = await res.json();
      if (!res.ok && json?.message) throw new Error(json.message);
      setState(json as ExperimentStatePayload);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  // load the most recent experiment on mount
  useEffect(() => {
    const exps = list.data?.experiments ?? [];
    if (exps.length > 0 && !state && !launching) {
      const target = exps.find((e) => e.status === "running") ?? exps[0];
      loadState(target.id).catch(() => undefined);
    }
  }, [list.data, state, launching, loadState]);

  const launch = async () => {
    setLaunching(true);
    setError(null);
    stopRef.current = false;
    try {
      const res = await fetch("/api/matrix/experiments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          targetN: Number(targetN),
          seed: Number(seed) || 42,
          label: label.trim() || undefined,
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.message ?? `HTTP ${res.status}`);
      setState(json as ExperimentStatePayload);
      list.reload();
      // auto-start the run loop
      setAutoRun(true);
      await driveLoop(json.experiment.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLaunching(false);
      setAutoRun(false);
    }
  };

  const step = async (id: number, retryFailed = false) => {
    const res = await fetch("/api/matrix/experiments/step", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, retryFailed }),
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json?.message ?? `HTTP ${res.status}`);
    setState(json as ExperimentStatePayload);
    return json as ExperimentStatePayload;
  };

  const driveLoop = async (id: number) => {
    for (let guard = 0; guard < 60; guard++) {
      if (stopRef.current) break;
      const next = await step(id);
      if (next?.experiment?.status === "done") break;
    }
  };

  const startAuto = async () => {
    if (!state?.experiment) return;
    setAutoRun(true);
    stopRef.current = false;
    try {
      await driveLoop(state.experiment.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAutoRun(false);
      list.reload();
    }
  };

  const stopAuto = () => {
    stopRef.current = true;
  };

  const retryErrors = async () => {
    if (!state?.experiment) return;
    setAutoRun(true);
    stopRef.current = false;
    try {
      // first step requeues every errored case, then re-attempts them
      let first = true;
      for (let guard = 0; guard < 60; guard++) {
        if (stopRef.current) break;
        const next = await step(state.experiment.id, first);
        first = false;
        if (next?.experiment?.status === "done") break;
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAutoRun(false);
      list.reload();
    }
  };

  const stepOnce = async () => {
    if (!state?.experiment) return;
    setStepping(true);
    try {
      await step(state.experiment.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setStepping(false);
      list.reload();
    }
  };

  const exp = state?.experiment;
  const r = state?.results;
  const hasScored = (r?.nScored ?? 0) > 0;

  return (
    <div className="space-y-4">
      <ModulePanel
        code="10"
        title="Laboratoire expérimental — protocole zero-shot"
        subtitle="Échantillon stratifié seedé d'affaires réelles · verdicts multi-agents rendus à l'aveugle de la décision humaine · scoring statistique complet"
        source="api/matrix/experiments"
        actions={<ReloadButton onClick={list.reload} />}
      >
        <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-6">
          {/* ---------------- protocol control ---------------- */}
          <div className="space-y-3">
            <div>
              <label className="label-caps text-muted-foreground block mb-1" htmlFor="exp-n">TAILLE CIBLE (N CAS)</label>
              <Select value={targetN} onValueChange={setTargetN} disabled={launching || autoRun}>
                <SelectTrigger id="exp-n" className="h-8 text-xs mono border-border/70"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {["10", "15", "20", "30"].map((n) => <SelectItem key={n} value={n}>{n} affaires</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="label-caps text-muted-foreground block mb-1" htmlFor="exp-seed">GRAINE (REPRODUCTIBILITÉ)</label>
              <Input
                id="exp-seed"
                type="number"
                value={seed}
                onChange={(e) => setSeed(e.target.value)}
                disabled={launching || autoRun}
                className="h-8 text-xs mono"
              />
            </div>
            <div>
              <label className="label-caps text-muted-foreground block mb-1" htmlFor="exp-label">ÉTIQUETTE (FACULTATIF)</label>
              <Input
                id="exp-label"
                placeholder="ex. zero-shot v1…"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                disabled={launching || autoRun}
                className="h-8 text-xs mono"
              />
            </div>
            <Button
              onClick={launch}
              disabled={launching || autoRun}
              className="w-full h-9 label-caps gap-2 bg-primary/15 border border-primary/40 text-primary hover:bg-primary/25"
            >
              <FlaskConical className="h-3.5 w-3.5" aria-hidden />
              {launching ? "CONSTITUTION DE L'ÉCHANTILLON…" : "LANCER LE PROTOCOLE"}
            </Button>
            <p className="mono text-[9px] text-muted-foreground/70 leading-relaxed">
              Critères d'inclusion (documentés) : affaire binaire réelle + recital officiel ≥ 120 caractères.
              Stratification proportionnelle département × issue. Le tirage est seedé : même graine = même
              échantillon, bit pour bit. La décision humaine n'est JAMAIS montrée aux agents.
            </p>

            {exp ? (
              <div className="panel rounded-sm p-3 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="label-caps text-muted-foreground">PROTOCOLE #{exp.id}</span>
                  <span className={cn(
                    "mono text-[10px] border rounded-sm px-1.5 py-0.5",
                    exp.status === "done" ? "text-pos border-pos bg-pos-subtle"
                    : exp.status === "running" ? "text-mix border-mix bg-mix-subtle"
                    : "text-neg border-neg bg-neg-subtle",
                  )}>
                    {exp.status === "done" ? "TERMINÉ" : exp.status === "running" ? "EN COURS" : exp.status.toUpperCase()}
                  </span>
                </div>
                <p className="mono text-[10px] text-muted-foreground truncate">{exp.label}</p>
                <div className="mono text-[10px] text-muted-foreground flex justify-between">
                  <span>graine {exp.seed}</span>
                  <span>{exp.progress}/{exp.targetN} résolus</span>
                </div>
                <div className="h-1.5 w-full bg-secondary rounded-sm overflow-hidden">
                  <div
                    className="h-full bg-pos transition-all"
                    style={{ width: `${exp.targetN > 0 ? Math.min(100, (exp.progress / exp.targetN) * 100) : 0}%` }}
                  />
                </div>
                {state?.pending ? (
                  <p className="mono text-[9px] text-mix">{state.pending} dossier(s) en attente de session</p>
                ) : null}
                {state && state.errors.length > 0 && exp?.status === "done" ? (
                  <button
                    onClick={retryErrors}
                    disabled={autoRun || stepping}
                    className="w-full mono text-[10px] label-caps gap-1.5 border border-neg text-neg hover:bg-neg-subtle rounded-sm px-2 py-1.5 transition-colors disabled:opacity-50"
                  >
                    REJOUER LES ÉCHECS ({state.errors.length})
                  </button>
                ) : null}
                <div className="flex gap-2 pt-1">
                  {autoRun ? (
                    <Button onClick={stopAuto} variant="outline" size="sm" className="h-7 flex-1 label-caps gap-1.5 border-mix text-mix">
                      <Pause className="h-3 w-3" aria-hidden /> PAUSE
                    </Button>
                  ) : (
                    <Button
                      onClick={startAuto}
                      disabled={stepping || exp.status === "done" || !hasScored && exp.progress === 0 ? exp.status === "done" : false}
                      variant="outline"
                      size="sm"
                      className="h-7 flex-1 label-caps gap-1.5 border-pos text-pos"
                    >
                      <Play className="h-3 w-3" aria-hidden /> REPRENDRE
                    </Button>
                  )}
                  <Button
                    onClick={stepOnce}
                    disabled={stepping || autoRun || exp.status === "done"}
                    variant="outline"
                    size="sm"
                    className="h-7 flex-1 label-caps gap-1.5 border-border/70"
                  >
                    <Plus className="h-3 w-3" aria-hidden /> PAS +1
                  </Button>
                </div>
              </div>
            ) : null}

            {/* previous protocols */}
            {list.data && !list.data.empty && (list.data.experiments.length > 1 || !exp) ? (
              <div className="panel rounded-sm p-3">
                <p className="label-caps text-muted-foreground mb-2">PROTOCOLES ARCHIVÉS</p>
                <div className="space-y-1 max-h-44 overflow-y-auto thin-scroll">
                  {list.data.experiments.map((e) => (
                    <button
                      key={e.id}
                      onClick={() => loadState(e.id)}
                      className={cn(
                        "w-full flex items-center gap-2 px-2 py-1.5 rounded-sm border text-left transition-colors",
                        exp?.id === e.id
                          ? "border-primary/50 bg-primary/10"
                          : "border-border/50 hover:border-border hover:bg-secondary/50",
                      )}
                    >
                      <span className="mono text-[10px] text-muted-foreground">#{e.id}</span>
                      <span className="mono text-[10px] text-foreground/80 truncate flex-1">{e.label}</span>
                      <span className="mono text-[9px] text-muted-foreground">{e.progress}/{e.targetN}</span>
                      {e.status === "done" ? (
                        <Square className="h-2.5 w-2.5 text-pos" aria-hidden />
                      ) : (
                        <span className="h-2 w-2 rounded-full bg-mix pulse-led" aria-hidden />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
          </div>

          {/* ---------------- results ---------------- */}
          <div className="min-w-0">
            {error ? <ErrorState message={error} /> : null}
            {!state ? (
              list.loading ? (
                <TerminalLoader label="INTERROGATION DES PROTOCOLES ARCHIVÉS" />
              ) : list.isEmpty ? (
                <div className="flex items-center justify-center h-full min-h-64">
                  <div className="max-w-md text-center space-y-2 border border-dashed border-border rounded-sm p-8">
                    <FlaskConical className="h-6 w-6 mx-auto text-muted-foreground" aria-hidden />
                    <p className="label-caps text-mix">AUCUN PROTOCOLE EXÉCUTÉ</p>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      Lancez le premier protocole zero-shot : le moteur tirera un échantillon
                      stratifié d'affaires réelles et rendra un verdict IA sur chacune, à
                      l'aveugle de la décision humaine. Aucun résultat ne sera affiché avant
                      qu'une session réelle ne l'ait produit.
                    </p>
                  </div>
                </div>
              ) : null
            ) : (
              <div className="space-y-4">
                {autoRun || stepping ? (
                  <div className="panel rounded-sm px-3 py-2 flex items-center gap-3 border-mix bg-mix-subtle">
                    <span className="h-2 w-2 rounded-full bg-mix pulse-led shrink-0" aria-hidden />
                    <p className="mono text-[10px] text-mix">
                      SESSION MULTI-AGENTS EN COURS — PROCUREUR → DÉFENSE → JUGE-IA (appels LLM réels, 1 dossier par pas)
                    </p>
                  </div>
                ) : null}

                {hasScored ? (
                  <>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      <KpiChip
                        label="ACCORD IA-HUMAIN"
                        value={fmtPct(r!.agreement)}
                        tone="pos"
                        sub={`${r!.agreementK}/${r!.nScored} verdicts · IC95 [${fmtPct(r!.wilson.low)} ; ${fmtPct(r!.wilson.high)}]`}
                      />
                      <KpiChip
                        label="BRIER SCORE"
                        value={r!.brier.toFixed(3)}
                        tone={r!.brier <= r!.brierBaseline ? "pos" : "neg"}
                        sub={`prédicteur base ${r!.brierBaseline.toFixed(3)} (0 = parfait)`}
                      />
                      <KpiChip
                        label="MCNEMAR vs TOUJOURS-CONFIRMER"
                        value={`p = ${r!.mcnemar.exactP.toFixed(4)}`}
                        tone={r!.mcnemar.exactP < 0.05 ? "pos" : "neutral"}
                        sub={`discordants : IA seule juste ${r!.mcnemar.c} · base seule juste ${r!.mcnemar.b}`}
                      />
                      <KpiChip
                        label="BASE AFFIRMÉE (ÉCHANTILLON)"
                        value={fmtPct(r!.baseRate)}
                        tone="mix"
                        sub={`baseline toujours-confirmer : ${fmtPct(r!.baselineAccuracy)}`}
                      />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="panel rounded-sm p-3">
                        <p className="label-caps text-muted-foreground mb-2">MATRICE DE CONFUSION (IA × HUMAIN)</p>
                        <ConfusionMatrix confusion={r!.confusion} />
                      </div>
                      <div className="panel rounded-sm p-3">
                        <p className="label-caps text-muted-foreground mb-1">COURBE DE CALIBRATION</p>
                        <CalibrationCurve buckets={r!.calibration} />
                        <p className="mono text-[9px] text-muted-foreground/80 text-center">
                          rayon ∝ effectif du bac · diagonale = calibration parfaite
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="panel rounded-sm p-3">
                        <p className="label-caps text-muted-foreground mb-2">ACCORD PAR DÉPARTEMENT</p>
                        <div className="space-y-1.5">
                          {r!.perDepartment.map((d) => (
                            <div key={d.department} className="flex items-center gap-2">
                              <span className="h-2 w-2 rounded-sm shrink-0" style={{ background: deptColor(d.department) }} aria-hidden />
                              <span className="mono text-[10px] text-muted-foreground w-20">{DEPT_LABELS[d.department] ?? d.department}</span>
                              <div className="flex-1 h-1.5 bg-secondary rounded-sm overflow-hidden">
                                <div className="h-full bg-pos" style={{ width: `${d.agreement * 100}%` }} />
                              </div>
                              <span className="mono text-[10px] text-foreground/80 w-20 text-right">{fmtPct(d.agreement)} · n={d.n}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="panel rounded-sm p-3">
                        <p className="label-caps text-muted-foreground mb-2">PROTOCOLE</p>
                        <div className="space-y-1 mono text-[10px] text-muted-foreground">
                          <div className="flex justify-between"><span>éligibles binaires</span><span className="text-foreground/80">{fmtNum(state.protocol.binaryEligibleTotal)}</span></div>
                          <div className="flex justify-between"><span>échantillon tiré</span><span className="text-foreground/80">{state.protocol.poolSize}</span></div>
                          <div className="flex justify-between"><span>exclus (recital &lt; {state.protocol.minRecitalChars} car.)</span><span className="text-foreground/80">{state.protocol.excludedNoRecital}</span></div>
                          <div className="flex justify-between"><span>sessions en erreur</span><span className={r!.nError > 0 ? "text-neg" : "text-foreground/80"}>{r!.nError}</span></div>
                          <div className="flex justify-between"><span>créé le</span><span className="text-foreground/80">{new Date(state.experiment.createdAt).toLocaleString("fr-FR")}</span></div>
                          {state.experiment.completedAt ? (
                            <div className="flex justify-between"><span>terminé le</span><span className="text-foreground/80">{new Date(state.experiment.completedAt).toLocaleString("fr-FR")}</span></div>
                          ) : null}
                        </div>
                      </div>
                    </div>

                    {/* runs ledger */}
                    <div className="panel rounded-sm p-3">
                      <p className="label-caps text-muted-foreground mb-2">REGISTRE DES VERDICTS ({r!.runs.length})</p>
                      <div className="max-h-80 overflow-y-auto overflow-x-auto thin-scroll">
                        <table className="w-full text-left">
                          <thead className="sticky top-0 bg-card">
                            <tr className="label-caps text-[9px] text-muted-foreground border-b border-border/60">
                              <th className="py-1.5 pr-2 font-normal">Affaire</th>
                              <th className="py-1.5 pr-2 font-normal">Dép.</th>
                              <th className="py-1.5 pr-2 font-normal">Humain</th>
                              <th className="py-1.5 pr-2 font-normal">Juge-IA</th>
                              <th className="py-1.5 pr-2 font-normal">Confiance</th>
                              <th className="py-1.5 font-normal">Accord</th>
                            </tr>
                          </thead>
                          <tbody className="mono text-[10px]">
                            {r!.runs.map((run) => (
                              <tr key={run.runId} className="border-b border-border/30 hover:bg-secondary/40">
                                <td className="py-1.5 pr-2 truncate max-w-56" title={`${run.caseName} · ${run.caseId}`}>{run.caseName}</td>
                                <td className="py-1.5 pr-2">
                                  <span className="inline-flex items-center gap-1">
                                    <span className="h-1.5 w-1.5 rounded-sm" style={{ background: deptColor(run.department) }} aria-hidden />
                                    {DEPT_LABELS[run.department] ?? run.department}
                                  </span>
                                </td>
                                <td className={cn("py-1.5 pr-2", run.human === "affirmed" ? "text-pos" : "text-neg")}>
                                  {run.human === "affirmed" ? "CONFIRMÉ" : "INFIRMÉ"}
                                </td>
                                <td className={cn("py-1.5 pr-2", run.ai === "affirmed" ? "text-pos" : "text-neg")}>
                                  {run.ai === "affirmed" ? "CONFIRMÉ" : "INFIRMÉ"}
                                </td>
                                <td className="py-1.5 pr-2 text-muted-foreground">{(run.confidence * 100).toFixed(0)} %</td>
                                <td className="py-1.5">
                                  {run.agreement ? (
                                    <span className="text-pos border border-pos bg-pos-subtle rounded-sm px-1.5 py-0.5">OUI</span>
                                  ) : (
                                    <span className="text-neg border border-neg bg-neg-subtle rounded-sm px-1.5 py-0.5">NON</span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    <MethodNote>
                      Protocole zero-shot : les agents (Procureur → Défense → Juge-IA) délibèrent sur le
                      recital officiel des faits sans jamais voir la décision humaine. Accord = verdict IA
                      binaire vs issue humaine binaire. IC95 Wilson. Brier = erreur quadratique moyenne de
                      P(confirmé) prédite. McNemar exact = comparaison appariée IA vs baseline
                      « toujours confirmer » sur les mêmes dossiers. Tirage stratifié seedé
                      (graine {state.experiment.seed}) — reproductible bit pour bit.
                    </MethodNote>
                  </>
                ) : exp?.status === "running" || exp?.progress === 0 ? (
                  <TerminalLoader label="PROTOCOLE ARMÉ — EN ATTENTE DE LA PREMIÈRE SESSION RÉELLE" />
                ) : (
                  <div className="border border-neg bg-neg-subtle rounded-sm p-4 space-y-2">
                    <p className="label-caps text-neg">AUCUN VERDICT VALIDE ARCHIVÉ</p>
                    {state.errors.length > 0 ? (
                      <div className="mono text-[10px] text-muted-foreground space-y-1 max-h-40 overflow-y-auto thin-scroll">
                        {state.errors.map((e) => (
                          <p key={e.caseId} className="break-all">[{e.caseId}] {e.note}</p>
                        ))}
                      </div>
                    ) : null}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </ModulePanel>
    </div>
  );
}
