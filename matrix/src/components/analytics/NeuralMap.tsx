"use client";

/**
 * MODULE 01 — CARTE NEURO-COGNITIVE (WebGL).
 * Nodes = real panel judges; node size = decisional volume; color = z-score
 * of the judge's affirmance rate vs the corpus baseline (or department).
 * Edges = real co-panel links (judges who sat together), weight ≥ filter.
 */
import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useMatrixData, ModulePanel, ModuleBody, ReloadButton, fmtPct, fmtSigned, fmtNum,
  deptColor, DEPT_LABELS, WilsonBar, MethodNote, EmptyState } from "./shared";
import type { JudgeMetric } from "@/lib/matrix/queries";
import { useMatrixStore } from "./store";

const ForceGraph3D = dynamic(() => import("./ForceGraph3D"), { ssr: false });

interface NetworkPayload {
  empty: boolean;
  nodes: {
    id: number; name: string; volume: number; binaryN: number;
    rate: number | null; z: number; dominantDepartment: string;
  }[];
  edges: { source: number; target: number; weight: number }[];
  totalPairs: number;
}

/** z in [-3, +3] → forest (infirme plus) … warm gray … carmine (confirme plus). */
function zColor(z: number): string {
  const t = Math.max(-3, Math.min(3, z)) / 3; // -1..1
  if (t >= 0) {
    // warm gray → carmine
    const a = [0x8b, 0x85, 0x77], b = [0xa8, 0x43, 0x3c];
    const mix = a.map((v, i) => Math.round(v + (b[i] - v) * t));
    return `rgb(${mix[0]},${mix[1]},${mix[2]})`;
  }
  const a = [0x8b, 0x85, 0x77], b = [0x2f, 0x7d, 0x51];
  const mix = a.map((v, i) => Math.round(v + (b[i] - v) * -t));
  return `rgb(${mix[0]},${mix[1]},${mix[2]})`;
}

