# Legally Subjective — The Visual Guide (LS-EXHIBIT-1.2)

> This document is the complete manual for producing **exhibit-grade visuals**
> for Legally Subjective — README banners, paper figures, and documentation
> art. It is adapted from the AEGIS Visual Guide (a physics-project visual
> system, proven on 45 shipped visuals) and re-grounded in this project's own
> design law: **UI-1.0 EXHIBIT — the interface is evidence.**
>
> Read it fully before touching a visual file. The bar: a visual that makes a
> statistical reviewer and an art director nod at the same time. Not one
> without the other.

---

## I. THE PHILOSOPHY — What separates a chart from an exhibit

### The absolute rule: EVERYTHING IS CENTERED

Every visual element is horizontally centered in the canvas. No left
alignment. No right alignment. The center axis is the spine. The only
exceptions are the tiny metadata stamps in the corners (docket id, seed,
window) — they alone live in the corners, 9px monospace, tertiary ink.

**Why?** Centered composition creates symmetric tension that pulls the eye
to the middle — to the subject. A left-aligned visual looks like a dashboard.
A centered visual looks like a filed exhibit. This project's interface is
evidence; exhibits are centered on the page.

### The second rule: NO CARDS, NO RADIUS, NO SHADOWS, NO GRADIENTS

Never put a rounded rectangle around content. No `border-radius`. No
`box-shadow`. No gradient fills of any kind. Separate elements with:

- **Whitespace** — the strongest separator
- **Typography** — size, weight, and ink density make the hierarchy
- **1px ink rules** between zones, **1px hairlines** inside them
- **The signal red** — used ONLY for the live variable, the highlight, the
  thing this exhibit is about

**Why?** Cards and shadows say "SaaS template". Rules and whitespace say
"court filing". The court does not round its corners.

### The third rule: THE AMBIENCE OF A FILING, NOT A DASHBOARD

A Legally Subjective visual must feel like a document entered into evidence:
white paper, dense tabular data, one red mark where the claim lives. Think:

- A filed appellate brief, typeset with institutional discipline
- *Bloomberg Terminal* density with *Swiss typography* restraint
- A forensics lab report — every number traces to a docket

---

## II. THE COLOR SYSTEM — One background, one ink, ONE signal

The house has exactly one palette. It is not negotiable.

```css
body {
  background: #ffffff;            /* paper — never pure-gray, never warm */
  color: #0a0a0a;                 /* ink */
}
:root {
  --paper:      #ffffff;          /* the one background */
  --paper-2:    #f7f7f5;          /* zebra rows, quiet fills */
  --ink:        #0a0a0a;          /* primary text */
  --ink-2:      #595959;          /* secondary text */
  --ink-3:      #8c8c8c;          /* tertiary / metadata */
  --rule:       #0a0a0a;          /* 1px zone rules — full ink */
  --hairline:   #e3e3e3;          /* 1px inner lines */
  --signal:     #e4002b;          /* THE red. One signal. */
  --signal-deep:#b40020;          /* pressed / dense signal */
}
```

### The data ramp — grayscale only

```css
--d1: #0a0a0a;   /* strongest data series */
--d2: #404040;
--d3: #737373;
--d4: #a6a6a6;
--d5: #d4d4d4;   /* faintest data series */
```

### The golden rule of the signal

Red `#e4002b` marks **the variable under examination** — and nothing else.
The sealed cases in red, the baseline to beat in red, the drawn justice in
red. If everything is red, nothing is. Target ratio: ~3–5% signal, 95–97%
ink-and-paper. Red is never decoration. Red is a claim.

**NEVER blue as a dominant color.** Never Tailwind blue-500. Never a
rainbow or jet colormap. Data series are distinguished by ink weight and
dash pattern, not by hue.

---

## III. THE TYPOGRAPHY — Grotesk speaks. Mono measures.

```css
body { font-family: 'Space Grotesk', -apple-system, sans-serif; }
.mono, .num, .meta, .stamp { font-family: 'IBM Plex Mono', ui-monospace, monospace; }
```

(For standalone HTML files, load both from Google Fonts — see §IX.)

### Typographic hierarchy

