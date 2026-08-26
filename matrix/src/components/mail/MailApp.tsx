"use client";

/**
 * INFINITUM — « La Boîte de la Cour » : interface publique (système jmail).
 *
 * Le monde entre ici. Les 1 387 décisions réelles se lisent comme une
 * messagerie ; le laboratoire de la console reste accessible via le
 * commutateur « Laboratoire ». Aucun bouton ne relance d'analyse : les
 * résultats sont publiés, datés, sourcés — c'est un projet fini que le
 * public explore, pas une démo interactive.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import {
  FileText,
  Flag,
  FlaskConical,
  Inbox,
  Menu,
  PenSquare,
  Search,
  Star,
  Users,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { TerminalLoader, deptColor } from "@/components/analytics/shared";
import type { FoldersPayload, MailItem, MailboxPage } from "@/lib/matrix/mailbox";
import { MailList } from "./MailList";
import { MailDetail } from "./MailDetail";
import { Composer } from "./Composer";
import { JudgeDirectory } from "./JudgeDirectory";

const ConsoleMode = dynamic(
  () => import("@/components/analytics/Console").then((m) => ({ default: m.Console })),
  { ssr: false, loading: () => <TerminalLoader label="Ouverture du laboratoire" /> },
);

const WELCOME_ITEM: MailItem = {
  id: "digest-welcome",
  kind: "digest",
  fromName: "INFINITUM — Rapports système",
  fromDetail: "Behavioral Matrix · rapport d'accueil",
  avatar: "IN",
  subject: "Bienvenue dans la Boîte de la Cour",
  snippet: "",
  date: new Date().toISOString(),
  department: null,
  disposition: null,
  flagged: false,
};

const STARS_KEY = "infinitum-follows";
const BANNER_KEY = "infinitum-banner-dismissed";

/** Deep-link shell for a shared dossier (?dossier=nyappdiv-…). */
const CASE_ID_RE = /^nyappdiv-\d+$/;

function sharedShell(caseId: string): MailItem {
  return {
    id: caseId,
    kind: "dossier",
    fromName: "Dossier partagé",
    fromDetail: "Ouverture du dossier partagé…",
    avatar: "D",
    subject: "Dossier partagé",
    snippet: "",
    date: new Date().toISOString(),
    department: null,
    disposition: null,
    flagged: false,
  };
}

const BOX_TITLES: Record<string, string> = {
  inbox: "Boîte de réception",
  flagged: "Signaux statistiques — président ou auteur en écart significatif",
  reports: "Rapports de la Matrice",
  followed: "Suivis (local à ce navigateur)",
  affirmed: "Confirmés",
  reversed: "Infirmés / annulés",
  signed: "Opinions signées",
  memos: "Mémos du président",
  "per-curiam": "Per curiam",
};

function RailButton({
  icon,
  label,
  count,
  active,
  onClick,
  accent,
}: {
  icon: React.ReactNode;
  label: string;
  count?: number;
  active: boolean;
  onClick: () => void;
  accent?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={active ? "true" : undefined}
      className={cn(
        "flex w-full items-center gap-2.5 rounded-sm px-3 py-1.5 text-left text-sm transition-colors",
        active
          ? "bg-accent font-medium text-accent-foreground"
          : "text-foreground/80 hover:bg-secondary/70",
        accent && "font-medium text-primary",
      )}
    >
      <span className={cn("shrink-0", active ? "text-accent-foreground" : "text-muted-foreground")}>
        {icon}
      </span>
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {count !== undefined && (
        <span className="mono shrink-0 text-[11px] text-muted-foreground">
          {count.toLocaleString("fr-FR")}
        </span>
      )}
    </button>
  );
}

