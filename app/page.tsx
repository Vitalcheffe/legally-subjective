import type { ReactNode } from "react";

/* ------------------------------------------------------------------ */
/* All numbers below are verified against data/processed/stats_v1.json */
/* and results/m2_baselines.json (frozen 2026-08-28).                   */
/* ------------------------------------------------------------------ */

const REPO = "https://github.com/Vitalcheffe/legally-subjective";

const HERO_STATS: Array<[string, string]> = [
  ["569", "argued cases"],
  ["1,778", "opinions"],
  ["13", "justices"],
  ["9 terms", "OT2015–2023"],
  ["98.6%", "oral arguments"],
];

const TERMS: Array<[string, number, number, number]> = [
  ["OT2015", 72, 294, 0],
  ["OT2016", 69, 247, 3],
  ["OT2017", 65, 235, 18],
  ["OT2018", 72, 265, 18],
  ["OT2019", 60, 263, 11],
  ["OT2020", 56, 130, 7],
  ["OT2021", 62, 86, 11],
  ["OT2022", 55, 117, 7],
  ["OT2023", 58, 141, 4],
];

const BASELINES = [
  {
    id: "B4",
    name: "Per-justice ideology",
    desc: "Martin–Quinn scores — vote the ideology, ignore the case",
    value: "63.7%",
    ci: "[61.3 – 65.9]",
    toBeat: true,
  },
  {
    id: "B3",
    name: "Always reverse",
    desc: "predict the lower court loses, every single time",
    value: "60.1%",
    ci: "[51.8 – 67.9]",
    toBeat: false,
  },
  {
    id: "B2",
    name: "Always conservative",
    desc: "the fixed direction the Court trended toward in the test window",
    value: "56.4%",
    ci: "[49.9 – 62.8]",
    toBeat: false,
  },
  {
    id: "B1",
    name: "Majority class",
    desc: "always predict the modal outcome — the floor, not the bar",
    value: "43.6%",
    ci: "[37.2 – 50.1]",
    toBeat: false,
  },
];

const CONDITIONS = [
  {
    letter: "A",
    title: "Zero-shot",
    kind: "control",
    body: "The unmodified base model reads the case and predicts each justice's vote. Nothing has been taught to it. This is the floor of machine belief: what a generic model already assumes about the Court, unprompted and unaided.",
  },
  {
    letter: "B",
    title: "Persona (QLoRA)",
    kind: "treatment",
    body: "The same model, lightly fine-tuned — one to three epochs, 4-bit QLoRA — on each justice's own opinions. Nine adapters for La Chambre, the Court as it stood. The experiment's heart: does a justice's prose carry a signal about their future votes?",
  },
  {
    letter: "C",
    title: "Retrieval (RAG)",
    kind: "treatment",
    body: "The base model predicts with the Court's prior decisions retrieved at prediction time. It knows the case law without claiming any identity. The alternative treatment: knowledge without persona.",
  },
  {
    letter: "D",
    title: "Statistical baselines",
    kind: "the bar",
    body: "Majority class. Always reverse. Per-justice ideology from Martin–Quinn scores. A few lines of Python with no language model at all — and the numbers any model must beat before claiming it learned anything.",
  },
];

const MILESTONES = [
  {
    id: "M1",
    title: "Corpus-Monde",
    desc: "569 argued cases assembled, cross-validated against SCDB, frozen under SHA-256.",
    status: "done",
    label: "frozen 2026-08-28",
  },
  {
    id: "M2",
    title: "Statistical baselines",
    desc: "The numbers to beat, with Wilson 95% intervals and inter-judge agreement.",
    status: "done",
    label: "done",
  },
  {
    id: "M1.5",
    title: "Opinion texts & cleaning",
    desc: "1,778 opinion texts collected, deduplicated, normalized; temporal train/test split per justice with a zero-leakage audit.",
    status: "now",
    label: "in progress",
  },
  {
    id: "M3",
    title: "QLoRA personas",
    desc: "Nine adapters trained on free GPUs (Colab/Kaggle), with memorization audits published alongside each one.",
    status: "todo",
    label: "next",
  },
  {
    id: "M4",
    title: "The sealed test",
    desc: "One pass, four conditions, fifty 5–4 decisions. Published whatever the numbers say.",
    status: "todo",
    label: "once",
  },
];

function Section({
  id,
  n,
  title,
  children,
}: {
  id: string;
  n: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="section" id={id}>
      <div className="wrap">
        <p className="section-eyebrow">{n}</p>
        <h2>{title}</h2>
        {children}
      </div>
    </section>
  );
}

