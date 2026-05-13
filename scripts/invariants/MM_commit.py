#!/usr/bin/python3
"""
Run the MM microbenchmark under Sniper and plot the 3 instructions with the
largest PICS @ commit stacks. Used to generate the figure in section 6.5 in the report.
"""

import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BENCH_BIN = REPO_ROOT / 'microbench' / 'MM' / 'bench'
RUN_ROI   = REPO_ROOT / 'run-roi.sh'
DB        = REPO_ROOT / 'out' / 'sim.stats.sqlite3'

N     = 3
TITLE = 'PICS @ dispatch for MM microbenchmark'


def run_sim():
    r = subprocess.run(['bash', str(RUN_ROI), str(BENCH_BIN)],
                       cwd=REPO_ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'simulation failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}')


def load_pics_c():
    con = sqlite3.connect(DB)
    rows = con.execute(
        'SELECT pics_d.instr_type, pics_d.addr, compute, drained, stalled, flushed '
        'FROM pics_c INNER JOIN pics_d ON pics_d.addr = pics_c.addr'
    ).fetchall()
    con.close()
    return rows


def top_n_by_commit(rows, n):
    scores = [r[2] + r[3] + r[4] + r[5] for r in rows]
    arr = np.array(scores)
    size = len(arr)
    n = min(n, size)
    indices = [np.argpartition(arr, size - 1 - i, axis=None)[size - 1 - i] for i in range(n)]
    return [rows[i] for i in indices]


def plot(top):
    tags    = [r[1][-4:] + ' | ' + r[0] for r in top]
    compute = np.array([r[2] for r in top], dtype=float)
    drained = np.array([r[3] for r in top], dtype=float)
    stalled = np.array([r[4] for r in top], dtype=float)
    flushed = np.array([r[5] for r in top], dtype=float)

    x      = np.arange(len(top))
    bottom = np.zeros(len(top))

    fig, ax = plt.subplots(figsize=(8, 5))
    for label, counts in [('Compute', compute), ('Drained', drained),
                           ('Stalled', stalled), ('Flushed', flushed)]:
        ax.bar(x, counts, 0.4, label=label, bottom=bottom)

        bottom += counts

    ax.set_ylim(top=bottom.max() * 1.1)
    ax.set_xticks(x, tags, rotation=15, ha='right')
    ax.set_title(TITLE)
    ax.legend()
    fig.tight_layout()

    out_path = Path(__file__).parent / 'MM_commit.png'
    fig.savefig(out_path, dpi=150)
    print(f'Plot saved → {out_path}')
    plt.show()


print('Running MM benchmark under Sniper...')
run_sim()
print('Simulation done. Reading pics_c...')
rows = load_pics_c()
top  = top_n_by_commit(rows, N)
plot(top)
