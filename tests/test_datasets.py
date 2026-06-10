from pathlib import Path

import pytest

from lab_knapsack.datasets import F_INSTANCES, load_f_instance, load_weish

DATASET_DIR = Path(__file__).resolve().parents[1] / "Multiple Knapsack Problem" / "Dataset"

KNOWN_WEISH_OPTIMA = {
    "weish01.dat": 4554,
    "weish05.dat": 4514,
    "weish15.dat": 7486,
    "weish30.dat": 11191,
}


def test_all_f_instances_consistent():
    for name, (capacity, weights, values, _) in F_INSTANCES.items():
        assert len(weights) == len(values), name
        assert capacity > 0, name


def test_load_f_instance_known_optimum():
    p = load_f_instance("f1")
    assert p.n_items == 10
    assert p.optimum == 295


def test_unknown_instance_rejected():
    with pytest.raises(KeyError):
        load_f_instance("f99")


@pytest.mark.parametrize("fname,optimum", KNOWN_WEISH_OPTIMA.items())
def test_load_weish_header(fname, optimum):
    p = load_weish(DATASET_DIR / fname)
    assert p.optimum == optimum
    assert p.n_constraints == 5


def test_all_weish_files_parse():
    files = sorted(DATASET_DIR.glob("weish*.dat"))
    assert len(files) == 30
    for f in files:
        p = load_weish(f)
        assert p.n_items in (30, 40, 50, 60, 70, 80, 90)
        assert p.weights.shape == (p.n_constraints, p.n_items)
