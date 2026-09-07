#!/usr/bin/env python3
"""
Render each book chapter (.qmd) standalone to LaTeX and assemble a
Springer-friendly, Overleaf-ready LaTeX project under latex/.

Each chapter is rendered *outside* the Quarto book project (in an isolated
temp dir with no reachable _quarto.yml), forced into book/chapter mode via
--metadata flags. This gives one self-contained .tex file per source
chapter, regardless of how many top-level (#) headings that chapter
happens to contain -- which matters because at least one chapter
(11_mobest) uses # for what should be ## sub-sections; we auto-detect and
demote any extra top-level headings after the first.

Usage:
    python3 scripts/build_latex.py [--chapters slug1,slug2,...]
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRATCH_ROOT = Path(
    "/private/tmp/claude-502/-Users-stephan-schiffels-Desktop-Book-Working/"
    "e067d6c6-e7ba-45d0-ba41-eebb574eeca8/scratchpad/latex_render_tmp"
)
LATEX_OUT = REPO_ROOT / "latex"

# (source qmd relative to repo root, output slug, chapter dir or None if at repo root)
CHAPTERS = [
    ("index.qmd", "00_preface", None),
    ("3_eager/eager.qmd", "01_eager", "3_eager"),
    ("4_quality_control/quality_control.qmd", "02_quality_control", "4_quality_control"),
    ("5_contamination/authentiCT.qmd", "03_authentict", "5_contamination"),
    ("6_poseidon/poseidon.qmd", "04_poseidon", "6_poseidon"),
    ("8_fst/fst.qmd", "05_fst", "8_fst"),
    ("9_fstats/fstats.qmd", "06_fstats", "9_fstats"),
    ("10_pca_mds/pca_mds.qmd", "07_pca_mds", "10_pca_mds"),
    ("11_mobest/mobest.qmd", "08_mobest", "11_mobest"),
    ("14_qpgraph/qpgraph.qmd", "09_qpgraph", "14_qpgraph"),
    ("18_pmrread/pmrread.qmd", "10_pmrread", "18_pmrread"),
    ("27_yleaf/yleaf.qmd", "11_yleaf", "27_yleaf"),
    ("28_admixfrog/admixfrog.qmd", "12_admixfrog", "28_admixfrog"),
    ("31_quarto/Quarto_intro.qmd", "13_quarto_intro", "31_quarto"),
]

RENDER_QUARTO_YML = """\
format:
  latex:
    documentclass: book
    top-level-division: chapter
    cite-method: natbib
    reference-location: document
    citation-location: document
    callout-icon: false
    toc: false
    number-sections: true
