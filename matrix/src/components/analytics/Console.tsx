"use client";

/**
 * Behavioral Matrix — mission control shell.
 * Single visible route (/). Modules are lazy-loaded; the rail switches them.
 */
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { motion, AnimatePresence } from "framer-motion";
import { useMatrixStore } from "./store";
import { TerminalLoader } from "./shared";
import { OverviewPanel } from "./OverviewPanel";

const NeuralMap = dynamic(() => import("./NeuralMap").then((m) => m.NeuralMap), {
  loading: () => <TerminalLoader />,
  ssr: false,
});
const WeaknessMatrix = dynamic(() => import("./WeaknessMatrix").then((m) => m.WeaknessMatrix), {
  loading: () => <TerminalLoader />,
});
const BiasHeatmap = dynamic(() => import("./BiasHeatmap").then((m) => m.BiasHeatmap), {
  loading: () => <TerminalLoader />,
});
const MonteCarlo = dynamic(() => import("./MonteCarlo").then((m) => m.MonteCarlo), {
  loading: () => <TerminalLoader />,
});
const StylometrySpectrum = dynamic(() => import("./StylometrySpectrum").then((m) => m.StylometrySpectrum), {
  loading: () => <TerminalLoader />,
});
const PrecedentNet = dynamic(() => import("./PrecedentNet").then((m) => m.PrecedentNet), {
  loading: () => <TerminalLoader />,
  ssr: false,
});
const CognitiveTimeline = dynamic(() => import("./CognitiveTimeline").then((m) => m.CognitiveTimeline), {
  loading: () => <TerminalLoader />,
});
const DeviationRadar = dynamic(() => import("./DeviationRadar").then((m) => m.DeviationRadar), {
  loading: () => <TerminalLoader />,
});
const ComparisonShield = dynamic(() => import("./ComparisonShield").then((m) => m.ComparisonShield), {
  loading: () => <TerminalLoader />,
});
const ExperimentLab = dynamic(() => import("./ExperimentLab").then((m) => m.ExperimentLab), {
  loading: () => <TerminalLoader />,
});

const MODULES = [
  { id: "overview", code: "00", label: "SYNOPTIQUE", hint: "état du corpus réel" },
  { id: "neural", code: "01", label: "CARTE NEURO-COGNITIVE", hint: "constellation des panélistes · WebGL" },
  { id: "weakness", code: "02", label: "MATRICE DES ÉCARTS", hint: "rétro-ingénierie décisionnelle" },
  { id: "heatmap", code: "03", label: "CARTE THERMIQUE DES BIAIS", hint: "déviations à la base annuelle" },
  { id: "montecarlo", code: "04", label: "SIMULATEUR MONTE-CARLO", hint: "bootstrap sur issues réelles" },
  { id: "stylometry", code: "05", label: "SPECTRE STYLOMÉTRIQUE", hint: "télémétrie lexicale" },
  { id: "precedent", code: "06", label: "GRAPHE DE JURISPRUDENCE", hint: "autorités résonantes · WebGL" },
  { id: "timeline", code: "07", label: "CHRONOLOGIE COGNITIVE", hint: "télémétrie temporelle" },
  { id: "radar", code: "08", label: "RADAR DE DÉVIATION", hint: "forme comportementale" },
  { id: "shield", code: "09", label: "BOUCLIER HUMAIN vs IA", hint: "sessions multi-agents LLM" },
  { id: "lab", code: "10", label: "LABORATOIRE EXPÉRIMENTAL", hint: "protocole zero-shot · Brier · McNemar" },
] as const;

