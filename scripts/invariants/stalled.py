#!/usr/bin/python3
"""
Vary the LEN macro in microbench/MM/bench.c across a fixed set of values,
recompile and simulate each under Sniper, then print a table and plot of
L1-D cache misses vs PICS-attributed stalled cycles.
"""

import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BENCH_C   = REPO_ROOT / 'microbench' / 'MM' / 'bench.c'
BENCH_BIN = REPO_ROOT / 'microbench' / 'MM' / 'bench'
RUN_ROI   = REPO_ROOT / 'run-roi.sh'
OUT       = REPO_ROOT / 'out'

LENS = [16384, 24576, 32768, 49152, 65536]

_LEN_RE = re.compile(r'(#define\s+LEN\s+)(\d+)')
_L1D_RE = re.compile(r'Cache L1-D.*?num cache misses\s*\|\s*(\d+)', re.DOTALL)


def set_len(value):
    text = BENCH_C.read_text()
    BENCH_C.write_text(_LEN_RE.sub(lambda m: m.group(1) + str(value), text))


def compile_bench():
    r = subprocess.run(['make'], cwd=BENCH_C.parent, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'compile failed:\n{r.stderr}')


def run_sim():
    r = subprocess.run(['bash', str(RUN_ROI), str(BENCH_BIN)],
                       cwd=REPO_ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'simulation failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}')


def read_l1d_misses():
    m = _L1D_RE.search((OUT / 'sim.out').read_text())
    return int(m.group(1)) if m else sys.exit('L1-D misses not found in sim.out')


def read_stalled():
    con = sqlite3.connect(OUT / 'sim.stats.sqlite3')
    val = con.execute('SELECT SUM(stalled) FROM pics_c').fetchone()[0]
    con.close()
    return float(val or 0)


def print_table(rows):
    cols = ['LEN', 'L1-D misses', 'Stalled cycles']
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
    lens    = [r[0] for r in rows]
    misses  = [r[1] for r in rows]
    stalled = [r[2] for r in rows]

    scale = 1
    while max(stalled) / max(misses) >= 10:
        stalled = [s / 10 for s in stalled]
        scale *= 10

    stalled_label = f'Stalled cycles (÷{scale:,})' if scale > 1 else 'Stalled cycles'

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(lens, misses,  'o-', label='L1 data cache misses')
    ax.plot(lens, stalled, 'o-', label=stalled_label)
    ax.set_xlabel('LEN')
    ax.set_ylabel('Count')
    ax.set_xticks(lens)
    ax.set_xticklabels([str(l) for l in lens], rotation=30, ha='right')
    ax.legend()
    ax.set_title('L1 data cache misses vs PICS stalled cycles')
    plt.tight_layout()
    out_path = Path(__file__).parent / 'stalled.png'
    plt.savefig(out_path, dpi=150)
    print(f'Plot saved → {out_path}')
    plt.show()


original_len = int(_LEN_RE.search(BENCH_C.read_text()).group(2))
rows = []

try:
    for length in LENS:
        print(f'[LEN={length}] compiling...')
        set_len(length)
        compile_bench()
        print(f'[LEN={length}] simulating...')
        run_sim()
        rows.append((length, read_l1d_misses(), read_stalled()))
        print(f'[LEN={length}] done: misses={rows[-1][1]:,}  stalled={rows[-1][2]:,.1f}')
finally:
    set_len(original_len)

print()
print_table(rows)
plot(rows)
