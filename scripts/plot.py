#!/usr/bin/python3


import argparse
import numpy as np
import matplotlib.pyplot as plt
import sqlite3


def _snap(x):
    """Round to nearest 0.25 (i.e. 0.00, 0.25, 0.50, 0.75)."""
    return np.round(np.asarray(x) * 4) / 4


class PicsData:
    def __init__(self, db_filename: str):
        con = sqlite3.connect(db_filename)
        cursor = con.cursor()

        query = ('SELECT pics_d.addr, pics_d.instr_type, base, fe_stall, be_stall, mispred, '
                 'compute, drained, stalled, flushed '
                 'FROM pics_d INNER JOIN pics_c ON pics_c.addr = pics_d.addr;')
        data = cursor.execute(query).fetchall()

        self.addr = [t[0] for t in data]
        self.instr_type = [t[1] for t in data]

        self.base     = _snap([t[2] for t in data])
        self.fe_stall = _snap([t[3] for t in data])
        self.be_stall = _snap([t[4] for t in data])
        self.mispred  = _snap([t[5] for t in data])

        self.compute = _snap([t[6] for t in data])
        self.drained = _snap([t[7] for t in data])
        self.stalled = _snap([t[8] for t in data])
        self.flushed = _snap([t[9] for t in data])


class PICS_d:
    def __init__(self, instr, addr, base, fe_stall, be_stall, mispred):
        self.tag      = instr + ' | ' + addr[-4:]
        self.base     = float(base)
        self.fe_stall = float(fe_stall)
        self.be_stall = float(be_stall)
        self.mispred  = float(mispred)


class PICS_c:
    def __init__(self, instr, addr, compute, drained, stalled, flushed):
        self.tag     = instr + ' | ' + addr[-4:]
        self.compute = float(compute)
        self.drained = float(drained)
        self.stalled = float(stalled)
        self.flushed = float(flushed)


def index_nth_largest(a: np.ndarray, n: int) -> int:
    """Return flat index of the n-th largest element (n=1 → argmax)."""
    if n <= 0:
        raise ValueError("index_nth_largest: non-positive n")
    size = np.size(a)
    if n > size:
        raise ValueError("index_nth_largest: n out of bounds")
    return np.argpartition(a, size - n, axis=None)[size - n]


def _top_indices(scores: np.ndarray, n: int):
    return [index_nth_largest(scores, 1 + i) for i in range(n)]


def _make_dispatch(data: PicsData, indices):
    return [PICS_d(data.instr_type[i], data.addr[i],
                   data.base[i], data.fe_stall[i], data.be_stall[i], data.mispred[i])
            for i in indices]


def _make_commit(data: PicsData, indices):
    return [PICS_c(data.instr_type[i], data.addr[i],
                   data.compute[i], data.drained[i], data.stalled[i], data.flushed[i])
            for i in indices]


def _label_nonzero(ax, bars):
    ax.bar_label(bars, label_type='center',
                 labels=['' if v == 0 else f'{v:g}' for v in bars.datavalues])


def _plot_dispatch_bars(ax, pics, title):
    x = np.arange(len(pics))
    bottom = np.zeros(len(pics))
    for label, field in [('Base', 'base'), ('FE Stall', 'fe_stall'),
                         ('BE Stall', 'be_stall'), ('Mispred', 'mispred')]:
        counts = np.array([getattr(p, field) for p in pics])
        bars = ax.bar(x, counts, 0.4, label=label, bottom=bottom)
        bottom += counts
        _label_nonzero(ax, bars)
    ax.set_ylim(top=bottom.max() * 1.1)
    ax.set_xticks(x, [p.tag for p in pics], rotation=15, ha='right')
    ax.set_title(title)
    ax.legend()


def _plot_commit_bars(ax, pics, title):
    x = np.arange(len(pics))
    bottom = np.zeros(len(pics))
    for label, field in [('Compute', 'compute'), ('Drained', 'drained'),
                         ('Stalled', 'stalled'), ('Flushed', 'flushed')]:
        counts = np.array([getattr(p, field) for p in pics])
        bars = ax.bar(x, counts, 0.4, label=label, bottom=bottom)
        bottom += counts
        _label_nonzero(ax, bars)
    ax.set_ylim(top=bottom.max() * 1.1)
    ax.set_xticks(x, [p.tag for p in pics], rotation=15, ha='right')
    ax.set_title(title)
    ax.legend()


def plot_pics(data: PicsData, n: int, title: str, save_file: str):
    n = min(n, len(data.addr))

    dispatch_score = data.base + data.fe_stall + data.be_stall + data.mispred
    commit_score   = data.compute + data.drained + data.stalled + data.flushed
    total_score    = dispatch_score + commit_score

    top_d_idx = _top_indices(dispatch_score, n)
    top_c_idx = _top_indices(commit_score,   n)
    top_t_idx = _top_indices(total_score,    n)

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle(title)

    _plot_dispatch_bars(axes[0, 0], _make_dispatch(data, top_d_idx),
                        f'Largest stacks @ dipatch')
    _plot_commit_bars  (axes[0, 1], _make_commit  (data, top_c_idx),
                        f'Largest stacks @ commit')
    _plot_dispatch_bars(axes[1, 0], _make_dispatch(data, top_t_idx),
                        f'Largest total stacks (dispatch view)')
    _plot_commit_bars  (axes[1, 1], _make_commit  (data, top_t_idx),
                        f'Largest total stack (commit view)')

    fig.tight_layout()
    fig.savefig(save_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('db_file')
    parser.add_argument('-n', '--amount', type=int, required=True)
    parser.add_argument('-t', '--title',  required=True)
    args = parser.parse_args()

    data = PicsData(args.db_file)
    plot_pics(data, args.amount, args.title, args.title + '.png')
