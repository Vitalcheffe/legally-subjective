"use client";

/**
 * Behavioral Matrix — institutional shell.
 * Single visible route (/). Modules are lazy-loaded; the editorial tab
 * rail switches them. Register: legal journal, quiet authority.
 */
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
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
  { id: "overview", code: "00", label: "Synoptique", hint: "État du corpus réel" },
  { id: "neural", code: "01", label: "Carte neuro-cognitive", hint: "Constellation des panélistes · WebGL" },
  { id: "weakness", code: "02", label: "Matrice des écarts", hint: "Rétro-ingénierie décisionnelle" },
  { id: "heatmap", code: "03", label: "Carte thermique des biais", hint: "Déviations à la base annuelle" },
  { id: "montecarlo", code: "04", label: "Simulateur Monte-Carlo", hint: "Bootstrap sur issues réelles" },
  { id: "stylometry", code: "05", label: "Spectre stylométrique", hint: "Télémétrie lexicale" },
  { id: "precedent", code: "06", label: "Graphe de jurisprudence", hint: "Autorités résonantes · WebGL" },
  { id: "timeline", code: "07", label: "Chronologie cognitive", hint: "Télémétrie temporelle" },
  { id: "radar", code: "08", label: "Radar de déviation", hint: "Forme comportementale" },
  { id: "shield", code: "09", label: "Arbitrage humain contre IA", hint: "Sessions multi-agents LLM" },
  { id: "lab", code: "10", label: "Laboratoire expérimental", hint: "Protocole zero-shot · Brier · McNemar" },
] as const;

function LiveClock() {
  const [now, setNow] = useState<string>("--:--:--");
  useEffect(() => {
    const tick = () => setNow(new Date().toLocaleTimeString("fr-FR", { hour12: false }));
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, []);
  return <span className="mono text-[11px] text-muted-foreground">{now}</span>;
}

export function Console() {
  const activeModuleId = useMatrixStore((s) => s.module);
  const setModule = useMatrixStore((s) => s.setModule);
  const selectedJudge = useMatrixStore((s) => s.selectedJudge);

  const active = MODULES.find((m) => m.id === activeModuleId) ?? MODULES[0];

  return (
    <div className="min-h-screen flex flex-col bg-background paper-grain">
      {/* masthead */}
      <header className="border-b border-border bg-background/95 backdrop-blur sticky top-0 z-40">
        <div className="mx-auto max-w-[1600px] px-5 pt-4 pb-3 flex flex-wrap items-end gap-x-6 gap-y-2">
          <div className="min-w-0">
            <h1 className="serif-display text-xl font-bold leading-none text-foreground tracking-tight">
              Legally Subjective
              <span className="text-muted-foreground/50 font-normal mx-2">·</span>
              <span className="font-semibold italic text-primary">Behavioral Matrix</span>
            </h1>
            <p className="text-[11.5px] text-muted-foreground mt-1.5">
              Analyse décisionnelle judiciaire — Appellate Division de New York, corpus criminel 2015–2023
            </p>
          </div>
          <div className="ml-auto flex items-center gap-5 pb-0.5">
            <span className="label-caps text-muted-foreground/75 hidden md:inline">
              CourtListener + documents officiels NY
            </span>
            <span className="label-caps text-pos hidden lg:inline">
              Données réelles · zéro donnée fictive
            </span>
            <LiveClock />
          </div>
        </div>
        {/* editorial tab rail */}
        <nav className="mx-auto max-w-[1600px] px-5 flex gap-0 overflow-x-auto" aria-label="Modules d'analyse">
          {MODULES.map((m) => {
            const isActive = m.id === activeModuleId;
            return (
              <button
                key={m.id}
                onClick={() => setModule(m.id)}
                title={m.hint}
                className={`shrink-0 flex items-baseline gap-1.5 px-2.5 py-2 border-b-2 -mb-px transition-colors ${
                  isActive
                    ? "border-primary text-foreground"
                    : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                }`}
                aria-current={m.id === activeModuleId ? "page" : undefined}
              >
                <span className={`mono text-[10px] ${isActive ? "text-primary" : "text-muted-foreground/70"}`}>{m.code}</span>
                <span className="label-caps text-[10px]">{m.label}</span>
              </button>
            );
          })}
        </nav>
        {selectedJudge ? (
          <div className="border-t border-border bg-accent/60">
            <div className="mx-auto max-w-[1600px] px-5 py-1.5 flex items-center gap-3">
              <span className="label-caps text-muted-foreground">Magistrat à l'étude</span>
              <span className="serif-display text-[13px] font-semibold text-accent-foreground">{selectedJudge}</span>
              <button
                onClick={() => useMatrixStore.getState().setSelectedJudge(null)}
                className="ml-auto inline-flex items-center gap-1 label-caps text-muted-foreground hover:text-neg transition-colors px-2 py-0.5"
              >
                <X className="h-3 w-3" aria-hidden />
                Retirer
              </button>
            </div>
          </div>
        ) : null}
      </header>

      {/* workspace */}
      <main className="relative z-[1] flex-1 mx-auto w-full max-w-[1600px] px-5 py-6 min-w-0">
        <AnimatePresence mode="wait">
          <motion.div
            key={active.id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
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

      {/* colophon */}
      <footer className="mt-auto border-t border-border bg-card/60">
        <div className="mx-auto max-w-[1600px] px-5 py-3.5 flex flex-wrap items-center gap-x-8 gap-y-1.5">
          <span className="text-[10.5px] text-muted-foreground">
            Provenance · 1 387 appels criminels réels (NY App. Div. 2015–2023) · pipeline Phase 2 validé · empreinte SHA-256 par document
          </span>
          <span className="text-[10.5px] text-muted-foreground/80">
            Reproductibilité · bun scripts/ingest.ts (reconstruit l'index + validation croisée)
          </span>
          <span className="label-caps text-pos ml-auto">
            Contrat d'intégrité : aucune donnée fictive
          </span>
        </div>
      </footer>
    </div>
  );
}
