"use client";

/**
 * MODULE 02 — MATRICE D'ANALYSE DES ÉCARTS (Weakness Matrix).
 * Retro-engineering of decisional behavior: per-judge binary affirmance
 * rates, Wilson 95% CIs, z-scores vs corpus baseline, statistical deviation
 * flags (|z| ≥ 2 with n ≥ 30). Every figure is computed from real outcomes.
 */
import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  useMatrixData, ModulePanel, ModuleBody, ReloadButton, fmtPct, fmtSigned, fmtNum,
  deptColor, DEPT_LABELS, WilsonBar, ZBadge, KpiChip, MethodNote,
} from "./shared";
import type { JudgeMetric } from "@/lib/matrix/queries";
import { useMatrixStore } from "./store";

type SortKey = "absZ" | "nBinary" | "rate" | "name" | "volatility";

export function WeaknessMatrix() {
  const { data, loading, error, isEmpty, reload } = useMatrixData<JudgeMetric[]>("/api/matrix/judges");
  const { selectedJudge, setSelectedJudge } = useMatrixStore();
  const [minN, setMinN] = useState("30");
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("absZ");
  const [sortDir, setSortDir] = useState<1 | -1>(-1);

  const judges = (data ?? []) as JudgeMetric[];

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filtered = judges.filter(
      (j) => j.nBinary >= Number(minN) && (!q || j.name.toLowerCase().includes(q)),
    );
    const cmp: Record<SortKey, (a: JudgeMetric, b: JudgeMetric) => number> = {
      absZ: (a, b) => Math.abs(a.z) - Math.abs(b.z),
      nBinary: (a, b) => a.nBinary - b.nBinary,
      rate: (a, b) => a.rate - b.rate,
      name: (a, b) => a.name.localeCompare(b.name),
      volatility: (a, b) => a.volatility - b.volatility,
    };
    return [...filtered].sort((a, b) => cmp[sortKey](a, b) * sortDir);
  }, [judges, minN, search, sortKey, sortDir]);

  const kpis = useMemo(() => {
    const eligible = judges.filter((j) => j.nBinary >= 30);
    const up = eligible.filter((j) => j.deviatesUp);
    const down = eligible.filter((j) => j.deviatesDown);
    const most = [...eligible].sort((a, b) => Math.abs(b.z) - Math.abs(a.z))[0];
    return { eligible, up, down, most };
  }, [judges]);

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) setSortDir((d) => (d === 1 ? -1 : 1));
    else {
      setSortKey(key);
      setSortDir(-1);
    }
  };

  const Th = ({ label, k, className }: { label: string; k?: SortKey; className?: string }) => (
    <th className={`px-2 py-1.5 text-left ${className ?? ""}`}>
      {k ? (
        <button
          onClick={() => toggleSort(k)}
          className="label-caps text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
        >
          {label}
          {sortKey === k ? (
            sortDir === -1 ? <ArrowDown className="h-2.5 w-2.5" /> : <ArrowUp className="h-2.5 w-2.5" />
          ) : null}
        </button>
      ) : (
        <span className="label-caps text-muted-foreground">{label}</span>
      )}
    </th>
  );

  return (
    <div className="space-y-4">
      <ModulePanel
        code="02"
        title="MATRICE D'ANALYSE DES ÉCARTS — RÉTRO-INGÉNIERIE DÉCISIONNELLE"
        subtitle="Taux de confirmation binaires réels · IC95 Wilson · score z vs base du corpus (76,96 %)"
        source="api/matrix/judges"
        actions={
          <div className="flex items-center gap-2">
            <Select value={minN} onValueChange={setMinN}>
              <SelectTrigger className="h-7 w-32 text-[11px] border-border/70" aria-label="Nombre minimal de décisions">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {["10", "20", "30", "50", "100"].map((n) => (
                  <SelectItem key={n} value={n}>N ≥ {n}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <ReloadButton onClick={reload} />
          </div>
        }
      >
        <ModuleBody loading={loading} error={error} isEmpty={isEmpty} data={data}>
          {() => (
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <KpiChip label="JUGES ANALYSÉS (N ≥ 30)" value={fmtNum(kpis.eligible.length)} sub={`sur ${fmtNum(judges.length)} identités normalisées`} />
                <KpiChip label="ÉCARTS SIGNIFICATIFS ↑" value={fmtNum(kpis.up.length)} tone="red" sub="confirment plus que la base (z ≥ +2)" />
                <KpiChip label="ÉCARTS SIGNIFICATIFS ↓" value={fmtNum(kpis.down.length)} tone="emerald" sub="infirment plus que la base (z ≤ −2)" />
                <KpiChip
                  label="ÉCART MAXIMAL OBSERVÉ"
                  value={kpis.most ? `${fmtSigned(kpis.most.z)}σ` : "—"}
                  tone="amber"
                  sub={kpis.most ? `${kpis.most.name} · n=${kpis.most.nBinary}` : ""}
                />
              </div>

              <Input
                placeholder="FILTRER PAR NOM…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="h-8 text-xs mono max-w-xs"
                aria-label="Filtrer les juges par nom"
              />

              <div className="border border-border/70 rounded-sm overflow-x-auto max-h-[520px] overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-zinc-950/95 backdrop-blur z-10 border-b border-border/70">
                    <tr>
                      <Th label="JUGE" k="name" />
                      <Th label="DÉPT" />
                      <Th label="N BIN" k="nBinary" className="text-right" />
                      <Th label="CONFIRMÉS" className="text-right" />
                      <Th label="TAUX" k="rate" />
                      <Th label="IC95 WILSON" />
                      <Th label="Z" k="absZ" />
                      <Th label="PRÉSID." className="text-right" />
                      <Th label="VOLAT." k="volatility" />
                      <Th label="DIAGNOSTIC" />
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((j) => (
                      <tr
                        key={j.name}
                        onClick={() => setSelectedJudge(j.name === selectedJudge ? null : j.name)}
                        className={`border-b border-border/40 cursor-pointer transition-colors ${
                          j.name === selectedJudge ? "bg-primary/10" : "hover:bg-secondary/50"
                        }`}
                      >
                        <td className="px-2 py-1.5 mono whitespace-nowrap">{j.name}</td>
                        <td className="px-2 py-1.5">
                          <span className="mono text-[10px]" style={{ color: deptColor(j.dominantDepartment) }}>
                            {DEPT_LABELS[j.dominantDepartment] ?? j.dominantDepartment}
                          </span>
                        </td>
                        <td className="px-2 py-1.5 mono text-right">{fmtNum(j.nBinary)}</td>
                        <td className="px-2 py-1.5 mono text-right">{fmtNum(j.affirmed)}</td>
                        <td className="px-2 py-1.5 mono">
                          <span className={j.rate >= 0.7696 ? "text-red-400" : "text-emerald-400"}>
                            {fmtPct(j.rate)}
                          </span>
                        </td>
                        <td className="px-2 py-1.5 w-32">
                          <WilsonBar rate={j.rate} low={j.wilson95.low} high={j.wilson95.high}
                            tone={j.rate >= 0.7696 ? "red" : "emerald"} />
                        </td>
                        <td className="px-2 py-1.5"><ZBadge z={j.z} /></td>
                        <td className="px-2 py-1.5 mono text-right">{fmtNum(j.presidingCount)}</td>
                        <td className="px-2 py-1.5 mono text-right">{j.volatility.toFixed(3)}</td>
                        <td className="px-2 py-1.5">
                          {j.deviatesUp ? (
                            <span className="mono text-[9px] border border-red-400/40 bg-red-400/10 text-red-400 rounded-sm px-1 py-0.5">DÉVIE ↑</span>
                          ) : j.deviatesDown ? (
                            <span className="mono text-[9px] border border-emerald-400/40 bg-emerald-400/10 text-emerald-400 rounded-sm px-1 py-0.5">DÉVIE ↓</span>
                          ) : (
                            <span className="mono text-[9px] text-muted-foreground">conforme</span>
                          )}
                        </td>
                      </tr>
                    ))}
                    {rows.length === 0 ? (
                      <tr>
                        <td colSpan={10} className="px-2 py-6 text-center mono text-muted-foreground">
                          AUCUN JUGE NE CORRESPOND AU FILTRE — les filtres s'appliquent aux données réelles uniquement.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </ModuleBody>
      </ModulePanel>

      <MethodNote>
        Population : appels criminels binaires (confirmé vs infirmé/annulé, n = 1 111) extraits des
        opinions officielles par le pipeline validé Phase 2. Chaque taux de confirmation est assorti
        d'un intervalle de confiance de Wilson à 95 %. Le score z mesure l'écart à la base du corpus
        (855/1 111 = 76,96 %) ; le drapeau DÉVIE exige |z| ≥ 2 ET n ≥ 30 (seuil de significativité
        statistique, pas d'heuristique). La « vulnérabilité » d'une stratégie d'appel devant un juge
        donné se lit comme l'écart mesuré entre son taux observé et la base — jamais comme une
        prédiction déterministe. Volatilité = écart-type des taux annuels (années avec n ≥ 5).
      </MethodNote>
    </div>
  );
}
