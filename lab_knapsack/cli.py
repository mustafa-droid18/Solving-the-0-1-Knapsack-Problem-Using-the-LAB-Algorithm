"""Command-line interface.

Examples
--------
Solve a built-in single-knapsack benchmark::

    lab-knapsack single f6 --runs 5

Solve a weish multidimensional instance::

    lab-knapsack multiple "Multiple Knapsack Problem/Dataset/weish01.dat"
"""

import argparse
import statistics
import time

from .core import LAB
from .datasets import load_f_instance, load_weish


def _solve_many(problem, args):
    results = []
    start = time.perf_counter()
    for run in range(args.runs):
        seed = None if args.seed is None else args.seed + run
        lab = LAB(problem, groups=args.groups, individuals=args.individuals, seed=seed)
        results.append(lab.solve(iterations=args.iterations))
    elapsed = time.perf_counter() - start

    values = [r.best_value for r in results]
    best = max(results, key=lambda r: r.best_value)

    print(f"Runs               : {args.runs}")
    print(f"Iterations per run : {args.iterations}")
    print(f"Best               : {best.best_value:g}")
    print(f"Mean               : {statistics.fmean(values):g}")
    print(f"Worst              : {min(values):g}")
    if len(values) > 1:
        print(f"Std deviation      : {statistics.stdev(values):g}")
    optimum = getattr(problem, "optimum", None)
    if optimum:
        gap = 100 * (optimum - best.best_value) / optimum
        print(f"Known optimum      : {optimum:g}  (gap {gap:.2f}%)")
    print(f"Items selected     : {int(best.best_selection.sum())} / {problem.n_items}")
    print(f"Total time         : {elapsed:.1f}s ({elapsed / args.runs:.2f}s per run)")


def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--groups", type=int, default=3, help="LAB groups (default 3)")
    common.add_argument(
        "--individuals", type=int, default=5, help="individuals per group (default 5)"
    )
    common.add_argument("--runs", type=int, default=1, help="independent runs (default 1)")
    common.add_argument("--seed", type=int, default=None, help="random seed")

    parser = argparse.ArgumentParser(
        prog="lab-knapsack",
        description="Solve 0-1 knapsack problems with the LAB metaheuristic.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_single = sub.add_parser(
        "single", parents=[common], help="single 0-1 knapsack benchmark (f1-f20)"
    )
    p_single.add_argument("instance", help="benchmark name, e.g. f1")
    p_single.add_argument(
        "--iterations", type=int, default=250, help="iterations per run (default 250)"
    )

    p_multi = sub.add_parser(
        "multiple", parents=[common], help="multidimensional knapsack from a weish .dat file"
    )
    p_multi.add_argument("path", help="path to a weish .dat file")
    p_multi.add_argument(
        "--iterations", type=int, default=50, help="iterations per run (default 50)"
    )

    args = parser.parse_args(argv)

    if args.command == "single":
        problem = load_f_instance(args.instance)
        print(f"Instance {args.instance}: {problem.n_items} items, "
              f"capacity {problem.capacity:g}")
    else:
        problem = load_weish(args.path)
        print(f"Instance {args.path}: {problem.n_items} items, "
              f"{problem.n_constraints} constraints")

    _solve_many(problem, args)


if __name__ == "__main__":
    main()