| Element | Size | Weight | Letter-spacing | Color |
|---|---|---|---|---|
| Main title | 88–104px | 700, Grotesk | -0.04em | ink |
| Subtitle / standfirst | 15–16px | 400 | normal | ink-2 |
| Section label | 12–13px | 500, Mono | 0.25em, UPPERCASE | ink-3 |
| Stats / big numbers | 22–30px | 600, Mono, tabular | -0.02em | ink |
| Signal number | same as stats | 600, Mono | -0.02em | signal |
| Labels | 9–11px | 400, Mono | 0.1–0.2em, UPPERCASE | ink-3 |
| Corner metadata | 9px | 400, Mono | 0.2em, UPPERCASE | ink-3 (faint) |
| Formulas / citations | 11–12px | 400, Mono | normal | ink-2 |

### The letter-spacing trick

UPPERCASE mono labels take `letter-spacing: 0.2em–0.3em` — the "case docket
stamp" look: spaced, technical, filed. Big grotesk titles take negative
tracking (`-0.04em`) — close-set, institutional. Every number that will be
compared to another number is set in mono with `font-variant-numeric:
tabular-nums`, so columns of figures align like a ledger.

---

## IV. THE GROUND — The three layers of paper

Every visual carries exactly three layers, in this order:

### 1. The paper (base layer)

Flat `#ffffff`. Never pure black, never cream. On it, structure is exposed:
1px full-ink rules (`--rule`) separate the major zones; 1px hairlines
(`--hairline`) structure the inside of a zone. Rules are horizontal and
vertical only. They are the bones of the exhibit.

### 2. The focal rule (focus layer)

Where AEGIS uses a radial glow, this house uses **the red signal mark** as
the focal mechanism: the one red element (a drawn segment, a sealed block,
a threshold line) is where the eye lands. If a visual needs additional
focus, use a **heavier ink weight** or a **denser hatch**, never a glow,
never a gradient, never a shadow.

### 3. The paper tooth (texture layer)

```html
<div class="tooth"></div>
```

```css
.tooth {
  position: absolute; inset: 0; pointer-events: none;
  opacity: 0.012;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)'%3E%3C/svg%3E");
}
```

Paper has tooth. Without this layer the ground reads as digital white; with
it, at ~1.2% opacity, it reads as *paper*. Subliminal, never noticed,
always felt.

---

## V. THE RENDER PIPELINE — HTML → PNG

### The method (adapted from 45 proven AEGIS renders)

1. **Write a standalone HTML file** with inline CSS. No external project
   files. Google Fonts `<link>` + inline `<script>` for procedural SVG only.

2. **Fix the exact body dimensions**:
   ```css
   body { width: 1920px; height: 800px; overflow: hidden; }
   ```
   Standard sizes: 1920×640 (banner), 1920×760 (standard exhibit),
   1920×800 (wide exhibit).

3. **Render headless**:
   ```bash
   agent-browser set viewport 1920 800
   agent-browser open "file:///…/docs/assets/hero.html"
   sleep 0.8        # let fonts + procedural SVG settle
   agent-browser screenshot …/hero.png
   ```

4. **Verify the PNG dimensions**:
   ```bash
   python3 -c "import struct; f=open('hero.png','rb').read(24); print(struct.unpack('>II', f[16:20]+f[20:24]))"
   ```

### Why HTML?

Pixel-perfect typographic control; procedural SVG for dense data; a
deterministic render (same browser, same image); files are diffable and
versioned. Every number in the SVG is generated from the real JSON — never
typed by hand.

---

## VI. PROCEDURAL SVG — For dense exhibits

Anything with more than ~30 elements (569 case ticks, a 13×13 matrix,
redaction bars) is generated by an inline `<script>` from **real data
inlined as JSON**, never drawn by hand.

```html
<svg id="ex" width="1600" height="600" viewBox="0 0 1600 600"></svg>
<script>
(function () {
  const svg = document.getElementById('ex');
  const NS = 'http://www.w3.org/2000/svg';
  // Real data, inlined from data/productions/*.json at build time:
  const TERMS = {"2015":72,"2016":69,"2017":65,"2018":72,"2019":60,"2020":56,"2021":62,"2022":55,"2023":58};
  // … build ticks, rules, labels from TERMS …
})();
</script>
```

### The seeded RNG

When a layout needs pseudo-randomness (jitter, hatch angles), use a seeded
generator so the same HTML always renders the same PNG:

