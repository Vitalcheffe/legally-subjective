"use client";

/**
 * MODULE 03 — CARTE THERMIQUE DES BIAIS.
 * Matrix of REAL affirmance rates by (department × year) and (judge × year),
 * colored by deviation from that year's corpus baseline. Anomalies (|z| ≥ 2,
 * n ≥ 20) are outlined — they are measured, not guessed.
 */
import { useMemo, useState } from "react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useMatrixData, ModulePanel, ModuleBody, ReloadButton, fmtPct, fmtNum,
  DEPT_LABELS, deptColor, MethodNote,
} from "./shared";
import type { JudgeMetric } from "@/lib/matrix/queries";

interface HeatmapPayload {
  empty: boolean;
  departments: string[];
  years: string[];
  deptYear: { rowKey: string; cells: { colKey: string; n: number; affirmed: number; rate: number | null }[] }[];
  byYear: { year: number; n: number; affirmed: number; rate: number }[];
  binaryN: number;
}

function cellColor(rate: number | null, baseline: number): { bg: string; border: string } {
  if (rate === null) return { bg: "transparent", border: "transparent" };
  const d = rate - baseline; // -1..1
  const intensity = Math.min(1, Math.abs(d) / 0.25);
  const alpha = 0.08 + intensity * 0.55;
  const color = d > 0 ? `rgba(248, 113, 113, ${alpha})` : `rgba(52, 211, 153, ${alpha})`;
  return { bg: color, border: "rgba(255,255,255,0.06)" };
}

