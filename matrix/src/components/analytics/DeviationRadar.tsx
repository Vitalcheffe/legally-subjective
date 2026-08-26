"use client";

/**
 * MODULE 08 — RADAR DE DÉVIATION COMPORTEMENTALE.
 * 6-axis behavioral shape of a judge, each axis = percentile rank among
 * eligible judges (n binary ≥ 30), vs the corpus median. All metrics real.
 */
import { useMemo } from "react";
import {
  CartesianGrid, PolarAngleAxis, PolarGrid, PolarRadiusAxis,
  Radar, RadarChart, ResponsiveContainer, Tooltip,
} from "recharts";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  useMatrixData, ModulePanel, ModuleBody, ReloadButton, fmtPct, fmtSigned, fmtNum,
  KpiChip, MethodNote, WilsonBar, ZBadge, deptColor, DEPT_LABELS,
} from "./shared";
import { useMatrixStore } from "./store";

interface RadarPayload {
  empty: boolean;
  judge: {
    name: string; nBinary: number; nOpinions: number; rate: number; z: number;
    wilson95: { low: number; high: number }; presidingCount: number;
    dominantDepartment: string; yearSpan: [number, number] | null; volatility: number;
  };
  axes: { axis: string; percentile: number; value: number; median: number }[];
  eligibleJudges: { name: string; nBinary: number; rate: number; z: number }[];
  nEligible: number;
  methodNote: string;
}

