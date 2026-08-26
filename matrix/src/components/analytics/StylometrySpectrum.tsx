"use client";

/**
 * MODULE 05 — SPECTRE STYLOMÉTRIQUE.
 * Lexical telemetry computed on the FULL official text of each real opinion
 * at ingest (rule R4): sentence length, type-token ratio, punitive vs
 * rehabilitative lexicon hits. Aggregated by department and by year.
 */
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import {
  useMatrixData, ModulePanel, ModuleBody, ReloadButton, fmtPct, fmtNum,
  KpiChip, MethodNote, DEPT_LABELS, deptColor,
} from "./shared";

interface StyloPayload {
  empty: boolean;
  message?: string;
  corpus: {
    n: number; avgSentenceLen: number; avgTtr: number; avgTokens: number;
    punitivePer1k: number; rehabPer1k: number; punitiveTotal: number;
    rehabTotal: number; ratio: number | null;
  };
  byDepartment: {
    department: string; n: number; avgSentenceLen: number; avgTtr: number;
    punitivePer1k: number; rehabPer1k: number; ratio: number | null;
  }[];
  byYear: { year: number; n: number; avgSentenceLen: number; avgTtr: number; punitivePer1k: number; rehabPer1k: number }[];
  ratioHistogram: { binLabel: string; binStart: number; count: number }[];
  sentenceHistogram: { binLabel: string; count: number }[];
  methodNote: string;
}

const tooltipStyle = {
  background: "#09090b", border: "1px solid #27272a", borderRadius: 2,
  fontSize: 11, fontFamily: "var(--font-geist-mono)",
};

