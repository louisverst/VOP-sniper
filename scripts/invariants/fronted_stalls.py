#!/usr/bin/python3
"""
Vary the ITERS macro in microbench/MIP/bench.c across [4, 8, 12, 16],
recompile and simulate each under Sniper, then plot L1-I cache misses
vs PICS-attributed front-end stall cycles.

Used to generate the figure in section 6.3 of the report.
"""

import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BENCH_C   = REPO_ROOT / 'microbench' / 'MIP' / 'bench.c'
BENCH_BIN = REPO_ROOT / 'microbench' / 'MIP' / 'bench'
RUN_ROI   = REPO_ROOT / 'run-roi.sh'
OUT       = REPO_ROOT / 'out'

ITERS_VALUES = [4, 8, 12, 16]

_ITERS_RE = re.compile(r'(#define\s+ITERS\s+)(\d+)')
_L1I_RE   = re.compile(r'Cache L1-I.*?num cache misses\s*\|\s*(\d+)', re.DOTALL)


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


def read_l1i_misses():
    m = _L1I_RE.search((OUT / 'sim.out').read_text())
    return int(m.group(1)) if m else sys.exit('L1-I misses not found in sim.out')


def read_fe_stalls():
    con = sqlite3.connect(OUT / 'sim.stats.sqlite3')
    val = con.execute('SELECT SUM(fe_stall) FROM pics_d').fetchone()[0]
    con.close()
    return float(val or 0)


def print_table(rows):
    cols = ['ITERS', 'L1-I misses', 'FE stall cycles']
    data = [[str(r[0]), f'{r[1]:,}', f'{r[2]:,.1f}'] for r in rows]
    widths = [max(len(cols[i]), max(len(d[i]) for d in data)) for i in range(3)]
    sep = '+' + '+'.join('-' * (w + 2) for w in widths) + '+'
    print(sep)
    print('|' + '|'.join(f' {cols[i]:<{widths[i]}} ' for i in range(3)) + '|')
    print(sep)
    for d in data:
        print('|' + '|'.join(f' {d[i]:>{widths[i]}} ' for i in range(3)) + '|')
    print(sep)


def plot(rows):
    iters   = [r[0] for r in rows]
    misses  = [r[1] for r in rows]
    stalls  = [r[2] for r in rows]

    scale = 1
    while max(stalls) / max(misses) >= 10:
        stalls = [s / 10 for s in stalls]
        scale *= 10

    stalls_label = f'FE stall cycles (÷{scale:,})' if scale > 1 else 'FE stall cycles'

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(iters, misses, 'o-', label='L1-I cache misses')
    ax.plot(iters, stalls, 'o-', label=stalls_label)
    ax.set_xlabel('ITERS')
    ax.set_ylabel('Count')
    ax.set_xticks(iters)
    ax.legend()
    ax.set_title('L1-I cache misses vs PICS front-end stall cycles (MIP)')
    fig.tight_layout()
    out_path = Path(__file__).parent / 'fronted_stalls.png'
    fig.savefig(out_path, dpi=150)
    print(f'Plot saved → {out_path}')
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
        rows.append((iters, read_l1i_misses(), read_fe_stalls()))
        print(f'[ITERS={iters}] done: misses={rows[-1][1]:,}  fe_stalls={rows[-1][2]:,.1f}')
finally:
    set_iters(original_iters)
    compile_bench()

print()
print_table(rows)
plot(rows)
