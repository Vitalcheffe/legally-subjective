"use client";

/**
 * MODULE 00 — SYNOPTIQUE DE MISSION.
 * Global real-data overview: corpus status, binary base rate with Wilson CI,
 * disposition distribution, department split. Gateway to the 9 modules.
 */
import { ArrowRight } from "lucide-react";
import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import {
  useMatrixData, ModulePanel, ModuleBody, ReloadButton, fmtPct, fmtNum,
  KpiChip, MethodNote, deptColor, DEPT_LABELS, WilsonBar,
} from "./shared";
import { useMatrixStore } from "./store";

interface OverviewPayload {
  empty: boolean;
  corpus: {
    records: number; firstDate: string; lastDate: string; years: number[];
    peopleV: number; other: number; withText: number;
  };
  binary: { n: number; affirmed: number; reversedVacated: number; rate: number; wilson95: { low: number; high: number } };
  dispositions: { key: string; count: number; share: number; wilson95: { low: number; high: number } }[];
  departments: { dept: string; n: number; affirmed: number; rate: number; wilson95: { low: number; high: number } }[];
  judges: number; seats: number; citedTargets: number; citedMentions: number;
}

const DISPO_COLORS: Record<string, string> = {
  affirmed: "#2F7D51", reversed: "#A8433C", modified: "#B8863B",
  vacated: "#8C6D3F", dismissed: "#9A948A", remitted: "#C4BFB5",
  "non classé": "#8B8577",
};

const MODULE_LINKS: { code: string; label: string; module: string }[] = [
  { code: "01", label: "Carte neuro-cognitive", module: "neural" },
  { code: "02", label: "Matrice des écarts", module: "weakness" },
  { code: "03", label: "Carte thermique des biais", module: "heatmap" },
  { code: "04", label: "Simulateur Monte-Carlo", module: "montecarlo" },
  { code: "05", label: "Spectre stylométrique", module: "stylometry" },
  { code: "06", label: "Graphe de jurisprudence", module: "precedent" },
  { code: "07", label: "Chronologie cognitive", module: "timeline" },
  { code: "08", label: "Radar de déviation", module: "radar" },
  { code: "09", label: "Arbitrage humain contre IA", module: "shield" },
];

