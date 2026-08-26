"use client";

/**
 * INFINITUM — « Composer » : le laboratoire public (sandbox).
 * Collez un recital → la délibération multi-agents RÉELLE se déroule
 * (Procureur → Défense → Juge-IA). Éphémère par conception : rien n'est
 * archivé, le corpus et les modèles ne sont pas modifiés.
 */
import { useState } from "react";
import { Loader2, Scale, Send, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { VerdictBadge, fmtPct } from "@/components/analytics/shared";
import { VERDICT_LABELS } from "./mail-shared";

interface AgentVerdict {
  role: string;
  key_arguments: string[];
  verdict: "affirmed" | "reversed";
  confidence: number;
  summary: string;
}

interface SandboxResult {
  status: "ok" | "error" | "refused";
  ephemeral: true;
  title: string;
  prosecutor?: AgentVerdict;
  defender?: AgentVerdict;
  judge?: AgentVerdict;
  error?: string;
  notice: string;
}

const MIN_CHARS = 120;

function AgentCard({
  agent,
  emphasis = false,
}: {
  agent: AgentVerdict;
  emphasis?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-sm border bg-card px-4 py-3",
        emphasis && "border-primary/40 bg-accent/40",
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span
          className={cn(
            "mono text-[11px] font-medium tracking-wider uppercase",
            emphasis ? "text-accent-foreground" : "text-muted-foreground",
          )}
        >
          {agent.role}
        </span>
        <div className="flex items-center gap-2">
          <VerdictBadge verdict={agent.verdict} />
          <span className="mono text-[11px] text-muted-foreground">
            {VERDICT_LABELS[agent.verdict] ?? agent.verdict} · confiance{" "}
            {fmtPct(agent.confidence, 0)}
          </span>
        </div>
      </div>
      {agent.key_arguments.length > 0 && (
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-[13px] leading-relaxed text-foreground/85">
          {agent.key_arguments.map((a, i) => (
            <li key={i}>{a}</li>
          ))}
        </ol>
      )}
      {agent.summary && (
        <p className="mt-2 border-t border-border/50 pt-2 text-[13px] leading-relaxed text-muted-foreground">
          {agent.summary}
        </p>
      )}
    </div>
  );
}

export function Composer({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<SandboxResult | null>(null);

  const chars = text.trim().length;
  const canSubmit = chars >= MIN_CHARS && !running;

  async function submit() {
    setRunning(true);
    setResult(null);
    try {
      const res = await fetch("/api/mail/sandbox", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, text }),
      });
      const json = (await res.json()) as SandboxResult;
      setResult(json);
    } catch (e) {
      setResult({
        status: "error",
        ephemeral: true,
        title: title || "Échantillon sans titre",
        error: `Le laboratoire n'a pas répondu : ${(e as Error).message}. L'échec est rapporté tel quel — aucune analyse simulée.`,
        notice: "",
      });
    } finally {
      setRunning(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 font-serif">
            <Scale className="h-4 w-4" /> Composer — laboratoire public
          </DialogTitle>
          <DialogDescription>
            Le seul point d'entrée interactif : collez le recital d'une décision (la vôtre,
            ou n'importe laquelle) et la délibération multi-agents réelle se déroule —
            Procureur, Défense, puis Juge-IA. Rien n'est archivé, le corpus scientifique et
            les modèles ne sont pas modifiés.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <Input
            placeholder="Désignation de l'affaire (optionnel) — ex. People v. Exemple"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={120}
            aria-label="Désignation de l'affaire"
          />
          <div>
            <Textarea
              placeholder={`Collez ici le recital des faits (au moins ${MIN_CHARS} caractères — même seuil que le protocole scientifique). L'analyse se fait sur ce que vous soumettez, rien d'autre.`}
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="min-h-40 font-serif text-[14px] leading-relaxed"
              aria-label="Recital des faits à analyser"
            />
            <div className="mt-1 flex items-center justify-between">
              <span
                className={cn(
                  "mono text-[11px]",
                  chars >= MIN_CHARS ? "text-muted-foreground" : "text-neg",
                )}
              >
                {chars.toLocaleString("fr-FR")} caractères — minimum {MIN_CHARS}
              </span>
              <Button
                size="sm"
                onClick={submit}
                disabled={!canSubmit}
                aria-label="Lancer la délibération multi-agents"
              >
                {running ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                Délibérer
              </Button>
            </div>
          </div>

          {running && (
            <div className="rounded-sm border bg-secondary/40 px-4 py-3">
              <div className="flex items-center gap-2 text-sm">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                Délibération réelle en cours — séquence Procureur → Défense → Juge-IA
              </div>
              <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
                Trois appels successifs au moteur, sans estimation de durée : l'attente est
                le prix de l'analyse authentique. Aucun résultat n'est substitué en cas
                d'échec.
              </p>
            </div>
          )}

          {result && (result.status === "error" || result.status === "refused") && (
            <div
              role="alert"
              className="rounded-sm border border-neg/40 bg-neg-subtle px-4 py-3 text-sm leading-relaxed text-neg"
            >
              {result.error ?? "Erreur inconnue — rapportée telle quelle."}
            </div>
          )}

          {result && result.status === "ok" && (
            <div className="space-y-2">
              {result.prosecutor && <AgentCard agent={result.prosecutor} />}
              {result.defender && <AgentCard agent={result.defender} />}
              {result.judge && <AgentCard agent={result.judge} emphasis />}
              <div className="flex items-start gap-2 rounded-sm border border-pos/40 bg-pos-subtle px-3 py-2">
                <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-pos" />
                <p className="text-[11px] leading-relaxed text-pos">
                  {result.notice}
                </p>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
