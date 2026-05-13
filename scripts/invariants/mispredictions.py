#!/usr/bin/python3
"""
Vary the ITERS macro in microbench/CCh/bench.c across [4, 8, 12, 16],
recompile and simulate each under Sniper, then plot:
  - incorrect branch predictions vs PICS mispred cycles (from pics_d)
  - incorrect branch predictions vs PICS flushed cycles (from pics_c)

  Used to generate the figures in section 6.4 of the report.
"""

import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BENCH_C   = REPO_ROOT / 'microbench' / 'CCh' / 'bench.c'
BENCH_BIN = REPO_ROOT / 'microbench' / 'CCh' / 'bench'
RUN_ROI   = REPO_ROOT / 'run-roi.sh'
OUT       = REPO_ROOT / 'out'

ITERS_VALUES = [4, 8, 12, 16]

_ITERS_RE     = re.compile(r'(#define\s+ITERS\s+)(\d+)')
_INCORRECT_RE = re.compile(r'num incorrect\s*\|\s*(\d+)')


def set_iters(value):
    text = BENCH_C.read_text()
    BENCH_C.write_text(_ITERS_RE.sub(lambda m: m.group(1) + str(value), text))


def compile_bench():
    r = subprocess.run(['make'], cwd=BENCH_C.parent, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'compile failed:\n{r.stderr}')


def run_sim():
    r = subprocess.run(['bash', str(RUN_ROI), str(BENCH_BIN)],
                       cwd=REPO_ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'simulation failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}')


def read_incorrect():
    m = _INCORRECT_RE.search((OUT / 'sim.out').read_text())
    return int(m.group(1)) if m else sys.exit('num incorrect not found in sim.out')


def read_db(query):
    con = sqlite3.connect(OUT / 'sim.stats.sqlite3')
    val = con.execute(query).fetchone()[0]
    con.close()
    return float(val or 0)


def print_table(rows):
    cols = ['ITERS', 'Incorrect preds', 'Mispred cycles', 'Flushed cycles']
    data = [[str(r[0]), f'{r[1]:,}', f'{r[2]:,.1f}', f'{r[3]:,.1f}'] for r in rows]
    widths = [max(len(cols[i]), max(len(d[i]) for d in data)) for i in range(4)]
    sep = '+' + '+'.join('-' * (w + 2) for w in widths) + '+'
    print(sep)
    print('|' + '|'.join(f' {cols[i]:<{widths[i]}} ' for i in range(4)) + '|')
    print(sep)
    for d in data:
        print('|' + '|'.join(f' {d[i]:>{widths[i]}} ' for i in range(4)) + '|')
    print(sep)


def _scaled(values, reference):
    scale = 1
    while max(values) / max(reference) >= 10:
        values = [v / 10 for v in values]
        scale *= 10
    return values, scale


def plot(rows):
    iters     = [r[0] for r in rows]
    incorrect = [r[1] for r in rows]
    mispred   = [r[2] for r in rows]
    flushed   = [r[3] for r in rows]

    mispred_s, scale_m = _scaled(mispred, incorrect)
    flushed_s, scale_f = _scaled(flushed, incorrect)

    mispred_label = f'Mispred cycles (÷{scale_m:,})' if scale_m > 1 else 'Mispred cycles'
    flushed_label = f'Flushed cycles (÷{scale_f:,})' if scale_f > 1 else 'Flushed cycles'

    base_path = Path(__file__).parent

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(iters, incorrect, 'o-', color='steelblue', label='Incorrect predictions')
    ax.plot(iters, mispred_s, 'o-', color='red',       label=mispred_label)
    ax.set_xlabel('ITERS')
    ax.set_ylabel('Count')
    ax.set_xticks(iters)
    ax.legend()
    ax.set_title('Incorrect predictions vs PICS mispred cycles (CCh)')
    fig.tight_layout()
    p = base_path / 'mispredictions_mispred.png'
    fig.savefig(p, dpi=150)
    print(f'Plot saved → {p}')
    plt.show()

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(iters, incorrect, 'o-', color='steelblue', label='Incorrect predictions')
    ax.plot(iters, flushed_s, 'o-', color='red',       label=flushed_label)
    ax.set_xlabel('ITERS')
    ax.set_ylabel('Count')
    ax.set_xticks(iters)
    ax.legend()
    ax.set_title('Incorrect predictions vs PICS flushed cycles (CCh)')
    fig.tight_layout()
    p = base_path / 'mispredictions_flushed.png'
    fig.savefig(p, dpi=150)
    print(f'Plot saved → {p}')
    plt.show()


original_iters = int(_ITERS_RE.search(BENCH_C.read_text()).group(2))
rows = []

try:
    for iters in ITERS_VALUES:
        print(f'[ITERS={iters}] compiling...')
        set_iters(iters)
        compile_bench()
        print(f'[ITERS={iters}] simulating...')
        run_sim()
        incorrect = read_incorrect()
        mispred   = read_db('SELECT SUM(mispred) FROM pics_d')
        flushed   = read_db('SELECT SUM(flushed) FROM pics_c')
        rows.append((iters, incorrect, mispred, flushed))
        print(f'[ITERS={iters}] done: incorrect={incorrect:,}  mispred={mispred:,.1f}  flushed={flushed:,.1f}')
finally:
    set_iters(original_iters)
    compile_bench()

print()
print_table(rows)
plot(rows)