export function OverviewPanel() {
  const { data, loading, error, isEmpty, reload } = useMatrixData<OverviewPayload>("/api/matrix/overview");
  const setModule = useMatrixStore((s) => s.setModule);

  return (
    <div className="space-y-4">
      <ModulePanel
        code="00"
        title="Synoptique — état du corpus réel"
        subtitle="Appels criminels NY Appellate Division · collecte CourtListener + documents officiels · pipeline validé Phase 2"
        source="api/matrix/overview"
        actions={<ReloadButton onClick={reload} />}
      >
        <ModuleBody
          loading={loading}
          error={error}
          isEmpty={isEmpty}
          emptyMessage="Index réel vide. Lancez l'ingestion : bun scripts/ingest.ts — aucune donnée de substitution n'existe dans ce système."
          data={data}
        >
          {(d) => (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
                <KpiChip label="DOSSIERS RÉELS" value={fmtNum(d.corpus.records)} sub={`${d.corpus.firstDate} → ${d.corpus.lastDate}`} />
                <KpiChip label="TAUX DE CONFIRMATION" value={fmtPct(d.binary.rate)} tone="pos" sub={`IC95 [${fmtPct(d.binary.wilson95.low)} ; ${fmtPct(d.binary.wilson95.high)}]`} />
                <KpiChip label="ANNULATIONS/INFIRM." value={fmtPct(1 - d.binary.rate)} tone="neg" sub={`n binaire = ${fmtNum(d.binary.n)}`} />
                <KpiChip label="JUGES NORMALISÉS" value={fmtNum(d.judges)} sub={`${fmtNum(d.seats)} liens de panel`} />
                <KpiChip label="AUTORITÉS CITÉES" value={fmtNum(d.citedTargets)} sub={`${fmtNum(d.citedMentions)} mentions extraites`} />
                <KpiChip label="TEXTES INDEXÉS" value={`${fmtNum(d.corpus.withText)}/${fmtNum(d.corpus.records)}`} tone="mix" sub="opinions officielles complètes" />
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <div>
                  <h3 className="label-caps text-muted-foreground mb-2">Distribution des dispositions (toutes opinions)</h3>
                  <div className="h-56 border border-border/70 rounded-sm p-2 bg-card">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={d.dispositions.map((x) => ({ ...x, label: x.key === "non_classé" ? "non classé" : x.key }))} layout="vertical">
                        <CartesianGrid stroke="#D8D3C8" strokeDasharray="2 4" horizontal={false} />
                        <XAxis type="number" stroke="#756F65" fontSize={10} tickLine={false} />
                        <YAxis type="category" dataKey="label" stroke="#756F65" fontSize={10} tickLine={false} width={80} />
                        <Tooltip
                          contentStyle={{ background: "#FFFFFF", border: "1px solid #D8D3C8", borderRadius: 2, fontSize: 11, fontFamily: "var(--font-geist-mono)" }}
                          cursor={{ fill: "#8B857733" }}
                          formatter={(v: number, _n, p) => [`${v} (${fmtPct(p.payload.share)})`, "opinions"]}
                        />
                        <Bar dataKey="count" isAnimationActive={false}>
                          {d.dispositions.map((x) => (
                            <Cell key={x.key} fill={DISPO_COLORS[x.key] ?? "#756F65"} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div>
                  <h3 className="label-caps text-muted-foreground mb-2">Segmentation par département (binaires)</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs mono border border-border rounded-sm min-w-[420px]">
                    <thead className="border-b border-border/70">
                      <tr>
                        {["DÉPARTEMENT", "N", "CONFIRMÉS", "TAUX", "IC95 WILSON"].map((h) => (
                          <th key={h} className="label-caps text-muted-foreground px-3 py-2 text-left">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {d.departments.map((dept) => (
                        <tr key={dept.dept} className="border-b border-border/40 hover:bg-secondary/40">
                          <td className="px-3 py-2" style={{ color: deptColor(dept.dept) }}>
                            {DEPT_LABELS[dept.dept] ?? dept.dept}
                          </td>
                          <td className="px-3 py-2">{fmtNum(dept.n)}</td>
                          <td className="px-3 py-2">{fmtNum(dept.affirmed)}</td>
                          <td className={`px-3 py-2 ${dept.rate >= 0.7696 ? "text-neg" : "text-pos"}`}>{fmtPct(dept.rate)}</td>
                          <td className="px-3 py-2 w-36">
                            <WilsonBar rate={dept.rate} low={dept.wilson95.low} high={dept.wilson95.high} tone={dept.rate >= 0.7696 ? "neg" : "pos"} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  </div>
                  <p className="mono text-[9px] text-muted-foreground/70 mt-2">
                    Population : {fmtNum(d.corpus.peopleV)} « People v. … » · {fmtNum(d.corpus.other)} autres (Matter of …, etc.)
                  </p>
                </div>
              </div>

              <div>
                <h3 className="label-caps text-muted-foreground mb-2">Accès modules</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {MODULE_LINKS.map((m) => (
                    <button
                      key={m.module}
                      onClick={() => setModule(m.module)}
                      className="group flex items-center justify-between gap-2 panel rounded-sm px-3 py-2.5 text-left hover:border-primary/40 transition-colors"
                    >
                      <span className="flex items-center gap-2.5 min-w-0">
                        <span className="mono text-[10px] text-primary/80 border border-primary/30 rounded-sm px-1 py-0.5 bg-primary/5">{m.code}</span>
                        <span className="mono text-[11px] text-foreground/90 truncate">{m.label}</span>
                      </span>
                      <ArrowRight className="h-3.5 w-3.5 text-muted-foreground group-hover:text-primary shrink-0" aria-hidden />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </ModuleBody>
      </ModulePanel>

      <MethodNote>
        Tout chiffre de cette console dérive exclusivement de l'index SQLite ingéré depuis le corpus
        Phase 2 (1 387 appels criminels réels, extraits des documents officiels, validation croisée
        automatique contre data/analysis/base_rate_corpus.json à chaque ingestion). Le contrat
        zéro-mock est structurel : aucune valeur n'est codée en dur, aucun générateur aléatoire
        n'alimente les graphiques (le seul aléa est le bootstrap Monte-Carlo seedé du module 04,
        appliqué aux issues réelles), et tout flux manquant produit un état d'attente explicite.
      </MethodNote>
    </div>
  );
}
