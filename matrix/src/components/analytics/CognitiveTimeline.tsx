"use client";

/**
 * MODULE 07 — CHRONOLOGIE COGNITIVE.
 * Real temporal telemetry: monthly decision volume, monthly/rolling
 * affirmance rates, month-of-year aggregation (documented chronobiology
 * PROXY — filing dates, not hearing times, exist in the source).
 */
import {
  Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import {
  useMatrixData, ModulePanel, ModuleBody, ReloadButton, fmtPct, fmtNum,
  KpiChip, MethodNote,
} from "./shared";

interface TimelinePayload {
  empty: boolean;
  monthly: { month: string; nBinary: number; volume: number; affirmed: number; rate: number | null }[];
  monthOfYear: { month: number; n: number; affirmed: number; rate: number | null }[];
  byYear: { year: number; n: number; affirmed: number; rate: number }[];
  rolling: { month: string; rate: number | null; n: number }[];
}

const tooltipStyle = {
  background: "#FFFFFF", border: "1px solid #D8D3C8", borderRadius: 2,
  fontSize: 11, fontFamily: "var(--font-geist-mono)",
};
const MONTH_LABELS = ["JAN", "FÉV", "MAR", "AVR", "MAI", "JUIN", "JUIL", "AOÛT", "SEP", "OCT", "NOV", "DÉC"];

export function CognitiveTimeline() {
  const { data, loading, error, isEmpty, reload } = useMatrixData<TimelinePayload>("/api/matrix/timeline");

  const monthlyChart = (data?.monthly ?? []).map((m) => ({
    month: m.month.slice(2), // YY-MM
    volume: m.volume,
    rate: m.rate !== null ? +(m.rate * 100).toFixed(2) : null,
    rolling: (() => {
      const r = data?.rolling.find((x) => x.month === m.month);
      return r?.rate !== null && r?.rate !== undefined ? +(r.rate * 100).toFixed(2) : null;
    })(),
  }));

  return (
    <div className="space-y-4">
      <ModulePanel
        code="07"
        title="Chronologie cognitive — télémétrie temporelle des décisions"
        subtitle="Volume décisionnel et taux de confirmation binaires, mois par mois, sur la fenêtre réelle du corpus"
        source="api/matrix/timeline"
        actions={<ReloadButton onClick={reload} />}
      >
        <ModuleBody
          loading={loading}
          error={error}
          isEmpty={isEmpty}
          emptyMessage="Aucune date réelle indexée."
          data={data}
        >
          {(d) => (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <KpiChip label="FENÊTRE RÉELLE" value={`${d.monthly[0]?.month ?? "—"} → ${d.monthly[d.monthly.length - 1]?.month ?? "—"}`} sub="première → dernière décision" />
                <KpiChip label="MOIS COUVERTS" value={fmtNum(d.monthly.length)} sub="mois avec au moins une décision" />
                <KpiChip
                  label="MEILLEUR MOIS CALANDAIRE"
                  value={(() => {
                    const best = [...d.monthOfYear].filter((m) => m.n >= 20).sort((a, b) => (b.rate ?? 0) - (a.rate ?? 0))[0];
                    return best ? MONTH_LABELS[best.month - 1] : "—";
                  })()}
                  tone="neg"
                  sub={(() => {
                    const best = [...d.monthOfYear].filter((m) => m.n >= 20).sort((a, b) => (b.rate ?? 0) - (a.rate ?? 0))[0];
                    return best ? `${fmtPct(best.rate)} · n=${best.n}` : "n insuffisant";
                  })()}
                />
                <KpiChip
                  label="MOIS LE PLUS CLÉMENT"
                  value={(() => {
                    const low = [...d.monthOfYear].filter((m) => m.n >= 20).sort((a, b) => (a.rate ?? 1) - (b.rate ?? 1))[0];
                    return low ? MONTH_LABELS[low.month - 1] : "—";
                  })()}
                  tone="pos"
                  sub={(() => {
                    const low = [...d.monthOfYear].filter((m) => m.n >= 20).sort((a, b) => (a.rate ?? 1) - (b.rate ?? 1))[0];
                    return low ? `${fmtPct(low.rate)} · n=${low.n}` : "n insuffisant";
                  })()}
                />
              </div>

              <div>
                <h3 className="label-caps text-muted-foreground mb-2">
                  VOLUME MENSUEL (BARRES, TOUTES OPINIONS) & TAUX DE CONFIRMATION (COURBES, BINAIRES)
                </h3>
                <div className="h-72 border border-border/70 rounded-sm p-2 bg-card">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={monthlyChart}>
                      <defs>
                        <linearGradient id="volFill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#B8B2A6" stopOpacity={0.9} />
                          <stop offset="100%" stopColor="#D8D3C8" stopOpacity={0.4} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke="#D8D3C8" strokeDasharray="2 4" />
                      <XAxis dataKey="month" stroke="#756F65" fontSize={9} tickLine={false} interval={5} />
                      <YAxis yAxisId="vol" stroke="#756F65" fontSize={10} tickLine={false} />
                      <YAxis yAxisId="rate" orientation="right" domain={[40, 100]} stroke="#756F65" fontSize={10} tickLine={false} tickFormatter={(v: number) => `${v}%`} />
                      <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#8B857733" }}
                        formatter={(v: number, name: string) => [
                          name === "volume" ? v : v !== null ? `${v.toFixed(1)} %` : "—",
                          name === "volume" ? "opinions" : name === "rate" ? "taux mensuel" : "moyenne 12 m.",
                        ]} />
                      <Legend wrapperStyle={{ fontSize: 10 }}
                        formatter={(v: string) => (v === "volume" ? "Volume" : v === "rate" ? "Taux mensuel" : "Moyenne mobile 12 m.")} />
                      <Bar yAxisId="vol" dataKey="volume" fill="url(#volFill)" isAnimationActive={false} />
                      <Line yAxisId="rate" type="monotone" dataKey="rate" stroke="#2F7D51" strokeWidth={1.5} dot={false} connectNulls isAnimationActive={false} />
                      <Line yAxisId="rate" type="monotone" dataKey="rolling" stroke="#B8863B" strokeWidth={1.5} strokeDasharray="5 3" dot={false} connectNulls isAnimationActive={false} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <div>
                  <h3 className="label-caps text-muted-foreground mb-2">
                    TAUX DE CONFIRMATION PAR MOIS CALANDAIRE (AGRÉGÉ 2015-2023)
                  </h3>
                  <div className="h-56 border border-border/70 rounded-sm p-2 bg-card">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={d.monthOfYear.map((m) => ({ ...m, label: MONTH_LABELS[m.month - 1], pct: m.rate !== null ? +(m.rate * 100).toFixed(1) : null }))}>
                        <CartesianGrid stroke="#D8D3C8" strokeDasharray="2 4" />
                        <XAxis dataKey="label" stroke="#756F65" fontSize={9} tickLine={false} />
                        <YAxis yAxisId="pct" domain={[40, 100]} stroke="#756F65" fontSize={10} tickLine={false} tickFormatter={(v: number) => `${v}%`} />
                        <YAxis yAxisId="n" orientation="right" stroke="#8B8577" fontSize={9} tickLine={false} />
                        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#8B857733" }}
                          formatter={(v: number, name: string) => [name === "pct" ? `${v} %` : v, name === "pct" ? "taux" : "n binaire"]} />
                        <Bar yAxisId="n" dataKey="n" fill="#D8D3C8" isAnimationActive={false} />
                        <Line yAxisId="pct" type="monotone" dataKey="pct" stroke="#A8433C" strokeWidth={1.5} dot={{ r: 2 }} isAnimationActive={false} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                  <p className="mono text-[9px] text-muted-foreground/70 mt-1">
                    SURVOL = n DU MOIS · barre grise = effectif (échelle implicite)
                  </p>
                </div>

                <div>
                  <h3 className="label-caps text-muted-foreground mb-2">Synthèse annuelle</h3>
                  <div className="overflow-x-auto">
                  <table className="w-full text-xs mono border border-border rounded-sm">
                    <thead className="border-b border-border/70">
                      <tr>
                        {["ANNÉE", "N BINAIRES", "CONFIRMÉS", "TAUX"].map((h) => (
                          <th key={h} className="label-caps text-muted-foreground px-3 py-2 text-left">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {d.byYear.map((y) => (
                        <tr key={y.year} className="border-b border-border/40 hover:bg-secondary/40">
                          <td className="px-3 py-1.5">{y.year}</td>
                          <td className="px-3 py-1.5">{fmtNum(y.n)}</td>
                          <td className="px-3 py-1.5">{fmtNum(y.affirmed)}</td>
                          <td className={`px-3 py-1.5 ${y.rate >= 0.7696 ? "text-neg" : "text-pos"}`}>
                            {fmtPct(y.rate)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  </div>
                </div>
              </div>
            </div>
          )}
        </ModuleBody>
      </ModulePanel>

      <MethodNote>
        Toutes les dates sont les dates de dépôt officielles des opinions (source : en-tête « Decided
        on… » / métadonnées CourtListener). L'agrégation par mois calandaire est un PROXY
        chronobiologique : la source ne contient ni l'heure de l'audience, ni l'ordre du rôle, ni la
        durée de délibération — l'interprétation en termes de « fatigue décisionnelle » resterait une
        hypothèse à tester avec des données d'audience. Les cellules avec n &lt; 20 sont signalées
        « n insuffisant » plutôt que sur-interprétées.
      </MethodNote>
    </div>
  );
}
