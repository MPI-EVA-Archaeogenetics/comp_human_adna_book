This is the code repository for the content of the online book on computational archaeogenetics developed at the [MPI for Evolutionary Anthropology](https://mpi-eva-archaeogenetics.github.io/comp_human_adna_book/poseidon.html).

## Rendering the book offline

You need the [Quarto](https://quarto.org) CLI installed for either of the below. All commands are run from the repository root.

### HTML (the online book)

```
quarto preview
```

This renders the book as-is and opens it in a browser with live-reload. A one-off render (no preview server) is `quarto render` (no `--to` needed; `html` is the default format), which writes to `docs/`.

### PDF

Requires a LaTeX distribution in addition to Quarto. If you don't have one, `quarto install tinytex` sets up TinyTeX (a minimal, Quarto-managed distribution) automatically.

```
QUARTO_PROFILE=pdf quarto render --to pdf
```

Output goes to `pdf-build/` — both the compiled PDF and the underlying `.tex` source (`keep-tex: true`). The `QUARTO_PROFILE=pdf` bit activates `_quarto-pdf.yml`, an overlay that adds PDF-specific settings (page margins, smaller font for wide code blocks, etc.) on top of the base `_quarto.yml` without touching the default HTML config — so a plain `quarto render`/`quarto preview` is completely unaffected by any of this.

**The PDF and HTML versions intentionally differ in a few places:**

- Two chapters use animated GIFs (`10_pca_mds`, `18_pmrread`); a still image has no way to represent motion, so the PDF shows a static first frame instead of the animation. Search those chapters' `.qmd` for `.content-visible when-format=` to see how the two versions are selected.
- A few chapters used HTML-only "margin notes" for citations (`reference-location: margin`, nested under `format: html:` in those chapters' frontmatter) — the PDF uses normal inline citations instead. This isn't just a style choice: Quarto's PDF template reserves screen space for margin notes in a way that conflicts with custom page margins, and setting both at once crashes Quarto's own layout filter (see the comments in `_quarto-pdf.yml` for the specifics, including a documented Quarto bug on the currently-used version, 1.3.450).
- A handful of very wide code/console-output blocks (pasted CLI transcripts, wide data tables) are shown in a smaller font in the PDF only, to keep them from overflowing the printed page — they display at normal size in HTML, where there's no fixed page width to worry about.

If you're adding a new chapter with wide figures or images sized in raw pixels (e.g. `{width="1200"}`), prefer a percentage width (`{width="90%"}`) instead — pixel widths translate literally to inches in the PDF and can overflow the page margin.