export function NeuralMap() {
  const { selectedJudge, setSelectedJudge } = useMatrixStore();
  const [minWeight, setMinWeight] = useState("8");
  const [colorMode, setColorMode] = useState<"z" | "dept">("z");
  const [search, setSearch] = useState("");
  const network = useMatrixData<NetworkPayload>(`/api/matrix/network?minWeight=${minWeight}`);
  const judges = useMatrixData<JudgeMetric[]>("/api/matrix/judges");

  const graphNodes = useMemo(() => {
    if (network.data?.empty || !network.data) return [];
    return network.data.nodes.map((n) => ({
      id: n.name,
      label: n.name,
      size: Math.sqrt(n.volume) * 1.35,
      color: colorMode === "z" ? zColor(n.z) : deptColor(n.dominantDepartment),
    }));
  }, [network.data, colorMode]);

  const graphEdges = useMemo(() => network.data?.edges ?? [], [network.data]);

  const listJudges = useMemo(() => {
    if (judges.data && !Array.isArray(judges.data)) return [];
    const arr = (judges.data as unknown as JudgeMetric[]) ?? [];
    const q = search.trim().toLowerCase();
    return (q ? arr.filter((j) => j.name.toLowerCase().includes(q)) : arr)
      .sort((a, b) => b.nOpinions - a.nOpinions)
      .slice(0, 40);
  }, [judges.data, search]);

  const detail = useMemo(() => {
    if (!judges.data || !selectedJudge) return null;
    const arr = judges.data as unknown as JudgeMetric[];
    return arr.find((j) => j.name === selectedJudge) ?? null;
  }, [judges.data, selectedJudge]);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[1fr_340px] gap-4 min-h-0">
      <ModulePanel
        code="01"
        title="Carte neuro-cognitive — constellation des panélistes"
        subtitle="Graphe de co-siège réel · chaque lien = juges ayant siégé ensemble"
        source="api/matrix/network"
        actions={
          <div className="flex items-center gap-2">
            <Select value={colorMode} onValueChange={(v) => setColorMode(v as "z" | "dept")}>
              <SelectTrigger className="h-7 w-36 text-[11px] border-border/70" aria-label="Mode de couleur">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="z">COULEUR : ÉCART Z</SelectItem>
                <SelectItem value="dept">COULEUR : DÉPARTEMENT</SelectItem>
              </SelectContent>
            </Select>
            <Select value={minWeight} onValueChange={setMinWeight}>
              <SelectTrigger className="h-7 w-28 text-[11px] border-border/70" aria-label="Poids minimum des liens">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {["5", "8", "12", "20", "40"].map((w) => (
                  <SelectItem key={w} value={w}>LIENS ≥ {w}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <ReloadButton onClick={network.reload} />
          </div>
        }
      >
        <ModuleBody
          loading={network.loading}
          error={network.error}
          isEmpty={network.isEmpty}
          emptyMessage="Aucun lien de panel dans l'index — lancez l'ingestion du corpus réel."
          data={network.data}
        >
          {(d) => (
            d.nodes.length === 0 ? (
              <EmptyState message="Index vide." />
            ) : (
              <>
                <ForceGraph3D
                  nodes={graphNodes}
                  edges={graphEdges}
                  selectedId={selectedJudge}
                  onSelect={(id) => setSelectedJudge(id as string | null)}
                  height={520}
                />
                <div className="flex flex-wrap items-center gap-x-5 gap-y-1 mt-3">
                  <span className="label-caps text-muted-foreground">LÉGENDE</span>
                  {colorMode === "z" ? (
                    <>
                      <span className="mono text-[10px] text-pos">■ INFIRME PLUS QUE LA BASE (z &lt; 0)</span>
                      <span className="mono text-[10px] text-muted-foreground">■ DANS LA MOYENNE</span>
                      <span className="mono text-[10px] text-neg">■ CONFIRME PLUS QUE LA BASE (z &gt; 0)</span>
                    </>
                  ) : (
                    Object.entries(DEPT_LABELS).map(([k, v]) => (
                      <span key={k} className="mono text-[10px]" style={{ color: deptColor(k) }}>
                        ■ {v}
                      </span>
                    ))
                  )}
                  <span className="mono text-[10px] text-muted-foreground/70">
                    TAILLE ∝ √(VOLUME DÉCISIONNEL) · {fmtNum(d.totalPairs)} PAIRES RÉELLES
                  </span>
                </div>
              </>
            )
          )}
        </ModuleBody>
      </ModulePanel>

      <div className="flex flex-col gap-4 min-h-0">
        <ModulePanel code="01·B" title="Registre des juges" source="api/matrix/judges" className="flex-1 min-h-0">
          <div className="flex flex-col h-full min-h-0 gap-3">
            <Input
              placeholder="Rechercher un juge…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-8 text-xs mono"
              aria-label="Rechercher un juge"
            />
            <div className="max-h-64 xl:max-h-none xl:flex-1 overflow-y-auto pr-1 space-y-1">
              {judges.loading ? (
                <p className="mono text-[10px] text-muted-foreground">CHARGEMENT…</p>
              ) : listJudges.length === 0 ? (
                <p className="mono text-[10px] text-muted-foreground">AUCUN RÉSULTAT.</p>
              ) : (
                listJudges.map((j) => (
                  <button
                    key={j.name}
                    onClick={() => setSelectedJudge(j.name === selectedJudge ? null : j.name)}
                    className={`w-full flex items-center justify-between gap-2 px-2 py-1.5 rounded-sm border text-left transition-colors ${
                      j.name === selectedJudge
                        ? "border-primary/50 bg-primary/10"
                        : "border-transparent hover:bg-secondary/60"
                    }`}
                  >
                    <span className="mono text-[11px] truncate">{j.name}</span>
                    <span className="mono text-[10px] text-muted-foreground shrink-0">
                      n={j.nBinary} · {fmtPct(j.rate, 0)}
                    </span>
                  </button>
                ))
              )}
            </div>
          </div>
        </ModulePanel>

        <ModulePanel code="01·C" title="Fiche du magistrat">
          {detail ? (
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <h3 className="mono text-sm text-foreground">{detail.name}</h3>
                <span
                  className="mono text-[10px] border rounded-sm px-1.5 py-0.5"
                  style={{ color: deptColor(detail.dominantDepartment), borderColor: `${deptColor(detail.dominantDepartment)}55` }}
                >
                  {DEPT_LABELS[detail.dominantDepartment] ?? detail.dominantDepartment}
                </span>
              </div>
              <dl className="grid grid-cols-2 gap-x-3 gap-y-1.5 mono text-[11px]">
                <div><dt className="text-muted-foreground">VOLUME</dt><dd>{fmtNum(detail.nOpinions)} opinions</dd></div>
                <div><dt className="text-muted-foreground">N BINAIRES</dt><dd>{fmtNum(detail.nBinary)}</dd></div>
                <div><dt className="text-muted-foreground">TAUX CONFIRM.</dt><dd className="text-pos">{fmtPct(detail.rate)}</dd></div>
                <div><dt className="text-muted-foreground">ÉCART Z</dt><dd className={detail.z >= 0 ? "text-neg" : "text-pos"}>{fmtSigned(detail.z)}</dd></div>
                <div><dt className="text-muted-foreground">PRÉSIDENCES</dt><dd>{fmtNum(detail.presidingCount)}</dd></div>
                <div><dt className="text-muted-foreground">CO-JUGES</dt><dd>{fmtNum(detail.uniqueCoJudges)}</dd></div>
                <div><dt className="text-muted-foreground">VOLATILITÉ</dt><dd>{detail.volatility.toFixed(3)}</dd></div>
                <div><dt className="text-muted-foreground">FENÊTRE</dt><dd>{detail.yearSpan ? `${detail.yearSpan[0]}–${detail.yearSpan[1]}` : "—"}</dd></div>
              </dl>
              <div>
                <div className="label-caps text-muted-foreground mb-1">IC95 WILSON — TAUX DE CONFIRMATION</div>
                <WilsonBar rate={detail.rate} low={detail.wilson95.low} high={detail.wilson95.high} />
                <div className="mono text-[9px] text-muted-foreground mt-1">
                  [{fmtPct(detail.wilson95.low)} ; {fmtPct(detail.wilson95.high)}]
                </div>
              </div>
            </div>
          ) : (
            <p className="mono text-[10px] text-muted-foreground py-6 text-center">
              Sélectionnez un nœud dans la constellation
            </p>
          )}
        </ModulePanel>
      </div>

      <div className="xl:col-span-2">
        <MethodNote>
          Identité des juges = nom de famille normalisé de la ligne officielle de panel (règle R1 de
          l'ingestion ; variantes brutes conservées dans l'index). Les liens représentent des co-sièges
          réellement observés dans les 1 387 opinions du corpus. Le score z compare le taux de
          confirmation binaire du juge à la base du corpus (76,96 %) — |z| ≥ 2 = écart statistiquement
          significatif. L'auteur exact de chaque opinion n'étant pas extrait par le pipeline source,
          les taux sont agrégés au niveau du panel (limite documentée).
        </MethodNote>
      </div>
    </div>
  );
}
