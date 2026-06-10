import numpy as np
import pytest

from lab_knapsack.core import LAB, saturation, weight_generation
from lab_knapsack.datasets import load_f_instance, load_weish

from pathlib import Path

DATASET_DIR = Path(__file__).resolve().parents[1] / "Multiple Knapsack Problem" / "Dataset"


def test_weight_generation_is_sorted_convex():
    rng = np.random.default_rng(0)
    for num in (2, 3, 5):
        w = weight_generation(rng, num)
        assert w.shape == (num,)
        assert np.isclose(w.sum(), 1.0)
        assert np.all(np.diff(w) <= 0)


def test_requires_three_individuals():
    with pytest.raises(ValueError):
        LAB(load_f_instance("f3"), individuals=2)


def test_solves_tiny_instance_to_optimum():
    # f3 and f4 are 4-item problems. A single LAB run can converge
    # prematurely, so mirror the benchmark protocol: best over a few runs.
    for name in ("f3", "f4"):
        problem = load_f_instance(name)
        best = max(
            LAB(problem, seed=s).solve(iterations=50).best_value for s in range(5)
        )
        assert best == problem.optimum


def test_history_is_monotone_and_solution_feasible():
    problem = load_f_instance("f1")
    result = LAB(problem, seed=7).solve(iterations=100)
    assert all(b >= a for a, b in zip(result.history, result.history[1:]))
    assert problem.solution_weight(result.best_encoding) <= problem.capacity
    assert result.best_value >= 0.9 * problem.optimum


def test_reproducible_with_seed():
    problem = load_f_instance("f6")
    a = LAB(problem, seed=123).solve(iterations=30)
    b = LAB(problem, seed=123).solve(iterations=30)
    assert a.best_value == b.best_value
    assert a.history == b.history


def test_multiple_knapsack_smoke():
    problem = load_weish(DATASET_DIR / "weish01.dat")
    result = LAB(problem, seed=1).solve(iterations=30)
    loads = problem.solution_loads(result.best_encoding)
    assert np.all(loads <= problem.capacities)
    # Should land within 20% of the known optimum even in a short run.
    assert result.best_value >= 0.8 * problem.optimum


def test_saturation():
    assert saturation([5.0, 5.0, 5.0])
    assert not saturation([1.0, 2.0, 10.0])