```javascript
let seed = 1337;
function rnd() { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; }
```

Reproducibility is a house value: a figure that renders differently on
Tuesday than on Monday is not evidence.

---

## VII. LIGHT AND DARK — The two-face law (amended 2026-08-29)

> **Amendment 1.1.** The original house law was *one face, always the
> paper* — a white PNG under every scheme. It was overturned by the
> project owner after field review: a white slab glued into a dark
> GitHub README reads as a foreign object, not as a filed document.
> The law is amended in writing, as the house requires.

Every exhibit now ships as **two transparent SVG files, one per face**:
`name.light.svg` (dark ink, for light papers) and `name.dark.svg`
(light ink, for dark papers). Each file is a **fixed, statically-
resolved palette** — no CSS variables, no media queries, no runtime
switching — baked into a plain `<style>` block, so it renders
identically in every SVG consumer.

> **Amendment 1.2 — why one file failed.** LS-EXHIBIT-1.1 put a
> `prefers-color-scheme` media query *inside* the SVG with CSS
> variables switching the palette. It worked when the SVG was opened
> as a document — and **silently failed on GitHub**: README images
> are served through the camo proxy inside an `<img>` element, and an
> SVG rendered as an image is an isolated document whose internal
> media query does **not** follow the page's color scheme. Field
> result (measured 2026-08-29): the dark face never fired; a reader
> in GitHub dark got near-black ink `#0a0a0a` on GitHub's dark paper
> `#0d1117` — invisible text. The reliable mechanism is the one
> GitHub itself documents: **the page** picks the file.

The README mounts each exhibit with

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/name.dark.svg">
  <img src="docs/assets/name.light.svg" alt="…" width="100%">
</picture>
```

The media attribute is evaluated by **github.com's own HTML**, which
knows the reader's theme. It degrades honestly: a browser that ignores
the query shows the light face — never a broken one.

**Contrast is law, and it is enforced by the build.**
`scripts/qa_exhibits.py` gates every file: text tokens must hold
**WCAG AA (≥ 4.5:1)** against their target paper — light face against
`#ffffff`, dark face against GitHub dark `#0d1117`; matrix numerals
against their own cell fill; data marks ≥ 3:1; and the ink bounding
box must keep ≥ 20px of air on all four sides of the 1200px raster
(the margin law). Invisible ink is a build failure, not a review
finding. Amendment 1.2 also lifted the borderline tokens: light ink3
`#8c8c8c → #6e7379` (3.4 → 4.8:1), dark ink3 `#6e7681 → #768390`
(4.1 → 4.9:1), light hairline `#e3e3e3 → #d0d7de` (GitHub's own
border token), dark matrix m4 `#6e7681 → #768390` so in-cell numerals
clear AA against their fill.

The signal red keeps its perceptual weight per face (`#e4002b` on
white, 4.9:1 → `#ff4d6a` on GitHub dark, 5.9:1). Paired fills (the
agreement matrix bins) ship their own fill+text pairs per face, so
in-cell numbers never lose contrast in either face.

**Known limit, documented:** the `<picture>` query follows the
*browser* preference, not a manually-forced GitHub theme. A reader
whose OS is light but who forced GitHub dark gets the light face.
This is the standard behavior of GitHub's own adaptive-image
mechanism; it is accepted and documented rather than hidden.

**No background, ever.** The exhibit is transparent. It lives on the
reader's paper. Never draw a background rect, never bake a paper color
into a raster. If an element needs separation from the page, separate
it with a hairline or whitespace — never with a slab.

---

## VIII. TECHNIQUES SPECIFIC TO THIS PROJECT

### 1. The bench (13 seats)

The thirteen justices of the window as a row of seat marks: equal-width
slots separated by hairlines, each seat a stacked bar or a tick column of
that justice's record. Mid-window arrivals (Gorsuch, Kavanaugh, Barrett,
Jackson) get visibly shorter columns — the record is honestly shorter, and
the exhibit says so. Signal red marks the justice under examination.

### 2. The agreement matrix (13×13, 60 pairs)

- A square grid of cells; cell ink density encodes agreement (0.54–0.95).
- Grayscale ramp only (`--d1`…`--d5`, or alpha over ink).
- The extreme pairs (highest, lowest) may carry the signal red — one mark
  for the closest pair, one for the most opposed. Never a full red row.
