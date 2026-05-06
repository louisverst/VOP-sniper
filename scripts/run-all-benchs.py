#!/usr/bin/python3

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT  = Path(__file__).resolve().parent.parent
MICROBENCH = REPO_ROOT / 'microbench'
RUN_ROI    = REPO_ROOT / 'run-roi.sh'
PLOT_PY    = REPO_ROOT / 'scripts' / 'plot.py'
OUT_ROOT   = REPO_ROOT / 'scripts' / 'out'
SNIPER_OUT = REPO_ROOT / 'out'

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
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--plot', action='store_true', help='Generate plots after simulation')
    args = parser.parse_args()

    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    benches = bench_dirs()
    failed = []
    for bench_dir in benches:
        name = bench_dir.name
        bench_bin = bench_dir / 'bench'

        if not bench_bin.exists():
            print(f'\n[{name}] SKIP — no bench binary')
            failed.append(name)
            continue

        print(f'\n[{name}] Running...')
        rc = run(['bash', str(RUN_ROI), str(bench_bin)], cwd=REPO_ROOT)
        if rc != 0:
            print(f'[{name}] simulation failed, skipping', file=sys.stderr)
            failed.append(name)
            continue

        if not SNIPER_OUT.exists():
            print(f'[{name}] out/ directory not found at {SNIPER_OUT}', file=sys.stderr)
            failed.append(name)
            continue

        bench_out = OUT_ROOT / name
        if bench_out.exists():
            shutil.rmtree(bench_out)
        shutil.copytree(SNIPER_OUT, bench_out)
        print(f'[{name}] Output saved → {bench_out.relative_to(REPO_ROOT)}')

        if args.plot:
            db_path = bench_out / 'sim.stats.sqlite3'
            if not db_path.exists():
                print(f'[{name}] sim.stats.sqlite3 not found, skipping plot', file=sys.stderr)
                failed.append(name)
                continue
            plot_dest = bench_out / f'{name}.png'
            rc = run(
                [sys.executable, str(PLOT_PY), str(db_path), '-n', str(TOP_N), '-t', name, '-o', str(plot_dest)],
                cwd=bench_out,
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
