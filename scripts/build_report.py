#!/usr/bin/env python3
"""Generate editable TeX and compile it with pdfLaTeX/BibTeX only.

Inputs are aggregate evidence, the content source, and vector PDF charts.
No model fitting or holdout scoring is performed.
"""
from pathlib import Path
from html.parser import HTMLParser
import argparse,csv,html,json,os,re,runpy,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1];T=ROOT/'reports/tables';M=ROOT/'reports/manuscript'
read=lambda n:list(csv.DictReader((T/n).open()))
load=lambda n:json.loads((T/n).read_text())
author=json.loads((ROOT/'docs/author.json').read_text());policy=json.loads((ROOT/'docs/cost_policy.json').read_text())
CITES={1:'fdicapi',2:'cawley',3:'sarlin',4:'elkan',5:'occ',6:'oig2019',7:'oig2012',8:'cpi',9:'imodels',10:'sklearnap',11:'treeshap',12:'ale',13:'petropoulos',14:'failingbanks',15:'fdicloss',16:'parquet',17:'polars',18:'spark',19:'ffiec',20:'basu',21:'saito',22:'michaillat',23:'microtype'}
ESC={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}',
     '×':r'\(\times\)','α':r'\(\alpha\)','ρ':r'\(\rho\)','Σ':r'\(\Sigma\)','≤':r'\(\leq\)','≥':r'\(\geq\)','−':'-','–':'--','—':'---','’':"'",'‘':"'",'“':'``','”':"''",'·':r'\textperiodcentered{}'}
