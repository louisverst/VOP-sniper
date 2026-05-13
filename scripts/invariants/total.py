#!/usr/bin/python3
"""
Verify that total attributed PICS cycles == total simulated cycles.

Usage:
  total.py [path]        path is an out-dir OR a directory of out-dirs
  total.py -B            run over all subdirs in scripts/out/


Used to generate the table in section 6.1 of the report.
"""

import argparse
import re
import sqlite3
import sys
from pathlib import Path

SCRIPTS_OUT = Path(__file__).resolve().parent.parent / 'out'

_FREQ_RE = re.compile(r'perf_model/core/frequency\s*=\s*([\d.]+)')


def is_out_dir(p: Path) -> bool:
    return (p / 'sim.stats.sqlite3').exists()


def _read_freq_ghz(out_dir: Path) -> float:
    cfg = out_dir / 'sim.cfg'
    if cfg.exists():
        m = _FREQ_RE.search(cfg.read_text())
        if m:
            return float(m.group(1))
    return 2.66


def read_rob_cycles(out_dir: Path) -> float:
    """ROB-attributed ROI cycles from the database.

    PICS only track instructions dispatched through the ROB.  The rest of the
    elapsed time is accounted for by:
      - cpiUnknown   (INST_UNKNOWN: spawned threads, barriers, system events)
      - cpiITLBMiss / cpiDTLBMiss  (TLB-miss servicing instructions)
    These go through micro_op_performance_model directly, never touching the ROB.

    ROB cycles = elapsed_time(roi-end − roi-begin) − cpiUnknown − cpiTLBMiss

    sim.out instead uses barrier.global_time, which advances in discrete steps
    and misses the partial interval at each ROI boundary.
    """
    freq_ghz = _read_freq_ghz(out_dir)
    db = out_dir / 'sim.stats.sqlite3'
    con = sqlite3.connect(db)
    cur = con.cursor()

    def get_fs(objectname, metricname, prefix):
        r = cur.execute("""
            SELECT v.value FROM `values` v
            JOIN names n    ON v.nameid    = n.nameid
            JOIN prefixes p ON v.prefixid  = p.prefixid
            WHERE n.objectname = ? AND n.metricname = ?
              AND p.prefixname = ? AND v.core = 0
        """, (objectname, metricname, prefix)).fetchone()
        return r[0] if r else 0

    et_begin   = get_fs('performance_model', 'elapsed_time', 'roi-begin')
    et_end     = get_fs('performance_model', 'elapsed_time', 'roi-end')
    cpi_unk    = get_fs('performance_model', 'cpiUnknown',   'roi-end')
    cpi_itlb   = get_fs('performance_model', 'cpiITLBMiss',  'roi-end')
    cpi_dtlb   = get_fs('performance_model', 'cpiDTLBMiss',  'roi-end')

    con.close()
    if et_end == 0:
        raise ValueError(f'performance_model.elapsed_time not found in {db}')

    rob_fs = et_end - et_begin - cpi_unk - cpi_itlb - cpi_dtlb
    return rob_fs * freq_ghz / 1e6


def read_pics_totals(out_dir: Path) -> tuple[float, float]:
    db = out_dir / 'sim.stats.sqlite3'
    con = sqlite3.connect(db)
    cur = con.cursor()
    pics_d = cur.execute('SELECT SUM(base + fe_stall + be_stall + mispred) FROM pics_d').fetchone()[0] or 0.0
    pics_c = cur.execute('SELECT SUM(compute + drained + stalled + flushed) FROM pics_c').fetchone()[0] or 0.0
    con.close()
    return float(pics_d), float(pics_c)


def check_dir(out_dir: Path) -> dict:
    cycles = read_rob_cycles(out_dir)
    pics_d, pics_c = read_pics_totals(out_dir)
    return {
        'name':   out_dir.name,
        'cycles': cycles,
        'pics_d': pics_d,
        'pics_c': pics_c,
        'diff_d': pics_d - cycles,
        'diff_c': pics_c - cycles,
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
    cols = ['Benchmark', 'ROB cycles', 'PICS_d', 'PICS_d diff', 'PICS_c', 'PICS_c diff']

    def fmt_num(n):
        return f'{n:,.2f}'

    def fmt_diff(d):
        s = f'{d:+,.2f}'
        return s

    data = []
    for r in rows:
        data.append([
            r['name'],
            fmt_num(r['cycles']),
            fmt_num(r['pics_d']),
            fmt_diff(r['diff_d']),
            fmt_num(r['pics_c']),
            fmt_diff(r['diff_c']),
        ])

    widths = [max(len(cols[i]), max(len(row[i]) for row in data)) for i in range(len(cols))]

    sep = '+' + '+'.join('-' * (w + 2) for w in widths) + '+'
    header = '|' + '|'.join(f' {cols[i]:<{widths[i]}} ' for i in range(len(cols))) + '|'

    print(sep)
    print(header)
    print(sep)
    for row in data:
        print('|' + '|'.join(f' {row[i]:>{widths[i]}} ' for i in range(len(cols))) + '|')
    print(sep)

    # summary — PICS use static_cast<float> in to_cycles(), so single-precision
    # rounding accumulates proportionally to run length.  PICS_c has an additional
    # deficit from instructions still in-flight at ROI end.
    def passes(r):
        tol_d = max(1.0, r['cycles'] * 1e-5)   # 0.001 % of ROB cycles
        tol_c = max(5.0, r['cycles'] * 1e-5)   # same + pipeline-tail slack
        return abs(r['diff_d']) <= tol_d and abs(r['diff_c']) <= tol_c

    ok = sum(1 for r in rows if passes(r))
    print(f'\n{ok}/{len(rows)} benchmarks pass the invariant '
          f'(|diff_d| ≤ max(1, 0.001% cycles), |diff_c| ≤ max(5, 0.001% cycles))')


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
            rows.append(check_dir(d))
        except Exception as e:
            print(f'warning: skipping {d.name}: {e}', file=sys.stderr)

    if not rows:
        sys.exit('No valid out-dirs found')

    print_table(rows)


if __name__ == '__main__':
    main()
