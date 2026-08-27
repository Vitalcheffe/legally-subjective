import Link from "next/link";
import { notFound } from "next/navigation";
import { readFile } from "fs/promises";
import path from "path";
import { Chrome } from "@/components/ls/chrome";
import { getSystemState } from "@/lib/system-state";
import { getDocket, AXIS_LABELS } from "@/lib/dockets";

/* ————————————————————————————————————————————————
   THE CHAIN OF CUSTODY — every number, traced to the byte.
   Function: for one FILED docket, expose the exact source cache the
   numbers were computed from — file counts, retrieval windows, tree
   hashes, canonical serialization, verification instructions.
   Result: an audit page. Click any figure anywhere on this site and
   you can arrive here and re-walk the chain yourself.
   ———————————————————————————————————————————————— */

interface CustodyAxis {
  system: string;
  files: number;
  cache: string;
  uri_pattern: string;
  retrieved_window: (string | null)[];
  tree_sha256: string;
}

interface Custody {
  exported_at: string;
  law: string;
  dockets: Record<
    string,
    {
      subject: string;
      axes: Record<string, CustodyAxis>;
      index: { files: number; cache: string; retrieved_window: (string | null)[]; tree_sha256: string };
      docket_sha256: string;
    }
  >;
}

async function getCustody(): Promise<Custody | null> {
  try {
    return JSON.parse(
      await readFile(
        path.join(process.cwd(), "data", "productions", "custody.json"),
        "utf8",
      ),
    ) as Custody;
  } catch {
    return null;
  }
}

export async function generateStaticParams() {
  const { listDockets } = await import("@/lib/dockets");
  const dockets = await listDockets();
  return dockets.map((d) => ({ id: d.docket }));
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return {
    title: `Chain of custody — ${id} · Legally Subjective`,
    description:
      "Every number in this docket, traced to the exact cached source files it was computed from: counts, retrieval windows, tree hashes, and the verification command.",
  };
}

function fmtTs(t: string | null): string {
  return t ? t.replace("T", " ").replace("Z", " UTC") : "—";
}

