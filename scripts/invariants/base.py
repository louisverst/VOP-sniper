#!/usr/bin/python3
"""
Verify that the base (PICS_d) and compute (PICS_c) components equal uops / dispatch_width.

Usage:
  base.py [path]        path is an out-dir OR a directory of out-dirs
  base.py -B            run over all subdirs in scripts/out/

Used to generate the table in section 6.2 of the report. 
"""

import argparse
import re
import sqlite3
import sys
from pathlib import Path

SCRIPTS_OUT = Path(__file__).resolve().parent.parent / 'out'

_DISPATCH_RE = re.compile(r'dispatch_width\s*=\s*(\d+)')


def is_out_dir(p: Path) -> bool:
    return (p / 'sim.stats.sqlite3').exists()


def _read_dispatch_width(out_dir: Path) -> int:
    cfg = out_dir / 'sim.cfg'
    if cfg.exists():
        m = _DISPATCH_RE.search(cfg.read_text())
        if m:
            return int(m.group(1))
    return 4


def read_data(out_dir: Path) -> dict:
    dispatch_width = _read_dispatch_width(out_dir)
    db = out_dir / 'sim.stats.sqlite3'
    con = sqlite3.connect(db)
    cur = con.cursor()

    uops = cur.execute("""
        SELECT v.value FROM 'values' v
        JOIN names n    ON v.nameid   = n.nameid
        JOIN prefixes p ON v.prefixid = p.prefixid
        WHERE n.objectname = 'rob_timer' AND n.metricname = 'uops_total'
          AND p.prefixname = 'roi-end' AND v.core = 0
    """).fetchone()
    if uops is None:
        con.close()
        raise ValueError(f'rob_timer.uops_total not found in {db}')
    uops = uops[0]

    base    = cur.execute('SELECT SUM(base)    FROM pics_d').fetchone()[0] or 0.0
    compute = cur.execute('SELECT SUM(compute) FROM pics_c').fetchone()[0] or 0.0
    con.close()

    expected = uops / dispatch_width
    return {
        'name':         out_dir.name,
        'expected':     expected,
        'base':         float(base),
        'compute':      float(compute),
        'diff_base':    float(base)    - expected,
        'diff_compute': float(compute) - expected,
    }


def collect_dirs(path: Path | None, use_bench: bool) -> list[Path]:
    if path is not None:
        if is_out_dir(path):
            return [path]
        subdirs = sorted(d for d in path.iterdir() if d.is_dir() and is_out_dir(d))
        if not subdirs:
            sys.exit(f'error: {path} is neither an out-dir nor a directory of out-dirs')
        return subdirs

    if use_bench:
        if not SCRIPTS_OUT.exists():
            sys.exit(f'error: {SCRIPTS_OUT} does not exist — run run-all-benchs.py first')
        subdirs = sorted(d for d in SCRIPTS_OUT.iterdir() if d.is_dir() and is_out_dir(d))
        if not subdirs:
            sys.exit(f'No benchmark output found in {SCRIPTS_OUT} — run run-all-benchs.py first')
        return subdirs

    sys.exit('error: provide a path or use -B to run over all benchmarks in scripts/out/')


def print_table(rows: list[dict]) -> None:
    cols = ['Benchmark', 'uops/width', 'base', 'base diff', 'compute', 'compute diff']

    def fmt(n):
        return f'{n:,.2f}'

    def fmt_diff(d):
        return f'{d:+,.2f}'

    data = []
    for r in rows:
        data.append([
            r['name'],
            fmt(r['expected']),
            fmt(r['base']),
            fmt_diff(r['diff_base']),
            fmt(r['compute']),
            fmt_diff(r['diff_compute']),
        ])

    widths = [max(len(cols[i]), max(len(row[i]) for row in data)) for i in range(len(cols))]
    sep    = '+' + '+'.join('-' * (w + 2) for w in widths) + '+'
    header = '|' + '|'.join(f' {cols[i]:<{widths[i]}} ' for i in range(len(cols))) + '|'

    print(sep)
    print(header)
    print(sep)
    for row in data:
        print('|' + '|'.join(f' {row[i]:>{widths[i]}} ' for i in range(len(cols))) + '|')
    print(sep)

    def passes(r):
        tol_base    = max(5.0,  r['expected'] * 1e-3)
        tol_compute = max(15.0, r['expected'] * 1e-3)
        return abs(r['diff_base']) <= tol_base and abs(r['diff_compute']) <= tol_compute

    ok = sum(1 for r in rows if passes(r))
    print(f'\n{ok}/{len(rows)} benchmarks pass the invariant '
          f'(|diff_base| ≤ max(5, 0.1% uops/width), |diff_compute| ≤ max(15, 0.1% uops/width))')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('path', nargs='?', type=Path, default=None,
                        help='out-dir or directory of out-dirs')
    parser.add_argument('-B', '--benchmarks', action='store_true',
                        help='run over all subdirs in scripts/out/')
    args = parser.parse_args()

    dirs = collect_dirs(args.path, args.benchmarks)

    rows = []
    for d in dirs:
        try:
            rows.append(read_data(d))
        except Exception as e:
            print(f'warning: skipping {d.name}: {e}', file=sys.stderr)

    if not rows:
        sys.exit('No valid out-dirs found')

    print_table(rows)


if __name__ == '__main__':
    main()
