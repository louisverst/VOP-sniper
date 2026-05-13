# VOP-sniper

Built by Tobe De Brabander, Jaco Lagrange, and Louis Verstraeten as part of *Vakoverschrijdend Project* — a cross-disciplinary capstone in the Bachelor of Computer Science Engineering at Ghent University.

## Building the simulator
Clone by entering the following in your terminal:
```bash
git clone --recurse-submodules https://github.com/louisverst/VOP-sniper.git
```
Build the simulator:
```bash
cd snipersim
make
```


## Microbenchmarks
Some code snippets (from https://github.com/VerticalResearchGroup/microbench) adjusted for the Sniper simulator can be found under `microbench/`. You can `make` them in one fell swoop with:
```bash
make -C microbench/
```

A description of every microbenchmark's intent can be printed to the terminal:
```bash
microbench/describe.sh
```


## ROI
The microbenchmarks make use of the *ROI* feature of the simulator. You can mark the beginning of a region of interest with `ROI_BEGIN()` and the end with `ROI_END()`. The definition of these macros is in `microbench/common.h` and `microbench/sim_api.h`. These files must be included in your own simulation programs.


## Running the simulator
For detailed instructions on the usage of the simulator see https://github.com/louisverst/snipersim . `run.sh` and `run-roi.sh` provide a template to make repeated invocation of the simulator with arguments easier (like directing output to an `out/` directory with the `-d` flag).

> IMPORTANT: Modern CPU's (such as the Intel Core Ultra 9) need to use the `--sde-arch=future` flag when running the simulator.


## PICS
The generated *PICS* data is included in the generated `sqlite3` database.


## Scripts
Some scripts used in the development of the *PICS* are under `scripts/`.

`run-all-benchs.py` can be used to generate the database files and a plot of all microbenchmarks (note that the microbenchmarks first have to be `make`ed).

To generate a visual plot of the *PICS* from the output of the simulator, the `plot.py` script can be used. It takes the path to the generated `sqlite3` file, a title for the plot can be set with the `-t` flag, the number of instructions for which the *PICS* are generated can be set with `-n` and the output path can be set with `-o`.
```bash
plot.py [file] [-t] [-n] [-o]
```

The `invariants/` directory contains scripts used to write the report (which can also be found under `report/`, but it does not serve as documentation).