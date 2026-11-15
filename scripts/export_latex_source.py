#!/usr/bin/env python3
"""Export a self-contained pdfLaTeX project, without Python or bank-level data."""
from pathlib import Path
import zipfile
r=Path(__file__).resolve().parents[1];m=r/'reports/manuscript';dest=r.parent/'fdic-report-latex-source.zip'
readme='''# FDIC academic report — pdfLaTeX source

Open main.tex and choose pdfLaTeX (not XeLaTeX/LuaLaTeX). On Overleaf, upload this
ZIP as a new project, set main.tex as the main document and select pdfLaTeX.
All vector figures and the local style/BibTeX database are included.
The title is Bank-Failure Early Warning Using FDIC Data. References starts on
its own page; BibTeX generates numbered entries and matching numeric citations.

For a local TeX Live/TinyTeX installation:

    pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
    bibtex main
    pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
    pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex

Packages include tex-gyre, newtx, oberdiek, vntex, microtype, babel-english,
hyphen-english, threeparttable, titlesec, placeins, setspace, caption, natbib,
bookmark, booktabs and geometry. No data download or model computation is needed.

main.tex is an editable static snapshot. The full GitHub-ready project also
contains the aggregate evidence and Python authoring source. Model and cost-policy
results are frozen. The report cover includes the public repository URL.
AI assistance remains disclosed in the project README.
The previous manuscript disclosure was removed at the author's request; the
assignment's report-level citation requirement still needs to be addressed.

Editorial guidance is recorded in EDITORIAL_REVIEW.md.

Typography draws on observed academic papers and the MIT-licensed template
https://github.com/pmichaillat/latex-paper. The local fdicpaper.sty is the style
actually compiled; the upstream paper.sty is not required.
'''
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('main.tex',(m/'main.tex').read_text().replace('../figures/paper/','figures/'))
 for name in ['fdicpaper.sty','references.bib']:z.write(m/name,name)
 for p in sorted((r/'reports/figures/paper').glob('*.pdf')):z.write(p,'figures/'+p.name)
 z.writestr('README.md',readme)
 z.write(r/'references/layout-template/LICENSE.md','LICENSE_TEMPLATE_REFERENCE.md')
 z.write(r/'docs/EDITORIAL_REVIEW.md','EDITORIAL_REVIEW.md')
print(dest)