export default function Page() {
  return (
    <>
      <header className="site-header">
        <div className="wrap">
          <a className="brand" href="#top">
            <span className="brand-mark" aria-hidden="true" />
            <span className="brand-name">Legally Subjective</span>
            <span className="brand-tag">Subjectivity, measured.</span>
          </a>
          <nav className="site-nav" aria-label="Site">
            <a href="#question">Question</a>
            <a href="#conditions">Method</a>
            <a href="#corpus">Corpus</a>
            <a href="#baselines">Baselines</a>
            <a href="#protocol">Protocol</a>
            <a href="#roadmap">Roadmap</a>
            <a className="nav-gh" href={REPO}>
              GitHub
            </a>
          </nav>
        </div>
      </header>

      <main id="top">
        {/* ---------------- HERO ---------------- */}
        <div className="hero">
          <div className="wrap">
            <p className="eyebrow">An open experiment in judicial predictability</p>
            <h1>Subjectivity, measured.</h1>
            <p className="hero-sub">How much of a Supreme Court vote is already on the page?</p>
            <p className="hero-lead">
              One open model, four conditions, a corpus frozen under hash — and a sealed
              final test that nobody, including the author, can peek at. This project does
              not argue about judicial personality. It hands the question a number.
            </p>
            <p className="hero-note">
              No budget, no lab, no credentials. Every byte of data is public, every script
              is in the repository, and every result will be published — whatever it says.
            </p>
            <div className="stat-strip" role="list" aria-label="Corpus in numbers">
              {HERO_STATS.map(([num, label]) => (
                <div className="stat-cell" role="listitem" key={label}>
                  <div className="stat-num">{num}</div>
                  <span className="stat-label">{label}</span>
                </div>
              ))}
            </div>
            <p className="status-line">
              <span className="status-dot" aria-hidden="true" />
              Currently running: M1.5 — collecting and cleaning the 1,778 opinion texts.
              Training comes next.
            </p>
          </div>
        </div>

        {/* ---------------- 01 QUESTION ---------------- */}
        <Section id="question" n="01 — The question" title="Do justices have a style, and does it decide anything?">
          <div className="prose">
            <p>
              Justices of the United States Supreme Court insist that votes follow law, not
              personality. The legal realists suspected otherwise, a century ago. Neither
              side has ever been handed a number.
            </p>
            <p>
              This project takes a model small enough to run on a free borrowed GPU —
              Llama 3 8B — and asks it to predict how each justice voted in argued cases,
              using only what was public before the decision was filed: the facts of the
              case, the question presented, the oral argument. The point is not to build a
              product. The point is to locate the ceiling.
            </p>
            <p>
              The decisive comparison is between two versions of the same model: one that
              merely knows the Court exists, and one that has briefly studied each
              justice's own prose.
            </p>
          </div>
          <div className="outcome-pair">
            <div className="outcome">
              <p className="outcome-label">If B beats A</p>
              <p>
                A justice's writing carries a measurable signal about their future votes.
                Persona is extractable from text.
              </p>
            </div>
            <div className="outcome">
              <p className="outcome-label">If B equals A</p>
              <p>
                Whatever "judicial personality" is, it is not in the data. The mythology
              does not survive contact with measurement.
              </p>
            </div>
          </div>
          <p className="outcome-note">
            Both outcomes are findings. Both get published. The experiment was designed so
            that there is no interesting way to fail.
          </p>
        </Section>

        {/* ---------------- 02 CONDITIONS ---------------- */}
        <Section id="conditions" n="02 — The method" title="Four conditions, one question">
          <div className="prose">
            <p>
              Every prediction task runs under all four conditions on the same split: the
              model either knows nothing, knows a justice's style, knows the case law, or
              knows nothing but statistics. Same base model everywhere —{" "}
              <strong>Llama 3 8B</strong> — so any difference between conditions is
              attributable to what was added, not to which model was used.
            </p>
          </div>
          <div className="conditions">
            {CONDITIONS.map((c) => (
              <article className="condition" key={c.letter}>
                <div className="condition-letter" aria-hidden="true">
                  {c.letter}
                </div>
                <div>
                  <h3>{c.title}</h3>
                  <span className="cond-kind">{c.kind}</span>
                  <p>{c.body}</p>
                </div>
              </article>
            ))}
          </div>
        </Section>

        {/* ---------------- 03 CORPUS ---------------- */}
        <Section id="corpus" n="03 — The corpus" title="Corpus-Monde: nine terms, frozen">
          <div className="prose">
            <p>
              569 argued cases from nine terms of the Roberts Court, assembled from three
              public sources and cross-validated vote by vote against the Supreme Court
              Database. The corpus was frozen on 2026-08-28: it has an identity now, and
              nothing may be added that changes it.
            </p>
          </div>

          <div className="facts">
            <div className="fact">
              <div className="fact-num">547 / 555</div>
              <span className="fact-label">SCDB argued cases matched by the pipeline (98.6%)</span>
            </div>
            <div className="fact">
              <div className="fact-num">79</div>
              <span className="fact-label">decisions handed down 5–4 — the Court at its most divided</span>
            </div>
            <div className="fact">
              <div className="fact-num">SHA-256</div>
              <span className="fact-label">every source file hashed; the corpus manifest is sealed in the repo</span>
            </div>
          </div>

          <div className="table-scroll">
            <table className="term-table">
              <thead>
                <tr>
                  <th scope="col">Term</th>
                  <th scope="col">Argued cases</th>
                  <th scope="col">Opinions</th>
                  <th scope="col">Decided 5–4</th>
                </tr>
              </thead>
              <tbody>
                {TERMS.map(([t, c, o, ff]) => (
                  <tr key={t}>
                    <td>{t}</td>
                    <td>{c}</td>
                    <td>{o}</td>
                    <td>{ff}</td>
                  </tr>
                ))}
                <tr className="total">
                  <td>Total</td>
                  <td>569</td>
                  <td>1,778</td>
                  <td>79</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="sources">
            <div className="source">
              <div className="source-name">CourtListener</div>
              <p>
                Bulk files (2026-06-30) and the v4 API: dockets, opinion clusters, oral
                argument audio and transcripts. Free Law Project.
              </p>
            </div>
            <div className="source">
              <div className="source-name">Supreme Court Database</div>
              <p>
                SCDB 2025_01, justice-centered: the vote of every justice in every case —
                the ground truth the models are judged against.
              </p>
            </div>
            <div className="source">
              <div className="source-name">Oyez</div>
              <p>
                Oral argument tapes and case summaries — the sound of the Court, which
                covers 98.6% of the corpus.
              </p>
            </div>
          </div>

          <div className="warts">
            <h3>Known imperfections, all documented</h3>
            <ul>
              <li>8 SCDB cases are not covered by the corpus — each one listed in the repo.</li>
              <li>22 in forma pauperis cases carry no documented SCDB votes.</li>
              <li>
                CourtListener's 2026-06-30 bulk files are truncated on S3 — measured,
                documented, no effect on this corpus.
              </li>
              <li>
                The same slip opinion is often stored several times; fine deduplication of
                texts happens in M1.5, after the freeze.
              </li>
            </ul>
          </div>
        </Section>

        {/* ---------------- 04 BASELINES ---------------- */}
        <Section id="baselines" n="04 — The baselines" title="The number to beat">
          <div className="prose">
            <p>
              Before any model claims to predict the Court, it must beat a spreadsheet.
              These are the numbers trivial rules achieve on the test split — OT2020–2023,
              225 labeled cases — fitted on nothing fancier than counting.
            </p>
          </div>

          <div className="baseline-list">
            {BASELINES.map((b) => (
              <div
                className={b.toBeat ? "baseline-row to-beat" : "baseline-row"}
                key={b.id}
              >
                <span className="baseline-id">{b.id}</span>
                <div>
                  <div className="baseline-name">{b.name}</div>
                  <span className="baseline-desc">{b.desc}</span>
                </div>
                <div className="baseline-value">
                  {b.value}
                  <span className="baseline-ci">{b.ci} Wilson 95%</span>
                </div>
              </div>
            ))}
          </div>

          <p className="punch">
            A model that cannot beat <span className="hl">63.7%</span> has learned nothing
            a spreadsheet doesn't already know.
          </p>

          <p className="footnote">
            Wilson 95% intervals throughout; one decimal, because precision beyond that
            would be theater. Cohen's κ is reported alongside every accuracy. Full tables,
            including per-term ideology drift and inter-judge agreement, live in{" "}
            <a href={REPO + "/blob/main/results/m2_baselines.md"}>results/m2_baselines.md</a>.
          </p>

          <div className="human-range">
            <div className="hr-cell">
              <span className="hr-label">Highest pair agreement</span>
              <p className="hr-pair">Kavanaugh — Roberts</p>
              <span className="hr-num">94.6%</span>
              <p className="hr-note">[91.6 – 96.5] — votes nearly in lockstep</p>
            </div>
            <div className="hr-cell low">
              <span className="hr-label">Lowest pair agreement</span>
              <p className="hr-pair">Alito — Sotomayor</p>
              <span className="hr-num">55.5%</span>
              <p className="hr-note">[51.2 – 59.8] — barely better than a coin</p>
            </div>
          </div>
          <p className="footnote">
            For scale: the justices' own range of agreement is the terrain the model walks.
          </p>
        </Section>

        {/* ---------------- 05 PROTOCOL ---------------- */}
        <Section id="protocol" n="05 — The protocol" title="A test sealed before it is run">
          <div className="prose">
            <p>
              Predictions are cheap if you can retry them. So the final examination —{" "}
              <span className="quiet">L'Épreuve Finale</span> — was sealed before any model
              was trained.
            </p>
          </div>

          <div className="steps">
            <div className="step">
              <span className="step-n">1</span>
              <div>
                <h3>Fifty cases, drawn by hash</h3>
                <p>
                  From the 79 decisions decided 5–4, fifty are drawn by a deterministic
                  random sample seeded with the SHA-256 of the sorted case list. Not a
                  curator's hand — arithmetic.
                </p>
              </div>
            </div>
            <div className="step">
              <span className="step-n">2</span>
              <div>
                <h3>The list stays sealed</h3>
                <p>
                  Only the hash of the sealed list is published. The selection cannot be
                  steered toward friendly cases, because nobody — including the author —
                  knows which cases are in it.
                </p>
              </div>
            </div>
            <div className="step">
              <span className="step-n">3</span>
              <div>
                <h3>Pre-registered, then run once</h3>
                <p>
                  The evaluation protocol is registered (OSF) before the single pass:
                  four conditions, same fifty cases, metrics fixed in advance.
                </p>
              </div>
            </div>
            <div className="step">
              <span className="step-n">4</span>
              <div>
                <h3>Published whatever it says</h3>
                <p>
                  No leaderboard grinding, no re-runs, no selective reporting. One pass,
                  and the results ship — including the boring ones and the embarrassing
                  ones.
                </p>
              </div>
            </div>
          </div>

          <p className="seal">
            <span className="k">sealed_list_sha256</span>{" "}
            596ea80ae2478082dca3a4aef85b370f0b30b7f121f5ffb2a59c6778ee652fee
            {"\n"}
            <span className="k">selection_seed</span> 0x8a400f4af9abb546 ·{" "}
            <span className="k">drawn_from</span> 79 five-four decisions
          </p>
        </Section>

        {/* ---------------- 06 ROADMAP ---------------- */}
        <Section id="roadmap" n="06 — The roadmap" title="Where this stands">
          <div className="milestones">
            {MILESTONES.map((m) => (
              <div className="milestone" key={m.id}>
                <span className="milestone-id">{m.id}</span>
                <div>
                  <h3>{m.title}</h3>
                  <p>{m.desc}</p>
                </div>
                <span className={"chip " + m.status}>{m.label}</span>
              </div>
            ))}
          </div>
          <p className="later-note">
            Later, and explicitly unpromised: an audio condition using the 98.6% of the
            corpus that has oral arguments; a model-vs-judge agreement matrix, to see
            whether a persona predicts its own justice better than it predicts the others;
            and an extension to the federal courts of appeals, for which the collection
            pipeline is already generic.
          </p>
        </Section>
      </main>

      {/* ---------------- FOOTER ---------------- */}
      <footer className="site-footer">
        <div className="wrap">
          <div className="footer-grid">
            <div>
              <div className="footer-brand">
                Legally Subjective
                <span className="brand-tag">Subjectivity, measured.</span>
              </div>
              <p className="creed">
                Built by an amateur, in the open, to the standards of the professionals —
                because the question deserved at least that.
              </p>
            </div>
            <div>
              <h4>Data</h4>
              <ul>
                <li>
                  <a href="https://www.courtlistener.com/">CourtListener</a> — Free Law
                  Project
                </li>
                <li>
                  <a href="http://scdb.wustl.edu/">Supreme Court Database</a> — Washington
                  University in St. Louis
                </li>
                <li>
                  <a href="https://www.oyez.org/">Oyez</a> — IIT Chicago-Kent
                </li>
              </ul>
              <h4 style={{ marginTop: "1.4rem" }}>License</h4>
              <ul>
                <li>Code — MIT</li>
                <li>Text and data — CC BY 4.0</li>
              </ul>
            </div>
            <div>
              <h4>This site</h4>
              <ul>
                <li>Static HTML — no server, no database</li>
                <li>No cookies, no analytics, no tracking</li>
                <li>No funding, no affiliation</li>
                <li>
                  <a href={REPO}>Source and data on GitHub</a>
                </li>
              </ul>
            </div>
          </div>

          <pre className="bibtex">{`@misc{harchelkorane2026legally,
  author = {Harch el Korane, Amine},
  title  = {Legally Subjective: Subjectivity, measured},
  year   = {2026},
  url    = {https://github.com/Vitalcheffe/legally-subjective},
}`}</pre>

          <div className="footer-bottom">
            <span>Data public. Methods public. Results, whatever they are.</span>
            <span>
              <a href={REPO}>GitHub</a> · <a href={REPO + "/blob/main/docs/04-PROTOCOLE.md"}>Protocol (FR)</a> ·{" "}
              <a href={REPO + "/blob/main/README.en.md"}>README (EN)</a>
            </span>
          </div>
        </div>
      </footer>
    </>
  );
}
