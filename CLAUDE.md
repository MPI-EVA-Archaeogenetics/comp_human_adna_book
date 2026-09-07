# CLAUDE.md

Context for Claude Code sessions working in this repo.

## What this repo is

A Quarto book (`_quarto.yml`, `project: type: book`) — *Computational
Methods for human population genetics and ancient DNA* — with one chapter
per numbered subfolder (`3_eager/`, `8_fst/`, `11_mobest/`, etc.), each a
`.qmd` file, some with executable R chunks. Normally rendered to HTML into
`docs/` for GitHub Pages.

## Current work: Quarto → LaTeX conversion

Goal: produce a clean, minimal, Springer-book-appropriate LaTeX version of
the book, structured as one `.tex` file per chapter plus a `master.tex`
that assembles them — for upload to an institute-internal Overleaf
instance (manual zip upload; that Overleaf instance is not git-integrated
and Claude has no network access to it).

**Status as of 2026-09-04**: fully working, end-to-end, on branch
`latex-conversion`. Nothing has been committed yet — see `git status`.
Changed/added: `.gitignore`, `references.bib` (two bugfixes, see below),
`scripts/build_latex.py` (new), `latex/` (new, generated output).

### How to rebuild

```
python3 scripts/build_latex.py                      # all chapters
python3 scripts/build_latex.py --chapters 05_fst,08_mobest   # subset, for faster iteration
```

Re-run this after editing any chapter `.qmd` or `references.bib`. It
regenerates `latex/` from scratch each time — don't hand-edit files under
`latex/`, edits will be lost.

### How to compile the PDF locally

TinyTeX is already installed (via `quarto install tinytex`, done in this
session) at `~/Library/TinyTeX`, not on the default `PATH`:

```
export PATH="$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"
cd latex
xelatex -interaction=nonstopmode master.tex
bibtex master
xelatex -interaction=nonstopmode master.tex
xelatex -interaction=nonstopmode master.tex   # two passes after bibtex, to resolve refs/citations
```

`tlmgr install <pkg>` is currently blocked here: local TeX Live (2025) is
older than the remote repo (2026) and `tlmgr` refuses cross-release
installs without `update-tlmgr-latest --update` first. Packages needed so
far (`tcolorbox`, `soul`) were already present; if compiling hits a
missing package, that's the likely blocker — see the TeX Live upgrade
docs, or install the package manually.

### Design decisions (read before changing the approach)

- **Each chapter is rendered standalone** (Quarto invoked on a copy of
  the chapter placed *outside* the book project, so no `_quarto.yml` is
  discoverable upward), not as part of one combined book render. This was
  a deliberate pivot: rendering the whole book at once merges all
  chapters into a single `.tex`, and reliably splitting that back into
  per-chapter files turned out to be fragile — worse, `11_mobest/mobest.qmd`
  uses `#` where the style guide calls for `##`, and in a merged
  book-context render those stray `#`s each became their own `\chapter`.
  Standalone-per-file rendering sidesteps both problems: one file in, one
  file out, and each chapter's own `shift-heading-level-by` (mobest
  already carries one, evidently a prior author fix for the same issue)
  is respected.
- Quarto's "title becomes the chapter heading" behavior is a **book
  project-only feature** — a standalone render never emits `\chapter{}`
  from YAML `title:`. The script synthesizes `\chapter{<title>}` itself
  by extracting `\title{...}` from the raw rendered preamble.
- `documentclass: book` + `top-level-division: chapter` only take effect
  when set via a `_quarto.yml` in the render directory — passing them as
  `--metadata` CLI flags does *not* override Quarto's own format
  resolution for a non-book-project render (tested; CLI flags for
  `documentclass` were silently ignored/overridden back to `scrartcl`).
  The build script writes a throwaway `_quarto.yml` into each temp render
  dir for this reason.
- Per-chapter frontmatter (`reference-location: margin`,
  `citation-location: margin`, `toc: true`, used in some chapters for the
  HTML build's margin-notes layout) **overrides** both CLI `--metadata`
  and a `_quarto.yml` format block — Quarto's precedence is
  document-frontmatter > project/format config. The script strips these
  three keys from each chapter's copied frontmatter before rendering.
- Citations use `cite-method: natbib` → clean `\citep{}`/`\citet{}`
  against `references.bib` directly, not pre-flattened citeproc text.
- Callout boxes (`callout-note/tip/warning/caution`) keep Quarto's
  `tcolorbox`-based rendering (handles nested content correctly, and
  `tcolorbox` is a standard, common package) but with `callout-icon:
  false` and all accent colors overridden to grayscale in the shared
  preamble — no reliance on color to distinguish callout types, print/B&W
  friendly.
- `\includegraphics` paths are rewritten to be relative to `master.tex`
  (`chapters/<slug>/...`) and chapters are `\input` (not `\subimport`) —
  the `import` package would have been the "correct"/cleaner mechanism
  but isn't installed and `tlmgr` is blocked (see above); path-rewriting
  avoids the dependency entirely, which is arguably more in the spirit of
  "minimal standard LaTeX" anyway.
- Section/subsection `\label{}`/`\hypertarget{}` names are namespaced
  with the chapter slug (e.g. `05_fst:theory-primer`) — Quarto generates
  short slugs that were unique within their own standalone HTML page but
  collided once every chapter shares one label namespace in the merged
  book (3 collisions found: `output`, `theory`, `usage`).
- Two bugs were found and fixed **in the canonical `references.bib`**
  (not just worked around in the LaTeX output, since they're real data
  bugs): two entries had a literal unescaped `&` in the journal name
  ("Nature Ecology & Evolution") — BibTeX requires `\&`.
- Two animated GIFs (`10_pca_mds/pca.gif`, `18_pmrread/Alacamli.TS1.gif`)
  are frozen to a static first-frame PNG during the build (via Pillow) —
  LaTeX/xelatex can't size or embed an animated GIF, and a print book has
  no equivalent of motion anyway.
- Currently uses a generic `book` documentclass, per user preference
  (no Springer template in hand yet). Swappable later.

### Known follow-ups (not yet addressed, see `latex/README.md`)

- A few wide console-output/table dumps (long shell commands, wide
  tab-separated statistics tables) overflow the page margin. Fixing this
  properly needs the `fvextra` package (auto line-wrapping in verbatim
  blocks) which isn't installed and `tlmgr` is blocked; worked around
  with a smaller code font size only, which doesn't fully solve the
  widest cases.
- A handful of emoji characters used informally in prose (💡 ▶️ 🔍 ❗ ⤵️)
  have no glyph in the default Latin Modern font — missing-character
  warnings, doesn't block compilation.
- `references.bib` has two exact-duplicate entries (`Wickham2019`,
  `prüfer2021`, each defined twice) — harmless for BibTeX (uses the
  first, warns), worth deduplicating separately.

### Not yet done

- Nothing committed to git (user wanted to review the PDF first).
- No Overleaf upload yet (manual zip upload planned, no git bridge on
  that instance).
- No Springer document class swapped in yet.