"""

# Per-chapter frontmatter keys that override the above _quarto.yml format
# defaults (document frontmatter wins over project/format config in Quarto),
# so we strip them from each chapter's own YAML header before rendering.
FRONTMATTER_KEYS_TO_STRIP = {"reference-location", "citation-location", "toc"}

HEADING_DEMOTE_ORDER = [
    (r"\subsubsection", r"\paragraph"),
    (r"\subsection", r"\subsubsection"),
    (r"\section", r"\subsection"),
    (r"\chapter", r"\section"),
]

CROSS_QMD_LINK_RE = re.compile(r"\\href\{[^}]*\.qmd\}\{([^}]*)\}", re.DOTALL)
CHAPTER_MARK_RE = re.compile(r"\\chapter\*?\{")
INCLUDEGRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")
TITLE_RE = re.compile(r"^\\title\{(.*)\}\s*$", re.MULTILINE)


def run(cmd, cwd):
    print(f"  $ {' '.join(cmd)}  (cwd={cwd})")
    subprocess.run(cmd, cwd=cwd, check=True)


def strip_frontmatter_overrides(qmd_path):
    text = qmd_path.read_text()
    if not text.startswith("---"):
        return  # no YAML frontmatter (e.g. index.qmd)
    end = text.find("\n---", 3)
    if end == -1:
        return
    header, rest = text[: end + 4], text[end + 4 :]
    lines = header.splitlines()
    kept = [
        ln for ln in lines
        if not any(ln.strip().startswith(f"{k}:") for k in FRONTMATTER_KEYS_TO_STRIP)
    ]
    qmd_path.write_text("\n".join(kept) + "\n" + rest)


COLUMN_MARGIN_DIV_RE = re.compile(
    r"^:{3,4}[ \t]*column-margin[ \t]*$\n(.*?)^:{3,4}[ \t]*$\n?", re.MULTILINE | re.DOTALL
)


def strip_column_margin_divs(qmd_path):
    """Unwrap ::: column-margin fenced divs (a Quarto/tufte-style layout
    feature with no equivalent in a standard book class) -- keep the
    content, drop the margin placement, matching our decision to print
    citations/notes in the normal text flow rather than the margin."""
    text = qmd_path.read_text()
    new_text = COLUMN_MARGIN_DIV_RE.sub(lambda m: m.group(1), text)
    if new_text != text:
        qmd_path.write_text(new_text)


CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitize_control_chars(qmd_path):
    """Strip stray C0 control characters (e.g. a vertical tab left over from
    a Word/Google Docs paste) that LaTeX chokes on but Quarto/HTML silently
    tolerates."""
    text = qmd_path.read_text()
    new_text = CONTROL_CHAR_RE.sub(" ", text)
    if new_text != text:
        qmd_path.write_text(new_text)


def render_chapter(src_qmd_rel, chapter_dir_rel):
    """Copy chapter source into an isolated temp dir and render it standalone."""
    tmp = SCRATCH_ROOT / src_qmd_rel.replace("/", "_")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    # Always need references.bib at the same relative depth the chapter expects.
    shutil.copy(REPO_ROOT / "references.bib", tmp / "references.bib")
    (tmp / "_quarto.yml").write_text(RENDER_QUARTO_YML)

    src_qmd = REPO_ROOT / src_qmd_rel
    if chapter_dir_rel is None:
        # e.g. index.qmd sitting at repo root
        shutil.copy(src_qmd, tmp / src_qmd.name)
        render_target = tmp / src_qmd.name
        render_cwd = tmp
    else:
        src_dir = REPO_ROOT / chapter_dir_rel
        dst_dir = tmp / chapter_dir_rel
        shutil.copytree(src_dir, dst_dir)
        render_target = dst_dir / src_qmd.name
        render_cwd = tmp

    sanitize_control_chars(render_target)
    strip_frontmatter_overrides(render_target)
    strip_column_margin_divs(render_target)

    cmd = ["quarto", "render", str(render_target.relative_to(render_cwd)), "--to", "latex"]
    run(cmd, cwd=render_cwd)

    tex_path = render_target.with_suffix(".tex")
    return tex_path, render_target.parent


def extract_body(raw_tex):
    m = re.search(r"\\begin\{document\}(.*)\\end\{document\}", raw_tex, re.DOTALL)
    if not m:
        raise RuntimeError("Could not find \\begin{document}...\\end{document}")
    body = m.group(1)
    # Drop \frontmatter/\maketitle/... boilerplate: real content starts after \mainmatter.
    mm = re.search(r"\\mainmatter\b", body)
    if mm:
        body = body[mm.end():]
    # Drop \backmatter and any per-chapter \bibliography{} call: the book's
    # bibliography is emitted once, globally, at the end of master.tex instead.
    bm = re.search(r"\\backmatter\b", body)
    if bm:
        body = body[: bm.start()]
    return body.strip() + "\n"


def extract_title(raw_tex):
    m = TITLE_RE.search(raw_tex)
    return m.group(1) if m else None


def demote_all_headings(text):
    for old, new in HEADING_DEMOTE_ORDER:
        text = re.sub(re.escape(old) + r"(?![a-zA-Z])", new, text)
    return text.replace(r"\addcontentsline{toc}{chapter}", r"\addcontentsline{toc}{section}")


def fix_cross_chapter_links(body):
    return CROSS_QMD_LINK_RE.sub(lambda m: m.group(1), body)


LABEL_REF_RE = re.compile(r"\\(label|ref|Cref|cref|autoref|nameref|hypertarget|hyperlink)\{([^}]+)\}")


def namespace_labels(body, slug):
    """Quarto generates short, human-readable \\label{}s per chapter (e.g.
    \\label{theory} or \\label{output}) that were unique within their own
    standalone HTML page but collide once every chapter shares one label
    namespace in the merged book. Prefix them with the chapter slug."""

    def rewrite(m):
        cmd, ident = m.group(1), m.group(2)
        if ident.startswith("chap:"):
            return m.group(0)
        return f"\\{cmd}{{{slug}:{ident}}}"

    return LABEL_REF_RE.sub(rewrite, body)


def copy_assets_and_rewrite_paths(body, render_dir, out_chapter_dir, slug):
    """Copy every asset an \\includegraphics call references into
    latex/chapters/<slug>/..., and rewrite the path in `body` to be
    relative to master.tex (chapters/<slug>/...) instead of to the
    chapter's own directory -- since chapters are \\input (not
    \\subimport'd) from master.tex, includegraphics paths must resolve
    from master.tex's own location.
    """
    def rewrite(m):
        rel_path = m.group(1)
        src = render_dir / rel_path
        candidates = [src] if src.exists() else []
        if not candidates:
            for ext in (".pdf", ".png", ".jpg", ".jpeg"):
                cand = render_dir / (rel_path + ext)
                if cand.exists():
                    candidates = [cand]
                    break
        if not candidates:
            print(f"  WARNING: could not find asset for \\includegraphics{{{rel_path}}}")
            return m.group(0)
        src = candidates[0]
        dst = out_chapter_dir / src.relative_to(render_dir)
        dst.parent.mkdir(parents=True, exist_ok=True)

        if src.suffix.lower() == ".gif":
            # LaTeX/xelatex can't size an animated GIF; freeze its first
            # frame to a PNG instead (a print book has no motion anyway).
            from PIL import Image

            dst = dst.with_suffix(".png")
            print(f"  -> freezing first frame of {src.name} to {dst.name}")
            with Image.open(src) as im:
                im.convert("RGB").save(dst)
            rel_out = dst.relative_to(out_chapter_dir)
        else:
            shutil.copy(src, dst)
            rel_out = src.relative_to(render_dir)

        new_rel = f"chapters/{slug}/{rel_out.as_posix()}"
        return m.group(0).replace(rel_path, new_rel)

    return INCLUDEGRAPHICS_RE.sub(rewrite, body)


def build_chapter(src_qmd_rel, slug, chapter_dir_rel):
    print(f"[{slug}] rendering {src_qmd_rel} ...")
    tex_path, render_dir = render_chapter(src_qmd_rel, chapter_dir_rel)
    raw_tex = tex_path.read_text()

    body = extract_body(raw_tex)
    title = extract_title(raw_tex)

    if title:
        # Quarto only auto-synthesizes a \chapter heading from the YAML title
        # inside a real book-project render; standalone, the body never gets
        # one. Any \chapter markers actually present in the body are stray
        # (mis-leveled headings in the source) and must be demoted so the
        # synthesized title heading is the file's one true chapter.
        if CHAPTER_MARK_RE.search(body):
            print("  -> found stray \\chapter marker(s) in body, demoting")
            body = demote_all_headings(body)
        body = f"\\chapter{{{title}}}\\label{{chap:{slug}}}\n\n" + body
    else:
        n_chapters = len(CHAPTER_MARK_RE.findall(body))
        if n_chapters == 0:
            print("  -> WARNING: no title and no \\chapter heading found in body")
        elif n_chapters > 1:
            print(f"  -> found {n_chapters} \\chapter markers, demoting all but the first")
            first_end = CHAPTER_MARK_RE.search(body).end()
            # demote everything from the second marker onward
            second = list(CHAPTER_MARK_RE.finditer(body))[1]
            head, tail = body[: second.start()], body[second.start() :]
            body = head + demote_all_headings(tail)

    body = fix_cross_chapter_links(body)
    body = namespace_labels(body, slug)

    out_dir = LATEX_OUT / "chapters" / slug
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    body = copy_assets_and_rewrite_paths(body, render_dir, out_dir, slug)

    out_tex = out_dir / f"{slug}.tex"
    out_tex.write_text(body)
    print(f"  -> wrote {out_tex.relative_to(REPO_ROOT)}")

    return raw_tex


def extract_preamble(raw_tex):
    m = re.search(r"(.*)\\begin\{document\}", raw_tex, re.DOTALL)
    return m.group(1) if m else ""


# Grayscale replacements for Quarto's default colored callout accents --
# print-friendly, no reliance on color to distinguish callout types (the
# bold title text -- Note/Tip/Warning/Caution -- already does that).
CALLOUT_COLOR_OVERRIDES = """\
\\definecolor{quarto-callout-color}{HTML}{6E6E6E}
\\definecolor{quarto-callout-note-color}{HTML}{404040}
\\definecolor{quarto-callout-important-color}{HTML}{404040}
\\definecolor{quarto-callout-warning-color}{HTML}{404040}
\\definecolor{quarto-callout-tip-color}{HTML}{404040}
\\definecolor{quarto-callout-caution-color}{HTML}{404040}
\\definecolor{quarto-callout-color-frame}{HTML}{999999}
\\definecolor{quarto-callout-note-color-frame}{HTML}{999999}
\\definecolor{quarto-callout-important-color-frame}{HTML}{999999}
\\definecolor{quarto-callout-warning-color-frame}{HTML}{999999}
\\definecolor{quarto-callout-tip-color-frame}{HTML}{999999}
\\definecolor{quarto-callout-caution-color-frame}{HTML}{999999}
"""

CALLOUT_COLOR_RE = re.compile(
    r"\\definecolor\{quarto-callout-[a-z-]*color[a-z-]*\}\{HTML\}\{[0-9A-Fa-f]{6}\}\n?"
)


def build_master_preamble(raw_tex_for_preamble):
    preamble = extract_preamble(raw_tex_for_preamble)
    # drop the per-chapter \title/\author/\date and \hypersetup{} -- the
    # book-level ones (set below) replace them.
    preamble = re.sub(r"\\title\{.*\}\n\\author\{.*\}\n\\date\{.*\}\n?", "", preamble)
    preamble = re.sub(r"\\hypersetup\{.*?pdfcreator=\{LaTeX via pandoc\}\}\n?", "", preamble, flags=re.DOTALL)
    # drop the early \bibliographystyle -- master.tex sets it once, right
    # before \bibliography at the end.
    preamble = preamble.replace("\\bibliographystyle{plainnat}\n", "")
    preamble = preamble.replace(
        r"\@ifpackageloaded{fontawesome5}{}{\usepackage{fontawesome5}}" "\n", ""
    )
    preamble = CALLOUT_COLOR_RE.sub("", preamble)
    preamble = preamble.rstrip() + "\n\n" + CALLOUT_COLOR_OVERRIDES
    # some chapters use pandoc's {.underline} span (e.g. 5_contamination),
    # which needs \ul from the soul package -- not always pulled in by a
    # single chapter's own preamble, so add it unconditionally here.
    preamble += "\\usepackage{soul}\n"
    # Shrink code-block font size to reduce (not eliminate) margin overflow
    # from long shell commands / wide console output -- plain fancyvrb (no
    # fvextra available here) can't auto-wrap long lines, so some wide
    # tab-separated data dumps will still overflow; flagged separately.
    preamble = preamble.replace(
        r"\DefineVerbatimEnvironment{Highlighting}{Verbatim}{commandchars=\\\{\}}",
        r"\DefineVerbatimEnvironment{Highlighting}{Verbatim}{commandchars=\\\{\},fontsize=\small}",
    )
    return preamble


BOOK_TITLE = "Computational Methods for human population genetics and ancient DNA"
BOOK_AUTHOR = "Various enthusiasts at the MPI-EVA"
BOOK_DATE = "2023-09-21"


def write_master_tex(built_slugs, preamble):
    lines = [preamble.rstrip(), ""]
    lines += [
        r"\hypersetup{",
        f"  pdftitle={{{BOOK_TITLE}}},",
        f"  pdfauthor={{{BOOK_AUTHOR}}},",
        "  hidelinks,",
        "  pdfcreator={LaTeX via pandoc, assembled via scripts/build_latex.py}}",
        "",
        f"\\title{{{BOOK_TITLE}}}",
        f"\\author{{{BOOK_AUTHOR}}}",
        f"\\date{{{BOOK_DATE}}}",
        "",
        r"\begin{document}",
        r"\frontmatter",
        r"\maketitle",
        r"\tableofcontents",
        "",
    ]

    mainmatter_started = False
    for slug in built_slugs:
        if slug != "00_preface" and not mainmatter_started:
            lines.append(r"\mainmatter")
            mainmatter_started = True
        lines.append(f"\\input{{chapters/{slug}/{slug}}}")
        lines.append("")

    lines += [
        r"\backmatter",
        r"\chapter*{References}",
        r"\addcontentsline{toc}{chapter}{References}",
        r"\bibliographystyle{plainnat}",
        r"\bibliography{references}",
        "",
        r"\end{document}",
    ]

    (LATEX_OUT / "master.tex").write_text("\n".join(lines) + "\n")
    print("Wrote latex/master.tex")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapters", help="comma-separated slugs to build (default: all)")
    args = parser.parse_args()

    wanted = set(args.chapters.split(",")) if args.chapters else None

    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    (LATEX_OUT / "chapters").mkdir(parents=True, exist_ok=True)

    preamble_raw_tex = None
    built_slugs = []
    for src_qmd_rel, slug, chapter_dir_rel in CHAPTERS:
        if wanted and slug not in wanted:
            continue
        raw_tex = build_chapter(src_qmd_rel, slug, chapter_dir_rel)
        built_slugs.append(slug)
        if slug == "05_fst":
            # fst is the most feature-complete chapter (code, figures,
            # callouts, citations), so its preamble carries every package
            # the book as a whole needs.
            preamble_raw_tex = raw_tex

    if preamble_raw_tex:
        shutil.copy(REPO_ROOT / "references.bib", LATEX_OUT / "references.bib")
        write_master_tex(built_slugs, build_master_preamble(preamble_raw_tex))
    else:
        print("NOTE: 05_fst not in this run, skipping master.tex (re)generation")

    print("Done.")


if __name__ == "__main__":
    main()