- Diagonal is paper (a justice does not agree with themselves at 1.0 in
  this data — the diagonal is undefined, and the exhibit shows it as void,
  not as 100%).

### 3. Redaction bars (the sealed 50)

Fifty of the seventy-nine 5–4 decisions are sealed for the Final Test. The
signature visual: 79 rows/blocks; 50 of them carry a solid ink redaction
bar where the case name would be; 29 are legible. The redaction bar is
**full ink (#0a0a0a)** — blacked out like a classified filing — and the
*count* is in signal red. This is the project's most on-brand figure:
the experiment's honesty, rendered as censorship.

### 4. The wheel (THE DRAW)

The storefront interaction is a wheel of 13 segments. In static form: a
precise radial dial — 13 segments delimited by hairline spokes, segment
labels in 9px mono uppercase, ONE segment filled signal red with the drawn
justice's stamp and number (e.g. `GINSBURG · 51 ±7 · 209 VOTES`). Ticks,
not decorations. The wheel reads as a calibrated instrument, not a casino.

### 5. Baseline forest (the number to beat)

Horizontal bars for each M2 baseline with Wilson 95% intervals as bracket
lines; every figure mono tabular; the per-justice ideology baseline
(63.7%) is the signal-red bar — the number every future model must beat.
Bars are ink; intervals are hairline brackets; the claim is red.

### 6. The corpus window (term timeline)

OT2015→OT2023 as nine columns of case ticks (569 total); 5–4 decisions
overlaid as denser marks; the window's bounds stamped in mono. Reads as a
seismograph of the docket — tick columns, hairline grid, no axis boxes.

---

## IX. THE STRUCTURE OF A VISUAL FILE

The base template every exhibit follows:

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  width:1920px;height:800px;overflow:hidden;
  background:#ffffff;color:#0a0a0a;
  font-family:'Space Grotesk',-apple-system,sans-serif;
}
.mono{font-family:'IBM Plex Mono',ui-monospace,monospace;font-variant-numeric:tabular-nums}
.tooth{position:absolute;inset:0;pointer-events:none;opacity:0.012;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)'/%3E%3C/svg%3E")}
.wrap{width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative}
.title{text-align:center}
.title h1{font-size:96px;font-weight:700;color:#0a0a0a;letter-spacing:-0.04em;line-height:1}
.title .line{width:48px;height:2px;background:#e4002b;margin:24px auto}
.title p{font-size:15px;color:#595959;max-width:600px;margin:0 auto;line-height:1.6}
.corner{position:absolute;font-size:9px;color:#8c8c8c;letter-spacing:0.2em;font-family:'IBM Plex Mono',monospace;text-transform:uppercase}
.tl{top:32px;left:32px}.tr{top:32px;right:32px}
.meta{position:absolute;bottom:24px;left:50%;transform:translateX(-50%);font-size:9px;color:#8c8c8c;letter-spacing:0.2em;font-family:'IBM Plex Mono',monospace;text-transform:uppercase}
</style>
</head>
<body>
<div class="wrap">
  <div class="tooth"></div>

  <!-- Procedural SVG exhibit -->
  <svg id="ex" width="1600" height="520" viewBox="0 0 1600 520"></svg>

  <div class="title">
    <h1>EXHIBIT TITLE</h1>
    <div class="line"></div>
    <p>One-sentence standfirst, max 600px wide.</p>
  </div>

  <div class="corner tl">LEGALLY SUBJECTIVE / LS-EXHIBIT-1.0</div>
  <div class="corner tr">CORPUS-MONDE V1 · 569 CASES</div>
  <div class="meta">OT2015–OT2023 · SCDB 2025_01 · FILED 2026-08-28</div>
</div>
<script>
/* Procedural SVG from real data — seeded if stochastic */
</script>
</body>
</html>
```

---

## X. QUALITY — The end-of-run checklist

Before an exhibit is declared filed, EVERY box must pass:

- [ ] `body{width:…px;height:…px;overflow:hidden}` — exact dimensions
- [ ] Everything horizontally centered (flex + `align-items:center`)
- [ ] Paper `#ffffff`, one ink `#0a0a0a`, ONE signal `#e4002b`
- [ ] Signal red covers ≤5% of the visual area
- [ ] Paper tooth layer present (fractal noise, ~1.2% opacity)
- [ ] 1px rules between zones; hairlines inside; no boxes around the canvas
- [ ] NO border-radius, NO box-shadow, NO gradient, NO glow
- [ ] Space Grotesk (display) + IBM Plex Mono (all numbers)
- [ ] All comparable numbers in tabular mono
- [ ] No emojis, no badges, no illustrations
- [ ] Corner metadata: 9px mono uppercase, `letter-spacing: 0.2em`
- [ ] Bottom meta stamp: 9px mono uppercase
- [ ] The exhibit shows a LIVE claim — a drawn segment, a sealed block, a
      threshold to beat — not a dead diagram
- [ ] Every number traces to `data/` or `results/` (or it does not exist)
- [ ] If stochastic: seeded RNG, documented
- [ ] PNG dimensions verified with `struct.unpack`
- [ ] File committed next to its HTML source (the PNG is evidence; the
      HTML is the deposition)

---

## XI. THE ERRORS TO NEVER MAKE

1. **Using a second accent color.** There is one signal. Adding amber,
   blue, or green "for contrast" breaks the house law. Contrast comes from
   ink weight and whitespace.

2. **Rounding corners or dropping shadows.** Cards scream template. The
   court does not round its corners.

3. **Red as decoration.** Red is a claim about a specific datum. If a red
   element cannot be traced to a sentence in the docs, delete it.

4. **Uppercase mono without letter-spacing.** `0.2em` minimum, always.

5. **Forgetting the paper tooth.** It is 80% of the difference between
   "digital white" and "paper". Subliminal is the point.

6. **Drawing data by hand.** 569 ticks are generated by script from the
   JSON, always. A hand-typed number is a fabricated number.

7. **Non-tabular numbers.** If two figures can be compared, they must
   share a mono tabular column. Ledger discipline.

8. **Random PNG dimensions.** 1920×640 / 1920×760 / 1920×800. Verify with
   python3 `struct.unpack`.

9. **A dark variant.** There is none. One face — the paper. (See §VII for
   the documented rule-break.)

10. **Emojis.** Never. An icon is inline SVG or nothing.

11. **A dead exhibit.** Every visual must contain one live element — the
    drawn seat, the redacted block, the bar to beat. Otherwise it is
    clip-art, not evidence.

---

## XII. RENDERING — Exact commands

The exhibits are **generated as SVG directly from the data** — no HTML
mock, no browser, no screenshot step. Text is shaped with HarfBuzz and
written as paths (`scripts/ls_svg.py`), so the exact typography
(Space Grotesk + IBM Plex Mono, both SIL OFL, sources in
`scripts/fonts/` with licenses in `docs/assets/fonts/`) renders
identically on every machine, with no font dependency and no CSP risk.

```bash
# from the repo root — regenerates all six exhibits
python3 scripts/make_exhibits.py   # -> docs/assets/*.svg
```

The draw in `the-draw.svg` is deterministic and documented: the seed is
`SHA-256("LS-EXHIBIT-1.1|THE-DRAW|bench-13")`, drawn with Random MT —
same convention as the sealed-case selection.

*(Historical note — the 1.0 rendering pipeline above was screenshot-based;
it was retired with amendment 1.1. The HTML mocks and PNG rasters were
removed from the repository; `git log` keeps their memory.)*

---

## XIII. THE AESTHETIC — The final word

Legally Subjective measures judicial subjectivity. Its visuals must have
the discipline of a court filing and the pull of a front page: a page from
*Nature* that was entered into evidence.

**Discipline without pull** = a correct chart nobody looks at.
**Pull without discipline** = an infographic nobody believes.
**Both** = an exhibit. People look at it, believe it, and cite it.

Every visual must pass the bench test: would a statistical reviewer sign
it, and would a stranger stop scrolling for it? If either answer is no,
it is not filed yet.

The system is set. The paper is white. The red is loaded. Make exhibits.

---

> This guide is alive. It was adapted from the AEGIS Visual Guide (the
> physics-project original) and re-grounded in UI-1.0 EXHIBIT. If you break
> a rule and it renders better, document why — the house law says the
> paper is the paper, and the law can be amended only in writing.