function LiveClock() {
  const [now, setNow] = useState<string>("--:--:--");
  useEffect(() => {
    const tick = () => setNow(new Date().toLocaleTimeString("fr-FR", { hour12: false }));
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, []);
  return <span className="mono text-[11px] text-muted-foreground">{now} UTC+1</span>;
}

export function Console() {
  const activeModuleId = useMatrixStore((s) => s.module);
  const setModule = useMatrixStore((s) => s.setModule);
  const selectedJudge = useMatrixStore((s) => s.selectedJudge);

  const active = MODULES.find((m) => m.id === activeModuleId) ?? MODULES[0];

  return (
    <div className="min-h-screen flex flex-col matrix-grid-bg">
      {/* header */}
      <header className="border-b border-border/70 bg-zinc-950/80 backdrop-blur sticky top-0 z-40">
        <div className="mx-auto max-w-[1600px] px-4 py-3 flex flex-wrap items-center gap-x-6 gap-y-2">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-2 h-2 rounded-full bg-emerald-400 pulse-led shrink-0" aria-hidden />
            <div className="min-w-0">
              <h1 className="mono text-sm text-foreground tracking-wide truncate">
                LEGALLY SUBJECTIVE <span className="text-muted-foreground/60">·</span>{" "}
                <span className="text-emerald-400 glow-emerald">BEHAVIORAL MATRIX</span>
              </h1>
              <p className="label-caps text-muted-foreground/80">
                CONSOLE D'ANALYSE COGNITIVE JUDICIAIRE — GRADE AÉROSPATIAL
              </p>
            </div>
          </div>
          <div className="ml-auto flex items-center gap-4">
            <span className="mono text-[10px] text-muted-foreground hidden md:inline">
              SRC · COURTLISTENER + DOCUMENTS OFFICIELS NY
            </span>
            <span className="mono text-[10px] text-emerald-400/90 hidden lg:inline">
              ● FLUX RÉEL — ZÉRO DONNÉE FICTIVE
            </span>
            <LiveClock />
          </div>
        </div>
        {/* module rail */}
        <nav className="mx-auto max-w-[1600px] px-4 pb-2 flex gap-1.5 overflow-x-auto" aria-label="Modules d'analyse">
          {MODULES.map((m) => (
            <button
              key={m.id}
              onClick={() => setModule(m.id)}
              title={m.hint}
              className={`shrink-0 flex items-center gap-2 px-2.5 py-1.5 rounded-sm border transition-colors ${
                m.id === activeModuleId
                  ? "border-primary/50 bg-primary/10 text-foreground"
                  : "border-border/60 text-muted-foreground hover:text-foreground hover:border-border"
              }`}
              aria-current={m.id === activeModuleId ? "page" : undefined}
            >
              <span className={`mono text-[9px] ${m.id === activeModuleId ? "text-primary" : "text-muted-foreground/60"}`}>{m.code}</span>
              <span className="label-caps">{m.label}</span>
            </button>
          ))}
        </nav>
        {selectedJudge ? (
          <div className="border-t border-border/50 bg-primary/5">
            <div className="mx-auto max-w-[1600px] px-4 py-1 flex items-center gap-2">
              <span className="label-caps text-muted-foreground">CIBLE VERROUILLÉE</span>
              <span className="mono text-[11px] text-emerald-400">{selectedJudge}</span>
              <button
                onClick={() => useMatrixStore.getState().setSelectedJudge(null)}
                className="mono text-[9px] text-muted-foreground hover:text-red-400 ml-2"
              >
                [DÉVERROUILLER]
              </button>
            </div>
          </div>
        ) : null}
      </header>

      {/* workspace */}
      <main className="flex-1 mx-auto w-full max-w-[1600px] px-4 py-5 min-w-0">
        <AnimatePresence mode="wait">
          <motion.div
            key={active.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.18 }}
          >
            {active.id === "overview" ? <OverviewPanel /> : null}
            {active.id === "neural" ? <NeuralMap /> : null}
            {active.id === "weakness" ? <WeaknessMatrix /> : null}
            {active.id === "heatmap" ? <BiasHeatmap /> : null}
            {active.id === "montecarlo" ? <MonteCarlo /> : null}
            {active.id === "stylometry" ? <StylometrySpectrum /> : null}
            {active.id === "precedent" ? <PrecedentNet /> : null}
            {active.id === "timeline" ? <CognitiveTimeline /> : null}
            {active.id === "radar" ? <DeviationRadar /> : null}
            {active.id === "shield" ? <ComparisonShield /> : null}
            {active.id === "lab" ? <ExperimentLab /> : null}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* footer */}
      <footer className="mt-auto border-t border-border/70 bg-zinc-950/90">
        <div className="mx-auto max-w-[1600px] px-4 py-3 flex flex-wrap items-center gap-x-6 gap-y-1.5">
          <span className="mono text-[9px] text-muted-foreground">
            PROVENANCE · 1 387 APPELS CRIMINELS RÉELS (NY APP. DIV. 2015-2023) · PIPELINE PHASE 2 VALIDÉ · SHA256 PAR DOCUMENT
          </span>
          <span className="mono text-[9px] text-muted-foreground/70">
            REPRODUCIBILITÉ · bun scripts/ingest.ts (RECONSTRUIT L'INDEX + VALIDATION CROISÉE)
          </span>
          <span className="mono text-[9px] text-emerald-400/80 ml-auto">
            CONTRAT ZÉRO-MOCK EN VIGUEUR
          </span>
        </div>
      </footer>
    </div>
  );
}