export default async function DocketChainPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [d, custody, sys] = await Promise.all([
    getDocket(id),
    getCustody(),
    getSystemState(),
  ]);
  if (!d) notFound();
  const c = custody?.dockets[d.docket];

  return (
    <div className="flex min-h-screen flex-col bg-paper font-display text-ink">
      <Chrome
        build={sys.build}
        judgesScored={sys.judgesScored}
        docketsIngested={sys.docketsIngested}
        engineCycles={sys.engineCycles}
        engineLast={sys.engineLast}
        state={sys.state}
        route={`/docket/${d.docket}`}
      />

      <main className="flex-1">
        {/* ——— MASTHEAD ——— */}
        <section className="border-b border-rule">
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14 lg:py-14">
            <p className="micro">[{d.docket}] · The chain of custody</p>
            <h1 className="mt-5 font-display text-[clamp(2rem,4.2vw,3.4rem)] font-bold uppercase leading-[0.98] tracking-[-0.02em]">
              In re {d.subject.name}
              <br />
              <span className="text-ink-2">Chain of custody</span>
            </h1>
            <p className="mt-4 max-w-3xl text-[14px] leading-relaxed text-ink-2">
              {custody?.law ??
                "Custody production not yet exported."}{" "}
              Nothing on this site is estimated: a number without a source does
              not exist, and a source without a timestamp does not count.
            </p>
            <dl className="mt-7 grid max-w-3xl grid-cols-2 gap-x-8 gap-y-3 font-data text-[12px] sm:grid-cols-4">
              {[
                ["Docket SHA-256", (d.chain.sha256 ?? "—").slice(0, 14) + "…"],
                ["Canonical form", "keys sorted · UTF-8 · compact"],
                ["Seal law", "sha256 over serialization minus chain.sha256"],
                ["Pipeline", d.chain.pipeline],
              ].map(([k, v]) => (
                <div key={k}>
                  <dt className="text-[10px] tracking-[0.08em] text-ink-3 uppercase">{k}</dt>
                  <dd className="mt-0.5 font-medium break-all">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        {/* ——— PER-AXIS CUSTODY ——— */}
        {c && (
          <section className="border-b border-rule">
            <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14">
              <p className="micro">[001] Per-axis custody — the exact bytes behind each number</p>
              <div className="mt-6 border-t border-rule">
                {Object.entries(c.axes).map(([ax, cu]) => {
                  const a = d.axes[ax];
                  return (
                    <div key={ax} className="grid grid-cols-1 gap-x-8 gap-y-3 border-b border-hairline py-5 lg:grid-cols-[180px_150px_1fr_260px]">
                      <div>
                        <p className="font-display text-[14px] font-bold uppercase">{AXIS_LABELS[ax]}</p>
                        <p className="mt-1 font-data text-[10px] tracking-[0.04em] text-ink-3 uppercase">
                          {a?.percentile != null ? `pct ${a.percentile} · N=${a.n.toLocaleString("en-US")}` : a?.status}
                        </p>
                      </div>
                      <div className="font-data text-[12px]">
                        <p className="font-semibold uppercase">{cu.system}</p>
                        <p className="mt-1 text-ink-2">{cu.files} cached files</p>
                        <p className="text-ink-3">retrieved {fmtTs(cu.retrieved_window[0])} → {fmtTs(cu.retrieved_window[1])}</p>
                      </div>
                      <div className="text-[12px] leading-relaxed text-ink-2">
                        <p className="font-data text-[11px] break-all">{cu.uri_pattern}</p>
                        <p className="mt-1 font-data text-[11px] text-ink-3 break-all">{cu.cache}</p>
                      </div>
                      <div className="font-data text-[10.5px] leading-relaxed break-all lg:justify-self-end">
                        <p className="text-[9.5px] tracking-[0.08em] text-ink-3 uppercase">tree sha-256</p>
                        <p className="mt-0.5">{cu.tree_sha256}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>
        )}

        {/* ——— THE INDEX + THE SEAL ——— */}
        {c && (
          <section className="border-b border-rule bg-paper-2">
            <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14">
              <p className="micro">[002] The index and the seal</p>
              <div className="mt-6 grid grid-cols-1 gap-10 lg:grid-cols-2">
                <div>
                  <h3 className="font-display text-[15px] font-bold uppercase">The enumeration index</h3>
                  <dl className="mt-4 space-y-2.5 font-data text-[12px]">
                    {[
                      ["Cache", c.index.cache],
                      ["Files", String(c.index.files)],
                      ["Retrieval", `${fmtTs(c.index.retrieved_window[0])} → ${fmtTs(c.index.retrieved_window[1])}`],
                      ["Tree SHA-256", c.index.tree_sha256],
                    ].map(([k, v]) => (
                      <div key={k} className="grid grid-cols-[130px_1fr] gap-3 border-b border-hairline pb-2.5">
                        <dt className="text-[10px] tracking-[0.08em] text-ink-3 uppercase">{k}</dt>
                        <dd className="break-all">{v}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
                <div>
                  <h3 className="font-display text-[15px] font-bold uppercase">Verify it yourself</h3>
                  <p className="mt-4 text-[13px] leading-relaxed text-ink-2">
                    The whole pipeline is deterministic. Clone the repository,
                    re-run the computation over the same cached sources, and you
                    get bit-identical dockets — or the standard is violated.
                  </p>
                  <pre className="mt-4 overflow-x-auto border border-rule bg-paper px-4 py-3 font-data text-[11px] leading-relaxed">
{`git clone <repo> && cd legally-subjective
python scripts/file_dockets.py --verify
# determinism: OK — bit-identical

sha256sum data/dockets/${d.docket}.json
# seal: ${(d.chain.sha256 ?? "").slice(0, 24)}…`}
                  </pre>
                  <p className="mt-3 font-data text-[11px] text-ink-3">
                    The seal is computed over the canonical JSON (keys sorted,
                    UTF-8, compact separators) with chain.sha256 excluded, then written last.
                  </p>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* ——— THE LIMITS + LINKS ——— */}
        <section className="border-b border-rule">
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14">
            <p className="micro">[003] The record</p>
            <div className="mt-6 flex flex-wrap gap-3 font-data text-[11px] font-medium tracking-[0.06em] uppercase">
              <Link href={`/judge/${d.docket}`} className="border border-ink px-4 py-2.5 hover:bg-ink hover:text-white">
                The case file →
              </Link>
              <Link href={`/api/dockets/${d.docket}`} className="border border-rule px-4 py-2.5 text-ink-2 hover:border-ink hover:text-ink">
                Canonical JSON →
              </Link>
              <Link href={`/api/dockets/${d.docket}/bibtex`} className="border border-rule px-4 py-2.5 text-ink-2 hover:border-ink hover:text-ink">
                BibTeX →
              </Link>
              <Link href="/standard" className="border border-rule px-4 py-2.5 text-ink-2 hover:border-ink hover:text-ink">
                The standard →
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-ink text-white">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-x-8 gap-y-2 px-6 py-5 font-data text-[10.5px] font-medium tracking-[0.06em] sm:px-10 lg:px-14">
          <span>LEGALLY SUBJECTIVE — AN OPEN STANDARD. NO ONE OWNS IT.</span>
          <span className="text-white/60">{d.docket} · CUSTODY · UI-1.0 EXHIBIT</span>
          <Link href="/court/scotus" className="text-white/60 hover:text-white">
            THE BENCH →
          </Link>
        </div>
      </footer>
    </div>
  );
}