export function MailApp({ initialDossier }: { initialDossier?: string }) {
  const [mode, setMode] = useState<"public" | "labo">("public");
  const [box, setBox] = useState("inbox");
  const [query, setQuery] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [page, setPage] = useState(1);
  const [mailPage, setMailPage] = useState<MailboxPage | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [folders, setFolders] = useState<FoldersPayload | null>(null);
  const [selected, setSelected] = useState<MailItem | null>(null);
  const [stars, setStars] = useState<Set<string>>(new Set());
  const [starsRev, setStarsRev] = useState(0);
  const [composerOpen, setComposerOpen] = useState(false);
  const [directoryOpen, setDirectoryOpen] = useState(false);
  const [railOpen, setRailOpen] = useState(false);
  const [bannerOpen, setBannerOpen] = useState(false);

  // Mount: local follows, first-visit banner, auto-open welcome on desktop,
  // or the shared dossier of a deep link (?dossier=nyappdiv-…).
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STARS_KEY);
      if (raw) {
        const arr = JSON.parse(raw);
        if (Array.isArray(arr)) setStars(new Set(arr.map(String)));
      }
      if (!localStorage.getItem(BANNER_KEY)) setBannerOpen(true);
    } catch {
      /* stockage local indisponible — les suivis ne fonctionnent pas, sans gravité */
    }
    if (initialDossier && CASE_ID_RE.test(initialDossier)) {
      setSelected(sharedShell(initialDossier));
      return;
    }
    if (window.matchMedia("(min-width: 768px)").matches) setSelected(WELCOME_ITEM);
  }, []);

  // Folders — loaded once.
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/mail/folders", { signal: controller.signal })
      .then((r) => r.json())
      .then((j: FoldersPayload) => {
        if (j && !j.empty) setFolders(j);
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  // Debounced search.
  useEffect(() => {
    const t = setTimeout(() => {
      setDebouncedQ(query.trim());
      setPage(1);
    }, 350);
    return () => clearTimeout(t);
  }, [query]);

  const followedKey = box === "followed" ? `${starsRev}:${[...stars].sort().join(",")}` : "";

  // Mailbox list.
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setListLoading(true);
      try {
        const params = new URLSearchParams({ box, page: String(page), pageSize: "50" });
        if (debouncedQ) params.set("q", debouncedQ);
        if (box === "followed") params.set("ids", [...stars].join(","));
        const res = await fetch(`/api/mail/dossiers?${params.toString()}`, {
          signal: controller.signal,
        });
        const json = await res.json();
        if (!res.ok) throw new Error(json?.message ?? `HTTP ${res.status}`);
        setMailPage(json as MailboxPage);
        setListLoading(false);
      } catch (e) {
        if (controller.signal.aborted) return;
        setMailPage({
          box,
          q: debouncedQ,
          page: 1,
          pageSize: 50,
          total: 0,
          pages: 1,
          items: [],
          empty: true,
        });
        setListLoading(false);
      }
    }
    load();
    return () => controller.abort();
  }, [box, debouncedQ, page, followedKey]);

  const toggleStar = useCallback((id: string) => {
    setStars((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      try {
        localStorage.setItem(STARS_KEY, JSON.stringify([...next]));
      } catch {
        /* stockage local indisponible */
      }
      return next;
    });
    setStarsRev((r) => r + 1);
  }, []);

  const selectBox = useCallback((id: string) => {
    setBox(id);
    setPage(1);
    setRailOpen(false);
  }, []);

  const pickJudge = useCallback((name: string) => {
    setBox("inbox");
    setPage(1);
    setQuery(name);
    setDebouncedQ(name);
  }, []);

  const boxTitle = useMemo(() => {
    const custom = folders?.labels.find((l) => l.id === box)?.label;
    return BOX_TITLES[box] ?? custom ?? "Dossiers";
  }, [box, folders]);

  const totalLabel = mailPage
    ? `${mailPage.total.toLocaleString("fr-FR")} dossiers`
    : folders
      ? `${folders.folders[0]?.count.toLocaleString("fr-FR") ?? "…"} dossiers`
      : "";

  const rail = (
    <nav className="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto px-2 py-3" aria-label="Dossiers et libellés">
      <button
        type="button"
        onClick={() => {
          setComposerOpen(true);
          setRailOpen(false);
        }}
        className="mb-3 flex items-center gap-2 rounded-sm border border-primary/35 bg-accent px-3 py-2 text-left text-sm font-medium text-accent-foreground transition-colors hover:bg-accent/70"
      >
        <PenSquare className="h-4 w-4" />
        <span className="flex-1">Composer</span>
        <span className="mono text-[10px] font-normal opacity-70">éphémère</span>
      </button>

      <RailButton
        icon={<Inbox className="h-4 w-4" />}
        label="Boîte de réception"
        count={folders?.folders.find((f) => f.id === "inbox")?.count}
        active={box === "inbox"}
        onClick={() => selectBox("inbox")}
      />
      <RailButton
        icon={<Flag className="h-4 w-4" />}
        label="Signaux statistiques"
        count={folders?.folders.find((f) => f.id === "flagged")?.count}
        active={box === "flagged"}
        onClick={() => selectBox("flagged")}
      />
      <RailButton
        icon={<FileText className="h-4 w-4" />}
        label="Rapports de la Matrice"
        count={folders?.reports ?? 5}
        active={box === "reports"}
        onClick={() => selectBox("reports")}
      />
      {stars.size > 0 && (
        <RailButton
          icon={<Star className="h-4 w-4" />}
          label="Suivis · local"
          count={stars.size}
          active={box === "followed"}
          onClick={() => selectBox("followed")}
        />
      )}
      <RailButton
        icon={<Users className="h-4 w-4" />}
        label="Contacts — juges"
        count={folders?.judges}
        active={false}
        accent
        onClick={() => {
          setDirectoryOpen(true);
          setRailOpen(false);
        }}
      />

      <p className="mono mt-4 mb-1 px-3 text-[10px] tracking-[0.14em] text-muted-foreground uppercase">
        Libellés
      </p>
      {folders?.labels.map((l) => (
        <RailButton
          key={l.id}
          icon={
            l.id.startsWith("dept-") ? (
              <span
                className="h-2 w-2 shrink-0 rounded-full"
                style={{
                  backgroundColor: deptColor(l.id.replace("dept-", "")),
                }}
              />
            ) : (
              <span className="h-2 w-2 shrink-0 rounded-full border border-muted-foreground/40" />
            )
          }
          label={l.label}
          count={l.count}
          active={box === l.id}
          onClick={() => selectBox(l.id)}
        />
      ))}

      <p className="mono mt-auto px-3 pt-4 text-[10px] leading-relaxed text-muted-foreground">
        {folders?.corpusYears
          ? `Corpus réel ${folders.corpusYears[0]}–${folders.corpusYears[1]}`
          : "Chargement du corpus…"}
      </p>
    </nav>
  );

  if (mode === "labo") {
    return (
      <div className="relative h-screen overflow-y-auto">
        <ConsoleMode />
        <button
          type="button"
          onClick={() => setMode("public")}
          className="fixed right-4 bottom-4 z-50 flex items-center gap-2 rounded-sm border border-primary/40 bg-card px-3 py-2 text-xs font-medium shadow-md transition-colors hover:bg-accent"
        >
          <X className="h-3.5 w-3.5" /> Retour à l&apos;interface publique
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background text-foreground">
      {/* ————— Barre supérieure ————— */}
      <header className="flex shrink-0 items-center gap-2 border-b bg-card px-3 py-2 md:gap-4 md:px-4">
        <button
          type="button"
          aria-label="Ouvrir le menu des dossiers"
          onClick={() => setRailOpen(true)}
          className="rounded-sm p-1.5 transition-colors hover:bg-secondary md:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="font-serif text-lg font-bold tracking-tight whitespace-nowrap">
            INFINITUM
          </span>
          <span className="mono hidden text-[10px] tracking-[0.18em] text-muted-foreground uppercase sm:inline">
            Dossiers
          </span>
        </div>

        <div className="relative mx-auto w-full max-w-xl flex-1">
          <Search className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Rechercher une affaire, un juge, un docket, une citation, un fragment du recital…"
            className="h-9 rounded-full border bg-secondary/40 pl-9 text-sm"
            aria-label="Recherche dans les dossiers réels"
          />
        </div>

        <div
          className="flex shrink-0 items-center overflow-hidden rounded-full border"
          role="group"
          aria-label="Choix de l'interface"
        >
          <button
            type="button"
            onClick={() => setMode("public")}
            aria-pressed={mode === "public"}
            className={cn(
              "mono px-3 py-1.5 text-[11px] transition-colors",
              mode === "public"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-secondary",
            )}
          >
            Publique
          </button>
          <button
            type="button"
            onClick={() => setMode("labo")}
            aria-pressed={mode === "labo"}
            className={cn(
              "mono flex items-center gap-1.5 px-3 py-1.5 text-[11px] transition-colors",
              mode === "labo"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-secondary",
            )}
          >
            <FlaskConical className="h-3.5 w-3.5" /> Laboratoire
          </button>
        </div>

        <div
          className="hidden items-center gap-2 lg:flex"
          title="Vous consultez l'intégralité des dossiers analysés — données réelles, sources officielles"
        >
          <span className="mono flex h-8 w-8 items-center justify-center rounded-full border border-primary/35 bg-accent text-[11px] font-medium text-accent-foreground">
            NY
          </span>
          <span className="leading-tight">
            <span className="block text-xs font-medium">Boîte de la cour</span>
            <span className="mono block text-[10px] text-muted-foreground">connecté — lecture</span>
          </span>
        </div>
      </header>

      {/* ————— Bandeau d'accueil (première visite) ————— */}
      {bannerOpen && folders && (
        <div className="flex shrink-0 items-start gap-3 border-b border-primary/25 bg-accent/60 px-4 py-2.5">
          <p className="flex-1 text-[13px] leading-relaxed text-accent-foreground">
            Vous consultez l&apos;intégralité des dossiers analysés —{" "}
            <strong>
              {(folders.folders[0]?.count ?? 0).toLocaleString("fr-FR")} décisions criminelles
              réelles
            </strong>{" "}
            de la Division d&apos;appel de New York ({folders.corpusYears?.[0]}–
            {folders.corpusYears?.[1]}), {folders.judges} juges, sources officielles. Zéro
            donnée fabriquée — c&apos;est un projet terminé que vous explorez, pas une démo.
          </p>
          <Button
            size="sm"
            variant="outline"
            className="h-7 shrink-0 border-primary/40 text-[11px]"
            onClick={() => setSelected(WELCOME_ITEM)}
          >
            Lire l&apos;accueil
          </Button>
          <button
            type="button"
            aria-label="Fermer le bandeau"
            className="shrink-0 rounded-sm p-1 hover:bg-secondary"
            onClick={() => {
              setBannerOpen(false);
              try {
                localStorage.setItem(BANNER_KEY, "1");
              } catch {
                /* stockage local indisponible */
              }
            }}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* ————— Corps : rail + liste + lecture ————— */}
      <div className="flex min-h-0 flex-1">
        <aside className="hidden w-60 shrink-0 flex-col border-r bg-card/40 md:flex">{rail}</aside>

        <section
          className={cn(
            "flex w-full min-w-0 flex-col border-r md:w-[380px] xl:w-[420px]",
            selected && "hidden md:flex",
          )}
          aria-label="Liste des dossiers"
        >
          <div className="flex shrink-0 items-baseline justify-between gap-2 border-b bg-card/60 px-4 py-2">
            <h2 className="truncate font-serif text-sm font-semibold">{boxTitle}</h2>
            <span className="mono shrink-0 text-[11px] text-muted-foreground">{totalLabel}</span>
          </div>
          <div className="min-h-0 flex-1">
            <MailList
              page={mailPage}
              loading={listLoading}
              selectedId={selected?.id ?? null}
              stars={stars}
              onToggleStar={toggleStar}
              onSelect={setSelected}
              onPage={setPage}
            />
          </div>
        </section>

        <section className="min-w-0 flex-1" aria-label="Lecture du dossier">
          <div className={cn("h-full", !selected && "hidden md:block")}>
            <MailDetail
              item={selected}
              onBack={() => setSelected(null)}
            />
          </div>
        </section>
      </div>

      {/* ————— Pied de coquille ————— */}
      <footer className="flex shrink-0 flex-wrap items-center justify-between gap-x-4 gap-y-0.5 border-t bg-card/70 px-4 py-1.5">
        <p className="text-[10.5px] text-muted-foreground">
          INFINITUM · Behavioral Matrix — profilage cognitif et comportemental du
          judiciaire · sources : opinions officielles de la Division d&apos;appel de
          l&apos;État de New York (nycourts.gov · CourtListener)
        </p>
        <p className="mono text-[10px] whitespace-nowrap text-pos">
          données réelles · zéro donnée fabriquée
        </p>
      </footer>

      {/* ————— Surcouches ————— */}
      <Sheet open={railOpen} onOpenChange={setRailOpen}>
        <SheetContent side="left" className="w-72 p-0">
          <SheetHeader className="border-b px-4 py-3">
            <SheetTitle className="font-serif text-base">INFINITUM — Dossiers</SheetTitle>
          </SheetHeader>
          {rail}
        </SheetContent>
      </Sheet>

      <Composer open={composerOpen} onOpenChange={setComposerOpen} />
      <JudgeDirectory
        open={directoryOpen}
        onOpenChange={setDirectoryOpen}
        onPick={pickJudge}
      />
    </div>
  );
}