export function StylometrySpectrum() {
  const { data, loading, error, isEmpty, reload } = useMatrixData<StyloPayload>("/api/matrix/stylometry");

  return (
    <div className="space-y-4">
      <ModulePanel
        code="05"
        title="SPECTRE STYLOMÉTRIQUE — TÉLÉMÉTRIE LEXICALE DES OPINIONS"
        subtitle="Calculée sur le texte officiel intégral de chaque opinion (1 387 documents)"
        source="api/matrix/stylometry"
        actions={<ReloadButton onClick={reload} />}
      >
        <ModuleBody
          loading={loading}
          error={error}
          isEmpty={isEmpty}
          emptyMessage="Aucun texte officiel indexé — la stylométrie n'affiche que du calculé."
          data={data}
        >
          {(d) => (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <KpiChip label="OPINIONS ANALYSÉES" value={fmtNum(d.corpus.n)} sub="texte officiel intégral" />
                <KpiChip label="LONGUEUR MOY. PHRASE" value={`${d.corpus.avgSentenceLen.toFixed(0)} car.`} tone="amber" sub="corpus complet" />
                <KpiChip label="RICHESSE LEXICALE (TTR)" value={d.corpus.avgTtr.toFixed(3)} sub="types / tokens" />
                <KpiChip
                  label="RATIO PUNITIF/RÉHAB."
                  value={d.corpus.ratio ? `${d.corpus.ratio.toFixed(1)} : 1` : "—"}
                  tone="red"
                  sub={`${fmtNum(d.corpus.punitiveTotal)} vs ${fmtNum(d.corpus.rehabTotal)} occurrences`}
                />
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <div>
                  <h3 className="label-caps text-muted-foreground mb-2">
                    VOCABULAIRE PUNITIF VS RÉHABILITATIF — POUR 1 000 MOTS, PAR DÉPARTEMENT
                  </h3>
                  <div className="h-64 border border-border/70 rounded-sm p-2 bg-zinc-950/40">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={d.byDepartment.map((r) => ({ ...r, label: DEPT_LABELS[r.department] ?? r.department }))}>
                        <CartesianGrid stroke="#27272a" strokeDasharray="2 4" />
                        <XAxis dataKey="label" stroke="#71717a" fontSize={10} tickLine={false} />
                        <YAxis stroke="#71717a" fontSize={10} tickLine={false} />
                        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#27272a33" }}
                          formatter={(v: number, name: string) => [v.toFixed(2), name === "punitivePer1k" ? "punitif" : "réhabilitatif"]} />
                        <Legend wrapperStyle={{ fontSize: 10 }} formatter={(v: string) => (v === "punitivePer1k" ? "Punitif" : "Réhabilitatif")} />
                        <Bar dataKey="punitivePer1k" fill="#f87171" isAnimationActive={false} />
                        <Bar dataKey="rehabPer1k" fill="#34d399" isAnimationActive={false} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div>
                  <h3 className="label-caps text-muted-foreground mb-2">
                    ÉVOLUTION TEMPORELLE — LONGUEUR DE PHRASE & RICHESSE LEXICALE
                  </h3>
                  <div className="h-64 border border-border/70 rounded-sm p-2 bg-zinc-950/40">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={d.byYear}>
                        <CartesianGrid stroke="#27272a" strokeDasharray="2 4" />
                        <XAxis dataKey="year" stroke="#71717a" fontSize={10} tickLine={false} />
                        <YAxis yAxisId="len" stroke="#71717a" fontSize={10} tickLine={false} />
                        <YAxis yAxisId="ttr" orientation="right" stroke="#71717a" fontSize={10} tickLine={false} />
                        <Tooltip contentStyle={tooltipStyle}
                          formatter={(v: number, name: string) => [name === "avgSentenceLen" ? v.toFixed(1) : v.toFixed(3), name === "avgSentenceLen" ? "car./phrase" : "TTR"]} />
                        <Legend wrapperStyle={{ fontSize: 10 }} formatter={(v: string) => (v === "avgSentenceLen" ? "Longueur phrase" : "TTR")} />
                        <Line yAxisId="len" type="monotone" dataKey="avgSentenceLen" stroke="#fbbf24" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                        <Line yAxisId="ttr" type="monotone" dataKey="avgTtr" stroke="#34d399" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div>
                  <h3 className="label-caps text-muted-foreground mb-2">
                    DISTRIBUTION DU RATIO PUNITIF/RÉHAB. PAR OPINION (ÉCHELLE LOG 2)
                  </h3>
                  <div className="h-56 border border-border/70 rounded-sm p-2 bg-zinc-950/40">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={d.ratioHistogram}>
                        <CartesianGrid stroke="#27272a" strokeDasharray="2 4" />
                        <XAxis dataKey="binLabel" stroke="#71717a" fontSize={9} tickLine={false} />
                        <YAxis stroke="#71717a" fontSize={10} tickLine={false} />
                        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#27272a33" }}
                          formatter={(v: number) => [`${v} opinions`, "effectif"]} />
                        <Bar dataKey="count" isAnimationActive={false}>
                          {d.ratioHistogram.map((_, i) => (
                            <Cell key={i} fill={i < 4 ? "#34d399" : i > 8 ? "#f87171" : "#a1a1aa"} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div>
                  <h3 className="label-caps text-muted-foreground mb-2">
                    DISTRIBUTION DE LA LONGUEUR MOYENNE DE PHRASE (CARACTÈRES)
                  </h3>
                  <div className="h-56 border border-border/70 rounded-sm p-2 bg-zinc-950/40">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={d.sentenceHistogram}>
                        <CartesianGrid stroke="#27272a" strokeDasharray="2 4" />
                        <XAxis dataKey="binLabel" stroke="#71717a" fontSize={9} tickLine={false} interval={2} />
                        <YAxis stroke="#71717a" fontSize={10} tickLine={false} />
                        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#27272a33" }}
                          formatter={(v: number) => [`${v} opinions`, "effectif"]} />
                        <Bar dataKey="count" fill="#fbbf24" isAnimationActive={false} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-xs mono border border-border/70 rounded-sm">
                  <thead className="border-b border-border/70">
                    <tr>
                      {["DÉPARTEMENT", "N", "CAR./PHRASE", "TTR", "PUNITIF/1K", "RÉHAB./1K", "RATIO"].map((h) => (
                        <th key={h} className="label-caps text-muted-foreground px-3 py-2 text-left">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {d.byDepartment.map((r) => (
                      <tr key={r.department} className="border-b border-border/40 hover:bg-secondary/40">
                        <td className="px-3 py-1.5" style={{ color: deptColor(r.department) }}>
                          {DEPT_LABELS[r.department] ?? r.department}
                        </td>
                        <td className="px-3 py-1.5">{fmtNum(r.n)}</td>
                        <td className="px-3 py-1.5">{r.avgSentenceLen.toFixed(1)}</td>
                        <td className="px-3 py-1.5">{r.avgTtr.toFixed(3)}</td>
                        <td className="px-3 py-1.5 text-red-400">{r.punitivePer1k.toFixed(2)}</td>
                        <td className="px-3 py-1.5 text-emerald-400">{r.rehabPer1k.toFixed(2)}</td>
                        <td className="px-3 py-1.5">{r.ratio ? `${r.ratio.toFixed(1)} : 1` : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </ModuleBody>
      </ModulePanel>

      <MethodNote>
        {data && !data.empty ? data.methodNote : "Méthode R4 : texte officiel intégral (feuilles de style et scripts retirés), lexiques punitif (17 entrées) et réhabilitatif (14 entrées) documentés dans scripts/ingest.ts, comptage par sous-chaîne insensible à la casse. Le TTR est sensible à la longueur — comparez des opinions de longueur similaire. L'auteur individuel de chaque opinion n'étant pas extrait, l'agrégation est départementale et annuelle (jamais attribuée à un juge sans preuve d'auteur)."}
      </MethodNote>
    </div>
  );
}
