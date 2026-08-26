"use client";

/**
 * MODULE 04 — SIMULATEUR DE VERDICT MONTE-CARLO.
 * Nonparametric bootstrap (10k default) over the REAL binary outcomes of a
 * user-selected filter. Seeded (FNV-1a of the filter) => reproducible.
 * Refuses to run on an empty sample — no invented distribution.
 */
import { useMemo, useState } from "react";
import {
  Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  useMatrixData, ModulePanel, ModuleBody, ReloadButton, fmtPct, fmtNum,
  KpiChip, MethodNote, TerminalLoader, ErrorState,
} from "./shared";
import type { JudgeMetric } from "@/lib/matrix/queries";

interface McPayload {
  empty: boolean;
  message?: string;
  filter: Record<string, unknown>;
  sampleSize: number;
  affirmed: number;
  observed: number;
  mean: number;
  median: number;
  p05: number; p25: number; p75: number; p95: number;
  histogram: { binStart: number; binEnd: number; count: number }[];
  baseline: { n: number; rate: number };
  iterations: number;
}

const YEARS = ["2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023"];

export function MonteCarlo() {
  const judges = useMatrixData<JudgeMetric[]>("/api/matrix/judges");
  const [department, setDepartment] = useState("all");
  const [judge, setJudge] = useState("all");
  const [yearFrom, setYearFrom] = useState("2015");
  const [yearTo, setYearTo] = useState("2023");
  const [chargeLike, setChargeLike] = useState("");
  const [iterations, setIterations] = useState("10000");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<McPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  const judgeOptions = useMemo(() => {
    const arr = (judges.data ?? []) as JudgeMetric[];
    return [...arr].filter((j) => j.nBinary >= 10).sort((a, b) => a.name.localeCompare(b.name));
  }, [judges.data]);

  const runSimulation = async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch("/api/matrix/monte-carlo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          department: department === "all" ? undefined : department,
          judge: judge === "all" ? undefined : judge,
          yearFrom: Number(yearFrom),
          yearTo: Number(yearTo),
          chargeLike: chargeLike.trim() || undefined,
          iterations: Number(iterations),
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.message ?? `HTTP ${res.status}`);
      setResult(json as McPayload);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  };

  const chartData = useMemo(() => {
    if (!result?.histogram) return [];
    return result.histogram.map((h) => ({
      x: h.binStart,
      x2: h.binEnd,
      mid: (h.binStart + h.binEnd) / 2,
      count: h.count,
    }));
  }, [result]);

  return (
    <div className="space-y-4">
      <ModulePanel
        code="04"
        title="SIMULATEUR DE VERDICT — PROJECTION MONTE-CARLO"
        subtitle="Bootstrap non paramétrique sur les issues binaires réelles de la sous-population filtrée"
        source="api/matrix/monte-carlo"
        actions={<ReloadButton onClick={judges.reload} />}
      >
        <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
          <div className="space-y-3">
            <div>
              <label className="label-caps text-muted-foreground block mb-1" htmlFor="mc-dept">DÉPARTEMENT</label>
              <Select value={department} onValueChange={setDepartment}>
                <SelectTrigger id="mc-dept" className="h-8 text-xs mono border-border/70">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">TOUS</SelectItem>
                  {["1st", "2nd", "3rd", "4th"].map((d) => (
                    <SelectItem key={d} value={d}>{d} DÉPARTEMENT</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="label-caps text-muted-foreground block mb-1" htmlFor="mc-judge">JUGE (PANEL)</label>
              <Select value={judge} onValueChange={setJudge}>
                <SelectTrigger id="mc-judge" className="h-8 text-xs mono border-border/70">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="max-h-72">
                  <SelectItem value="all">TOUS</SelectItem>
                  {judgeOptions.map((j) => (
                    <SelectItem key={j.name} value={j.name}>
                      {j.name} (n={j.nBinary})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label-caps text-muted-foreground block mb-1" htmlFor="mc-from">ANNÉE DÉBUT</label>
                <Select value={yearFrom} onValueChange={setYearFrom}>
                  <SelectTrigger id="mc-from" className="h-8 text-xs mono border-border/70"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {YEARS.map((y) => <SelectItem key={y} value={y}>{y}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="label-caps text-muted-foreground block mb-1" htmlFor="mc-to">ANNÉE FIN</label>
                <Select value={yearTo} onValueChange={setYearTo}>
                  <SelectTrigger id="mc-to" className="h-8 text-xs mono border-border/70"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {YEARS.map((y) => <SelectItem key={y} value={y}>{y}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <label className="label-caps text-muted-foreground block mb-1" htmlFor="mc-charge">MOT-CLÉ D'ACCUSATION (EX. « weapon »)</label>
              <Input
                id="mc-charge"
                placeholder="FACULTATIF…"
                value={chargeLike}
                onChange={(e) => setChargeLike(e.target.value)}
                className="h-8 text-xs mono"
              />
            </div>
            <div>
              <label className="label-caps text-muted-foreground block mb-1" htmlFor="mc-iter">ITÉRATIONS</label>
              <Select value={iterations} onValueChange={setIterations}>
                <SelectTrigger id="mc-iter" className="h-8 text-xs mono border-border/70"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {["5000", "10000", "20000", "50000"].map((i) => <SelectItem key={i} value={i}>{Number(i).toLocaleString("fr-FR")}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <Button
              onClick={runSimulation}
              disabled={running}
              className="w-full h-9 label-caps gap-2 bg-primary/15 border border-primary/40 text-primary hover:bg-primary/25"
            >
              <Play className="h-3.5 w-3.5" aria-hidden />
              {running ? "SIMULATION EN COURS…" : "EXÉCUTER LA SIMULATION"}
            </Button>
            <p className="mono text-[9px] text-muted-foreground/70 leading-relaxed">
              La simulation s'exécute uniquement sur les affaires binaires réelles correspondant au
              filtre. Échantillon vide = refus d'exécution.
            </p>
          </div>

          <div className="min-w-0">
            {running ? (
              <TerminalLoader label="RÉ-ÉCHANTILLONNAGE DES ISSUES RÉELLES" />
            ) : error ? (
              <ErrorState message={error} />
            ) : result?.empty ? (
              <div className="flex items-center justify-center h-full">
                <div className="max-w-md text-center space-y-2 border border-dashed border-border rounded-sm p-8">
                  <p className="label-caps text-amber-400">AUCUN ÉCHANTILLON RÉEL</p>
                  <p className="text-xs text-muted-foreground">{result.message}</p>
                </div>
              </div>
            ) : result ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <KpiChip label="ÉCHANTILLON RÉEL" value={fmtNum(result.sampleSize)} sub={`${fmtNum(result.affirmed)} confirmés`} />
                  <KpiChip label="TAUX OBSERVÉ" value={fmtPct(result.observed)} tone="emerald" sub="dans l'échantillon filtré" />
                  <KpiChip label="BASE CORPUS" value={fmtPct(result.baseline.rate)} tone="amber" sub={`n = ${fmtNum(result.baseline.n)}`} />
                  <KpiChip label="MÉDIANE BOOTSTRAP" value={fmtPct(result.median)} sub={`moyenne ${fmtPct(result.mean)}`} />
                </div>

                <div className="h-64 border border-border/70 rounded-sm p-2 bg-zinc-950/40">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 8, right: 12, bottom: 4, left: -12 }}>
                      <defs>
                        <linearGradient id="mcFill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#34d399" stopOpacity={0.5} />
                          <stop offset="100%" stopColor="#34d399" stopOpacity={0.04} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke="#27272a" strokeDasharray="2 4" />
                      <XAxis
                        dataKey="mid"
                        type="number"
                        domain={[0, 1]}
                        tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                        stroke="#71717a"
                        fontSize={10}
                        tickLine={false}
                      />
                      <YAxis stroke="#71717a" fontSize={10} tickLine={false} />
                      <Tooltip
                        contentStyle={{
                          background: "#09090b", border: "1px solid #27272a",
                          borderRadius: 2, fontSize: 11, fontFamily: "var(--font-geist-mono)",
                        }}
                        labelFormatter={(v: number) => `Taux ≈ ${(v * 100).toFixed(1)} %`}
                        formatter={(value: number) => [`${value} simulations`, "fréquence"]}
                      />
                      <ReferenceLine x={result.observed} stroke="#34d399" strokeWidth={1.5}
                        label={{ value: "OBSERVÉ", fill: "#34d399", fontSize: 9, position: "insideTopLeft" }} />
                      <ReferenceLine x={result.baseline.rate} stroke="#fbbf24" strokeDasharray="4 3" strokeWidth={1.2}
                        label={{ value: "BASE", fill: "#fbbf24", fontSize: 9, position: "insideBottomLeft" }} />
                      <ReferenceLine x={result.p05} stroke="#52525b" strokeDasharray="2 3" />
                      <ReferenceLine x={result.p95} stroke="#52525b" strokeDasharray="2 3" />
                      <Area type="monotone" dataKey="count" stroke="#34d399" strokeWidth={1.5} fill="url(#mcFill)" isAnimationActive={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                  {[
                    ["P05", result.p05], ["P25", result.p25],
                    ["MÉDIANE", result.median], ["P75", result.p75], ["P95", result.p95],
                  ].map(([label, v]) => (
                    <div key={label as string} className="panel rounded-sm px-2.5 py-1.5">
                      <div className="label-caps text-muted-foreground">{label as string}</div>
                      <div className="mono text-sm text-foreground">{fmtPct(v as number)}</div>
                    </div>
                  ))}
                </div>

                <MethodNote>
                  {`${fmtNum(result.iterations)} ré-échantillonnages avec remise des ${fmtNum(result.sampleSize)} issues binaires réelles du filtre. Graine = hache FNV-1a du filtre (mulberry32) — exécutez deux fois le même filtre, la distribution sera identique. Lignes grises = percentiles 5/95.`}
                </MethodNote>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full min-h-64">
                <div className="max-w-md text-center space-y-2">
                  <p className="label-caps text-muted-foreground">SIMULATEUR ARMÉ</p>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Configurez la sous-population puis exécutez. Le moteur ré-échantillonne
                    uniquement les issues réellement observées — la probabilité affichée est une
                    inférence statistique sur données authentiques, pas une prédiction.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </ModulePanel>
    </div>
  );
}