export function BiasHeatmap() {
  const heat = useMatrixData<HeatmapPayload>("/api/matrix/heatmap");
  const judges = useMatrixData<JudgeMetric[]>("/api/matrix/judges");
  const [view, setView] = useState<"dept" | "judge">("dept");

  const yearBaseline = useMemo(() => {
    const m = new Map<number, number>();
    heat.data?.byYear?.forEach((y) => m.set(y.year, y.rate));
    return m;
  }, [heat.data]);

  const topJudges = useMemo(() => {
    const arr = (judges.data ?? []) as JudgeMetric[];
    return [...arr].sort((a, b) => b.nBinary - a.nBinary).slice(0, 24);
  }, [judges.data]);

  return (
    <div className="space-y-4">
      <ModulePanel
        code="03"
        title="Carte thermique des biais — déviations à la base annuelle"
        subtitle="Taux de confirmation binaires réels · rouge = au-dessus de la base annuelle · vert = en-dessous"
        source="api/matrix/heatmap"
        actions={
          <div className="flex items-center gap-2">
            <Tabs value={view} onValueChange={(v) => setView(v as "dept" | "judge")}>
              <TabsList className="h-7">
                <TabsTrigger value="dept" className="text-[10px] h-6">DÉPT × ANNÉE</TabsTrigger>
                <TabsTrigger value="judge" className="text-[10px] h-6">JUGE × ANNÉE</TabsTrigger>
              </TabsList>
            </Tabs>
            <ReloadButton onClick={heat.reload} />
          </div>
        }
      >
        <ModuleBody
          loading={heat.loading}
          error={heat.error}
          isEmpty={heat.isEmpty}
          emptyMessage="Aucune donnée thermique — index réel vide."
          data={heat.data}
        >
          {(d) => (
            <div className="overflow-x-auto">
              {view === "dept" ? (
                <table className="border-collapse text-[11px] mono">
                  <thead>
                    <tr>
                      <th className="label-caps text-muted-foreground px-2 py-1.5 text-left">DÉPARTEMENT</th>
                      {d.years.map((y) => (
                        <th key={y} className="label-caps text-muted-foreground px-2 py-1.5">{y}</th>
                      ))}
                      <th className="label-caps text-muted-foreground px-2 py-1.5">TOTAL</th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.deptYear.map((row) => (
                      <tr key={row.rowKey}>
                        <td className="px-2 py-1.5 whitespace-nowrap" style={{ color: deptColor(row.rowKey) }}>
                          {DEPT_LABELS[row.rowKey] ?? row.rowKey}
                        </td>
                        {row.cells.map((c) => {
                          const base = yearBaseline.get(Number(c.colKey)) ?? 0;
                          const z = c.n > 0 ? (c.rate! - base) / Math.sqrt((base * (1 - base)) / c.n) : 0;
                          const anomaly = c.n >= 20 && Math.abs(z) >= 2;
                          const { bg, border } = cellColor(c.rate, base);
                          return (
                            <td
                              key={c.colKey}
                              className="px-2 py-1.5 text-center border"
                              style={{
                                background: bg,
                                borderColor: border,
                                boxShadow: anomaly ? "inset 0 0 0 1.5px rgba(251, 191, 36, 0.9)" : undefined,
                                minWidth: 64,
                              }}
                              title={`n = ${c.n} · confirmés = ${c.affirmed} · taux = ${fmtPct(c.rate)} · base ${c.colKey} = ${fmtPct(base)} · z = ${z.toFixed(2)}${anomaly ? " ⚠ ANOMALIE (|z| ≥ 2)" : ""}`}
                            >
                              {c.rate === null ? (
                                <span className="text-muted-foreground/50">—</span>
                              ) : (
                                <span className={c.rate >= base ? "text-neg" : "text-pos"}>
                                  {(c.rate * 100).toFixed(0)}
                                </span>
                              )}
                            </td>
                          );
                        })}
                        <td className="px-2 py-1.5 text-center text-muted-foreground">
                          {fmtNum(row.cells.reduce((a, b) => a + b.n, 0))}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="overflow-x-auto">
                <table className="border-collapse text-[11px] mono">
                  <thead>
                    <tr>
                      <th className="label-caps text-muted-foreground px-2 py-1.5 text-left sticky left-0 bg-card">JUGE</th>
                      {d.years.map((y) => (
                        <th key={y} className="label-caps text-muted-foreground px-2 py-1.5">{y}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {topJudges.map((j) => (
                      <tr key={j.name}>
                        <td className="px-2 py-1.5 whitespace-nowrap sticky left-0 bg-card">{j.name}</td>
                        {d.years.map((y) => {
                          const cell = j.yearlyRates.find((r) => r.year === Number(y));
                          const base = yearBaseline.get(Number(y)) ?? 0;
                          const rate = cell && cell.n > 0 ? cell.rate : null;
                          const z = cell && cell.n > 0 ? (cell.rate - base) / Math.sqrt((base * (1 - base)) / cell.n) : 0;
                          const anomaly = cell && cell.n >= 20 && Math.abs(z) >= 2;
                          const { bg, border } = cellColor(rate, base);
                          return (
                            <td
                              key={y}
                              className="px-2 py-1.5 text-center border"
                              style={{
                                background: bg,
                                borderColor: border,
                                boxShadow: anomaly ? "inset 0 0 0 1.5px rgba(251, 191, 36, 0.9)" : undefined,
                                minWidth: 52,
                              }}
                              title={cell ? `n = ${cell.n} · taux = ${fmtPct(cell.rate)} · base ${y} = ${fmtPct(base)} · z = ${z.toFixed(2)}` : "aucune décision binaire"}
                            >
                              {rate === null ? (
                                <span className="text-muted-foreground/50">—</span>
                              ) : (
                                <span className={rate >= base ? "text-neg" : "text-pos"}>
                                  {(rate * 100).toFixed(0)}
                                </span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              )}

              <div className="flex flex-wrap items-center gap-x-5 gap-y-1 mt-4">
                <span className="label-caps text-muted-foreground">Échelle</span>
                <span className="mono text-[10px] text-pos">■■■ −25 pts sous la base</span>
                <span className="mono text-[10px] text-muted-foreground">■ Conforme</span>
                <span className="mono text-[10px] text-neg">■■■ +25 pts au-dessus</span>
                <span className="mono text-[10px] text-mix">▢ contour ambre = anomalie |z| ≥ 2 (n ≥ 20)</span>
                <span className="mono text-[10px] text-muted-foreground/80">Survol = détail complet de la cellule</span>
              </div>
            </div>
          )}
        </ModuleBody>
      </ModulePanel>

      <MethodNote>
        Chaque cellule affiche le taux de confirmation binaire réel pour la sous-population
        (département ou juge) × année. La couleur encode l'écart à la base ANNUELLE du corpus (et
        non la base globale) afin de neutraliser la dérive temporelle. Le contour ambre signale les
        anomalies statistiques (|z| ≥ 2 avec n ≥ 20) — une mesure d'écart à la norme, pas un
        jugement de valeur : une anomalie peut refléter la composition du portefeuille d'affaires
        (type de crime, département, année) autant que le comportement du juge.
      </MethodNote>
    </div>
  );
}