export function DeviationRadar() {
  const { selectedJudge, setSelectedJudge } = useMatrixStore();
  const url = `/api/matrix/radar${selectedJudge ? `?judge=${encodeURIComponent(selectedJudge)}` : ""}`;
  const { data, loading, error, isEmpty, reload } = useMatrixData<RadarPayload>(url);

  const chartData = useMemo(
    () =>
      (data?.axes ?? []).map((a) => ({
        axis: a.axis.split(" (")[0],
        juge: a.percentile,
        mediane: 50,
      })),
    [data],
  );

  return (
    <div className="space-y-4">
      <ModulePanel
        code="08"
        title="Radar de déviation comportementale — forme décisionnelle"
        subtitle="Percentiles calculés parmi les juges éligibles (n binaire ≥ 30) · superposition médiane corpus"
        source="api/matrix/radar"
        actions={
          <div className="flex items-center gap-2">
            {data && !data.empty ? (
              <Select
                value={data.judge.name}
                onValueChange={(v) => setSelectedJudge(v)}
              >
                <SelectTrigger className="h-7 w-48 text-[11px] border-border/70" aria-label="Sélection du juge">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="max-h-72">
                  {data.eligibleJudges.map((j) => (
                    <SelectItem key={j.name} value={j.name}>
                      {j.name} (n={j.nBinary})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : null}
            <ReloadButton onClick={reload} />
          </div>
        }
      >
        <ModuleBody
          loading={loading}
          error={error}
          isEmpty={isEmpty}
          emptyMessage="Aucun juge éligible (n binaire ≥ 30) dans l'index réel."
          data={data}
        >
          {(d) => (
            <div className="grid grid-cols-1 xl:grid-cols-[1fr_1fr] gap-6">
              <div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                  <KpiChip label="CIBLE" value={d.judge.name} sub={`${fmtNum(d.judge.nOpinions)} opinions · ${DEPT_LABELS[d.judge.dominantDepartment] ?? d.judge.dominantDepartment}`} />
                  <KpiChip label="TAUX CONFIRMATION" value={fmtPct(d.judge.rate)} tone="pos" sub={`n = ${fmtNum(d.judge.nBinary)} binaires`} />
                  <KpiChip label="ÉCART Z" value={<><ZBadge z={d.judge.z} /></>} sub="vs base corpus 76,96 %" />
                  <KpiChip label="PRÉSIDENCES" value={fmtNum(d.judge.presidingCount)} tone="mix" sub={d.judge.yearSpan ? `${d.judge.yearSpan[0]}–${d.judge.yearSpan[1]}` : "—"} />
                </div>

                <div className="h-80 border border-border/70 rounded-sm p-2 bg-card">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart data={chartData} outerRadius="72%">
                      <PolarGrid stroke="#D8D3C8" />
                      <PolarAngleAxis dataKey="axis" tick={{ fill: "#9A948A", fontSize: 9 }} />
                      <PolarRadiusAxis domain={[0, 100]} tick={{ fill: "#8B8577", fontSize: 8 }} angle={90} />
                      <Radar name="Médiane corpus" dataKey="mediane" stroke="#756F65" fill="#756F65" fillOpacity={0.08} strokeWidth={1} isAnimationActive={false} />
                      <Radar name="Juge" dataKey="juge" stroke="#2F7D51" fill="#2F7D51" fillOpacity={0.22} strokeWidth={1.8} isAnimationActive={false} />
                      <Tooltip
                        contentStyle={{
                          background: "#FFFFFF", border: "1px solid #D8D3C8",
                          borderRadius: 2, fontSize: 11, fontFamily: "var(--font-geist-mono)",
                        }}
                        formatter={(v: number, name: string) => [name === "juge" ? `P${v.toFixed(1)}` : v, name === "juge" ? "juge" : "médiane"]}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex items-center gap-4 mt-2">
                  <span className="mono text-[10px] text-pos">■ JUGE (PERCENTILE)</span>
                  <span className="mono text-[10px] text-muted-foreground">■ MÉDIANE DU CORPUS (P50)</span>
                  <span className="mono text-[10px] text-muted-foreground/70">ÉCHELLE 0-100 = PERCENTILE</span>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <div className="label-caps text-muted-foreground mb-1">IC95 WILSON — TAUX DE CONFIRMATION DE LA CIBLE</div>
                  <WilsonBar rate={d.judge.rate} low={d.judge.wilson95.low} high={d.judge.wilson95.high} />
                  <div className="mono text-[9px] text-muted-foreground mt-1">
                    [{fmtPct(d.judge.wilson95.low)} ; {fmtPct(d.judge.wilson95.high)}] · volatilité interannuelle {d.judge.volatility.toFixed(3)}
                  </div>
                </div>

                <div className="overflow-x-auto">
                <table className="w-full text-xs mono border border-border rounded-sm">
                  <thead className="border-b border-border/70">
                    <tr>
                      {["AXE", "VALEUR", "MÉDIANE", "PERCENTILE"].map((h) => (
                        <th key={h} className="label-caps text-muted-foreground px-2.5 py-2 text-left">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {d.axes.map((a, i) => (
                      <tr key={a.axis} className="border-b border-border/40 hover:bg-secondary/40">
                        <td className="px-2.5 py-1.5">{a.axis}</td>
                        <td className="px-2.5 py-1.5 text-foreground">{a.value}</td>
                        <td className="px-2.5 py-1.5 text-muted-foreground">{a.median}</td>
                        <td className="px-2.5 py-1.5">
                          <span className={a.percentile >= 75 ? "text-neg" : a.percentile <= 25 ? "text-pos" : "text-foreground"}>
                            P{a.percentile.toFixed(1)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>

                <p className="mono text-[10px] text-muted-foreground">
                  {fmtNum(d.nEligible)} juges éligibles dans la population de comparaison.
                </p>
              </div>
            </div>
          )}
        </ModuleBody>
      </ModulePanel>

      <MethodNote>
        {data && !data.empty ? data.methodNote : "Percentiles parmi les juges éligibles (n binaire ≥ 30)."}{" "}
        Sévérité = taux de confirmation binaire ; volume = opinions siégées ; volatilité = écart-type
        des taux annuels ; diversité = nombre de co-juges distincts ; intensité de citation =
        mentions d'autorités par opinion ; présidence = part des décisions présidées. La forme du
        radar est une DESCRIPTION statistique du comportement observé — elle ne prédit pas une
        décision future et n'établit pas de diagnostic psychologique individuel.
      </MethodNote>
    </div>
  );
}
