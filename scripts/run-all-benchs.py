#!/usr/bin/python3

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parent.parent
MICROBENCH  = REPO_ROOT / 'microbench'
RUN_ROI     = REPO_ROOT / 'run-roi.sh'
PLOT_PY     = REPO_ROOT / 'scripts' / 'plot.py'
OUT_DB      = REPO_ROOT / 'scripts'  / 'out' / 'db'
OUT_PLOTS   = REPO_ROOT / 'scripts' / 'out' / 'plots'
SNIPER_OUT  = REPO_ROOT / 'out' / 'sim.stats.sqlite3'

TOP_N = 5


def run(cmd, **kwargs):
    print(f'  $ {" ".join(str(c) for c in cmd)}')
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f'  ERROR: exit code {result.returncode}', file=sys.stderr)
    return result.returncode


def bench_dirs():
    return sorted(
        d for d in MICROBENCH.iterdir()
        if d.is_dir() and (d / 'Makefile').exists()
    )


def main():
    OUT_DB.mkdir(parents=True, exist_ok=True)
    OUT_PLOTS.mkdir(parents=True, exist_ok=True)


    benches = bench_dirs()
    failed = []
    for bench_dir in benches:
        name = bench_dir.name
        bench_bin = bench_dir / 'bench'

        if not bench_bin.exists():
            print(f'\n[{name}] SKIP — no bench binary after build')
            failed.append(name)
            continue

        print(f'\n[{name}] Running...')
        rc = run(['bash', str(RUN_ROI), str(bench_bin)], cwd=REPO_ROOT)
        if rc != 0:
            print(f'[{name}] simulation failed, skipping', file=sys.stderr)
            failed.append(name)
            continue

        db_dest = OUT_DB / f'{name}.sqlite3'
        if not SNIPER_OUT.exists():
            print(f'[{name}] sim.sqlite3 not found at {SNIPER_OUT}', file=sys.stderr)
            failed.append(name)
            continue
        shutil.copy2(SNIPER_OUT, db_dest)
        print(f'[{name}] DB saved → {db_dest.relative_to(REPO_ROOT)}')

        plot_dest = OUT_PLOTS / f'{name}.png'
        rc = run(
            [sys.executable, str(PLOT_PY), str(db_dest), '-n', str(TOP_N), '-t', name],
            cwd=OUT_PLOTS,
        )
        if rc != 0:
            print(f'[{name}] plot failed', file=sys.stderr)
            failed.append(name)
            continue
        print(f'[{name}] Plot saved → {plot_dest.relative_to(REPO_ROOT)}')

    print('\n=== Done ===')
    ok = len(benches) - len(failed)
    print(f'{ok}/{len(benches)} benchmarks succeeded')
    if failed:
        print(f'Failed: {", ".join(failed)}')
        sys.exit(1)


if __name__ == '__main__':
    main()