def escape(s):return ''.join(ESC.get(c,c) for c in str(s))
class Inline(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.out=[]
    def handle_starttag(self,tag,attrs):
        if tag in ['b','strong']:self.out.append(r'\textbf{')
        elif tag in ['i','em']:self.out.append(r'\textit{')
        elif tag=='br':self.out.append(r'\\ ')
        elif tag=='sub':self.out.append(r'\textsubscript{')
        elif tag in ['super','sup']:self.out.append(r'\textsuperscript{')
        elif tag=='link':self.out.append(r'\href{'+dict(attrs)['href']+'}{')
        elif tag=='cite':
            a=dict(attrs);loc='['+a['locator']+']' if a.get('locator') else ''
            self.out.append(r'\citep'+loc+'{'+a['key']+'}')
    def handle_endtag(self,tag):
        if tag in ['b','strong','i','em','sub','super','sup','link']:self.out.append('}')
    def handle_data(self,s):
        # Citations use true BibTeX keys; literal Spark local[2] is not a citation.
        parts=re.split(r'(?<!\w)(\[\d+(?:,\s*\d+)*\])',s)
        for part in parts:
            if re.fullmatch(r'\[\d+(?:,\s*\d+)*\]',part):
                keys=[CITES[int(i)] for i in re.findall(r'\d+',part)]
                self.out.append(r'\citep{'+','.join(keys)+'}')
            else:
                for v in re.split(r'(\b[\w/.-]+\.(?:csv|json|txt|ipynb|py|md)\b)',part):
                    self.out.append((r'\evidence{'+v+'}') if re.fullmatch(r'[\w/.-]+\.(?:csv|json|txt|ipynb|py|md)',v) else escape(v))
def tx(s):
    q=Inline();q.feed(str(s));return ''.join(q.out)
chunks=[];ntable=0;nfig=0;is_appendix=False

def p(s,kind='body'):chunks.append(tx(s)+'\n\n')
def intro(s):chunks.append('\\section*{'+tx(s)+'}\n\\addcontentsline{toc}{section}{'+tx(s)+'}\n')
def sec(s):chunks.append('\\section{'+tx(s)+'}\n')
def sub(s):
    barrier='\\FloatBarrier\n' if s=='Detection and review workload' else ''
    chunks.append(barrier+'\\subsection{'+tx(s)+'}\n')
def begin_appendix():
    global is_appendix
    is_appendix=True
    chunks.append(r'\FloatBarrier'+'\n'+r'\clearpage'+'\n'+r'\bibliographystyle{unsrtnat}'+'\n'+r'\bibliography{references}'+'\n'+r'\clearpage'+'\n'+r'\appendix'+'\n'+r'\label{appendix-start}'+'\n')
def fmt(x,d=3):return f'{float(x):.{d}f}'
def pct(x,d=1):return f'{float(x)*100:.{d}f}%'
def integer(x):return f'{int(float(x)):,}'
def eq(text,n):
    equations={1:r'y_{i,t}=\mathbf{1}\!\left\{t<T_i\leq t+4\ \text{quarters}\right\},',2:r'\operatorname{AP}=\sum_k(R_k-R_{k-1})P_k,\qquad \overline{\operatorname{AP}}_{\mathrm{year}}=\frac{1}{|\mathcal{Y}_{+}|}\sum_{y\in\mathcal{Y}_{+}}\operatorname{AP}_y.',3:r'L(q)=\frac{ch}{1000}\left[N_{\mathrm{new}}(q)+\rho N_{\mathrm{repeat}}(q)\right]+\alpha S_{\mathrm{missed}}(q).'}
    chunks.append('\\begin{equation}\n'+equations[n]+'\n\\label{eq:'+str(n)+'}\n\\end{equation}\n')
def tab(caption,headers,body,widths,notes,panels=None,numeric=(),barrier_after=False):
    global ntable
    ntable+=1;n=len(headers);parts=[]
    for i,w in enumerate(widths):
        parts.append(('R' if i in numeric else 'L')+'{\\dimexpr '+f'{w/sum(widths):.5f}'+r'\linewidth-2\tabcolsep\relax}')
    chunks.append('\\begin{table}[!htbp]\n\\centering\n\\begin{threeparttable}\n\\caption{'+tx(caption)+'}\n\\label{tab:'+str(ntable)+'}\n'+r'\small\setstretch{1.0}\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.15}'+'\n\\begin{tabular}{@{}'+''.join(parts)+'@{}}\n\\toprule\n')
    chunks.append(' & '.join(r'\textbf{'+tx(v)+'}' for v in headers)+r' \\'+'\n\\midrule\n')
    for row in body:
        if isinstance(row,str):
            chunks.append(r'\addlinespace[3pt]\multicolumn{'+str(n)+r'}{@{}l}{\textit{'+tx(row)+r'}} \\'+ '\n'+r'\addlinespace[2pt]'+'\n')
        else:
            chunks.append(' & '.join((r'\textbf{'+tx(v)+'}') if row[0]=='Pipeline' else tx(v) for v in row)+r' \\'+'\n')
    chunks.append('\\bottomrule\n\\end{tabular}\n\\begin{tablenotes}[flushleft]\n\\footnotesize\\setstretch{1.0}\n\\item '+r'\textit{Notes.} '+tx(notes)+'\n\\end{tablenotes}\n\\end{threeparttable}\n\\end{table}\n')
    if barrier_after:chunks.append('\\FloatBarrier\n')
def fig(name,caption,notes,width=None):
    global nfig
    nfig+=1
    chunks.append('\\begin{figure}[!htbp]\n\\centering\n\\includegraphics[width=\\linewidth]{../figures/paper/'+name+'.pdf}\n\\caption{'+tx(caption)+'}\n\\label{fig:'+str(nfig)+'}\n\\papernotes{'+tx(notes)+'}\n\\end{figure}\n')

PRE=r'''\documentclass[11pt,a4paper]{article}
\usepackage{fdicpaper}
\hypersetup{pdftitle={Bank-Failure Early Warning Using FDIC Data},pdfauthor={Nguyen Le Nam Khanh}}
\begin{document}
\begin{titlepage}
\centering
\vspace*{7mm}
{\fontsize{18}{22}\selectfont\bfseries Bank-Failure Early Warning\\Using FDIC Data\par}
\vspace{3mm}
{\normalsize Data Engineering, Temporal Validation and Review Costs\par}
\vspace{7mm}
{\microtypesetup{protrusion=false}\fontencoding{T5}\fontfamily{qtm}\selectfont\large Nguyễn Lê Nam Khánh\par}
\vspace{2mm}
{\normalsize\itshape National Economics University, Hanoi, Vietnam\par}
\vspace{3mm}
{\normalsize Student ID: 11230976\par}
{\small BFT65B -- Big Data Analytics in Finance\par}
{\normalsize 15 November 2026\par}
\vspace{6mm}
{\bfseries Abstract\par}
\vspace{2mm}
\begin{minipage}{.92\textwidth}
\small\setstretch{1.08}\setlength{\parindent}{0pt}
This project constructed a financial reporting pipeline from FDIC data covering 1984Q1--2026Q2. The acquired sample contains 1,682,616 reports across 170 quarters. Original responses were retained alongside typed Parquet tables, with financial reporting exceptions documented before feature construction. For an identical seven-column projection, Parquet reduced storage from 68.56 to 18.05 MB. The matched join and aggregation took a median 0.073 seconds in Polars and 0.569 seconds in pandas, while a local Spark implementation reproduced the aggregate results. Model development used 64 chronological validation folds. On the final 2013Q1--2025Q2 holdout, the selected iterative random forest attained mean annual average precision of 0.251 and detected 68 of 78 failures at an illustrative quarterly alert share of 3.53\%, with precision of 2.23\%. A seven-feature forest achieved higher mean annual average precision of 0.310. Review-cost scenarios quantified the associated workload under assumptions about review effort and missed-event severity. The results support a local columnar workflow for this panel and identify the operational measurements needed to evaluate its use in supervision.
\end{minipage}\par
\vspace{5mm}
\begin{minipage}{\textwidth}
\small\setstretch{1.0}\setlength{\parindent}{0pt}
\textit{Keywords:} bank failure; financial data engineering; temporal validation; rare events; review costs.
\par\vspace{4mm}
\textbf{Data and evaluation scope}\par\vspace{2mm}
\begin{tabularx}{\linewidth}{@{}p{.24\linewidth}X@{}}
\toprule
Acquisition & FDIC BankFind public API; downloaded 6 November 2026.\\
Source coverage & Financials 1984Q1--2026Q2: 1,682,616 rows, 170 quarters, 87 fields; Failures: 4,117 records; Institutions: 27,835 records.\\
Development & Final training sample, prediction quarters 1984Q2--2011Q4: 1,306,763 rows and 2,729 represented failures; validation 1996--2011: 594,873 rows and 514 events per primary scheme.\\
Holdout & Prediction quarters 2013Q1--2025Q2, after the 2012 gap: 273,863 evaluable rows and 78 failures; labels complete through 2026Q2.\\
Repository & REPOSITORY_URL\\
\bottomrule
\end{tabularx}
\end{minipage}
\end{titlepage}
'''
url=author['github_url'];url='Not yet published.' if url.startswith('TO_BE_') else r'\url{'+url+'}'
PRE=PRE.replace('REPOSITORY_URL',url)
runpy.run_path(str(M/'content.py'),init_globals={k:v for k,v in globals().copy().items() if not k.startswith('__')})
text=PRE+''.join(chunks)+r'\end{document}'+'\n'
(M/'main.tex').write_text(text)

def compile_report():
    local=ROOT/'.local/tex-runtime/TinyTeX/bin/universal-darwin'
    explicit=os.environ.get('PDFLATEX')
    engine=Path(explicit) if explicit else (Path(shutil.which('pdflatex')) if shutil.which('pdflatex') else local/'pdflatex')
    if not engine.is_file():raise RuntimeError('pdfLaTeX not found. Install TeX Live/TinyTeX or set PDFLATEX; source is already generated.')
    env=os.environ.copy();env['PATH']=str(engine.parent)+os.pathsep+env.get('PATH','')
    bib=shutil.which('bibtex',path=env['PATH'])
    if not bib:raise RuntimeError('BibTeX not found alongside pdfLaTeX')
    build=ROOT/'.local/latex-build';build.mkdir(exist_ok=True)
    commands=[[str(engine),'-no-shell-escape','-interaction=nonstopmode','-halt-on-error',f'-output-directory={build}','main.tex'],[bib,'main']]
    commands += [commands[0],commands[0]]
    for i,cmd in enumerate(commands):
        runenv=env.copy()
        if cmd[0]==bib:runenv['BIBINPUTS']=str(M)+os.pathsep
        result=subprocess.run(cmd,cwd=(build if cmd[0]==bib else M),env=runenv,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (build/f'pass_{i+1}.txt').write_text(result.stdout)
        if result.returncode:raise RuntimeError(result.stdout[-5000:])
    out=ROOT/'reports/FDIC_Risk_Analytics_Report.pdf';shutil.copy2(build/'main.pdf',out)
    log=(build/'main.log').read_text(errors='replace')
    problems=[line for line in log.splitlines() if 'Overfull ' in line or 'undefined' in line.lower() or 'Missing character:' in line]
    (ROOT/'reports/latex_build.json').write_text(json.dumps({'engine':subprocess.check_output([str(engine),'--version'],text=True).splitlines()[0],'passes':['pdflatex','bibtex','pdflatex','pdflatex'],'shell_escape':False,'warnings':problems,'other_package_warnings':[line for line in log.splitlines() if 'Warning:' in line and line not in problems],'sources':['reports/manuscript/main.tex','reports/manuscript/fdicpaper.sty','reports/manuscript/references.bib','reports/manuscript/content.py']},indent=2)+'\n')
    try:
        from pypdf import PdfReader
        r=PdfReader(out);a=next(i for i,p in enumerate(r.pages) if re.search(r'A\.\s+Supplementary',p.extract_text()))
        summary={'pages':len(r.pages),'main_pages':a,'appendix_pages':len(r.pages)-a,'tables':ntable,'figures':nfig,'renderer':'pdfLaTeX + BibTeX'}
        assert summary['main_pages']<=20 and summary['appendix_pages']<=10,summary
        (ROOT/'reports/report_layout.json').write_text(json.dumps(summary,indent=2)+'\n')
        print(summary)
    except ImportError:print('pypdf unavailable; PDF built, page audit requires requirements-report.txt')
    print(out)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source-only',action='store_true');args=parser.parse_args()
    if not args.source_only:compile_report()
