"use client";

/**
 * MODULE 06 — GRAPHE DE JURISPRUDENCE RÉSONANTE.
 * Nodes = real authorities (cases & statutes) extracted by deterministic
 * regex from the official opinion texts; edges = co-citation within the
 * same opinion (≥ 3 shared opinions). Size = distinct opinions citing it.
 */
import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  useMatrixData, ModulePanel, ModuleBody, ReloadButton, fmtNum,
  KpiChip, MethodNote, deptColor, DEPT_LABELS,
} from "./shared";

const ForceGraph3D = dynamic(() => import("./ForceGraph3D"), { ssr: false });

interface PrecedentPayload {
  empty: boolean;
  nodes: {
    target: string; kind: string; citedInOpinions: number;
    mentions: number; dominantDepartment: string;
  }[];
  edges: { source: string; target: string; weight: number }[];
  totalUniqueTargets: number;
  totalMentions: number;
}

const KIND_COLORS: Record<string, string> = {
  case: "#fbbf24",
  statute: "#34d399",
};

export function PrecedentNet() {
  const [topN, setTopN] = useState("40");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const { data, loading, error, isEmpty, reload } = useMatrixData<PrecedentPayload>(
    `/api/matrix/precedents?topN=${topN}`,
  );

  const graphNodes = useMemo(() => {
    if (!data || data.empty) return [];
    return data.nodes.map((n) => ({
      id: n.target,
      label: n.target,
      size: Math.sqrt(n.citedInOpinions) * 1.5,
      color: KIND_COLORS[n.kind] ?? "#a1a1aa",
    }));
  }, [data]);

  const listNodes = useMemo(() => {
    if (!data || data.empty) return [];
    const q = search.trim().toLowerCase();
    return (q ? data.nodes.filter((n) => n.target.toLowerCase().includes(q)) : data.nodes)
      .slice(0, 40);
  }, [data, search]);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[1fr_340px] gap-4">
      <ModulePanel
        code="06"
        title="GRAPHE DE JURISPRUDENCE RÉSONANTE — CONSTELLATION DES AUTORITÉS"
        subtitle="Autorités réellement citées dans les opinions · liens = co-citation dans une même opinion (≥ 3)"
        source="api/matrix/precedents"
        actions={
          <div className="flex items-center gap-2">
            <Select value={topN} onValueChange={setTopN}>
              <SelectTrigger className="h-7 w-32 text-[11px] border-border/70" aria-label="Nombre d'autorités affichées">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {["20", "30", "40", "60", "80"].map((n) => (
                  <SelectItem key={n} value={n}>TOP {n}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <ReloadButton onClick={reload} />
          </div>
        }
      >
        <ModuleBody
          loading={loading}
          error={error}
          isEmpty={isEmpty}
          emptyMessage="Aucune citation extraite — l'index des autorités est vide."
          data={data}
        >
          {(d) => (
            <>
              <div className="grid grid-cols-3 gap-3 mb-4">
                <KpiChip label="AUTORITÉS UNIQUES" value={fmtNum(d.totalUniqueTargets)} sub="dans tout le corpus" />
                <KpiChip label="MENTIONS TOTALES" value={fmtNum(d.totalMentions)} sub="occurrences regex-détectées" />
                <KpiChip label="LIENS DE CO-CITATION" value={fmtNum(d.edges.length)} sub={`parmi le top ${topN}`} />
              </div>
              <ForceGraph3D
                nodes={graphNodes}
                edges={d.edges}
                selectedId={selected}
                onSelect={(id) => setSelected(id as string | null)}
                height={480}
              />
              <div className="flex flex-wrap items-center gap-x-5 gap-y-1 mt-3">
                <span className="label-caps text-muted-foreground">LÉGENDE</span>
                <span className="mono text-[10px] text-amber-400">■ JURISPRUDENCE (People v X, Matter of X)</span>
                <span className="mono text-[10px] text-emerald-400">■ TEXTE DE LOI (CPL, Penal Law…)</span>
                <span className="mono text-[10px] text-muted-foreground/70">TAILLE ∝ √(OPINIONS CITANTES)</span>
              </div>
            </>
          )}
        </ModuleBody>
      </ModulePanel>

      <ModulePanel code="06·B" title="RÉFÉRENTIEL DES AUTORITÉS" className="min-h-0">
        <div className="flex flex-col h-full gap-3 min-h-0">
          <Input
            placeholder="RECHERCHER (EX. « 440.10 »)…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 text-xs mono"
            aria-label="Rechercher une autorité"
          />
          <div className="flex-1 min-h-0 overflow-y-auto pr-1 space-y-1 max-h-[520px]">
            {listNodes.map((n) => (
              <button
                key={n.target}
                onClick={() => setSelected(n.target === selected ? null : n.target)}
                className={`w-full flex items-start justify-between gap-2 px-2 py-1.5 rounded-sm border text-left transition-colors ${
                  n.target === selected ? "border-primary/50 bg-primary/10" : "border-transparent hover:bg-secondary/60"
                }`}
              >
                <div className="min-w-0">
                  <div className="mono text-[11px] truncate">{n.target}</div>
                  <div className="mono text-[9px] text-muted-foreground">
                    <span style={{ color: KIND_COLORS[n.kind] }}>
                      {n.kind === "case" ? "JURISPRUDENCE" : "LOI"}
                    </span>
                    {" · "}
                    <span style={{ color: deptColor(n.dominantDepartment) }}>
                      {DEPT_LABELS[n.dominantDepartment] ?? n.dominantDepartment}
                    </span>
                  </div>
                </div>
                <div className="mono text-[10px] text-muted-foreground shrink-0 text-right">
                  <div>{fmtNum(n.citedInOpinions)} op.</div>
                  <div className="text-muted-foreground/60">{fmtNum(n.mentions)} réf.</div>
                </div>
              </button>
            ))}
            {listNodes.length === 0 && !loading ? (
              <p className="mono text-[10px] text-muted-foreground">AUCUN RÉSULTAT.</p>
            ) : null}
          </div>
        </div>
      </ModulePanel>

      <div className="xl:col-span-2">
        <MethodNote>
          Extraction déterministe (règle R5) sur le texte officiel intégral : citations d'espèces
          « People v X / Matter of X » suivies d'une référence de recueil (NY3d, AD3d, NY Slip
          Op…) et références statutaires (CPL, CPLR, Penal Law…). Une autorité = une chaîne
          normalisée ; le lien de co-citation exige ≥ 3 opinions citant les deux autorités. La
          couleur du département dans le référentiel = département dominant des opinions qui la
          citent. Note : « Judiciary Law 431 » apparaît dans la ligne de publication standard des
          slip opinions — c'est un artefact réel du corpus, conservé tel quel.
        </MethodNote>
      </div>
    </div>
  );
}
