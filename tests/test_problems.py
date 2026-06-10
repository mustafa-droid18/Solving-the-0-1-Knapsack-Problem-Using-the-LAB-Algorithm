import numpy as np
import pytest

from lab_knapsack.problems import (
    DROPPED_VALUE,
    MultipleKnapsack,
    SingleKnapsack,
)


def encode(selection):
    """Binary selection -> continuous encoding (75 selected, 25 not)."""
    return np.where(np.asarray(selection, dtype=bool), 75.0, 25.0)


class TestSingleKnapsack:
    def test_items_sorted_by_ratio_ascending(self):
        p = SingleKnapsack(weights=[1, 1, 1], values=[30, 10, 20], capacity=2)
        assert list(p.values) == [10, 20, 30]

    def test_feasible_solution_untouched(self):
        p = SingleKnapsack(weights=[5, 5], values=[10, 10], capacity=10)
        profit, repaired = p.evaluate(encode([1, 1]))
        assert profit == 20
        assert np.all(repaired >= 50)

    def test_overweight_solution_repaired_to_feasible(self):
        p = SingleKnapsack(weights=[5, 5, 5], values=[1, 2, 3], capacity=10)
        profit, repaired = p.evaluate(encode([1, 1, 1]))
        # Lowest-ratio item (value 1) is dropped first.
        assert profit == 5
        assert p.solution_weight(repaired) <= p.capacity
        assert repaired[0] == DROPPED_VALUE

    def test_empty_selection_scores_zero(self):
        p = SingleKnapsack(weights=[5], values=[10], capacity=5)
        profit, _ = p.evaluate(encode([0]))
        assert profit == 0

    def test_mismatched_lengths_rejected(self):
        with pytest.raises(ValueError):
            SingleKnapsack(weights=[1, 2], values=[1], capacity=5)

    def test_to_input_order_round_trips(self):
        p = SingleKnapsack(weights=[1, 1, 1], values=[30, 10, 20], capacity=3)
        # Internal order is by ascending ratio: values [10, 20, 30].
        restored = p.to_input_order(p.values)
        assert list(restored) == [30, 10, 20]


class TestMultipleKnapsack:
    def make(self):
        return MultipleKnapsack(
            values=[10, 20, 30],
            weights=[[5, 5, 5], [1, 9, 1]],
            capacities=[10, 10],
        )

    def test_feasible_solution_untouched(self):
        p = self.make()
        full_value = p.values.sum()
        # Select everything under generous capacities.
        q = MultipleKnapsack(
            values=p.values, weights=p.weights, capacities=[100, 100]
        )
        profit, _ = q.evaluate(encode([1, 1, 1]))
        assert profit == full_value

    def test_repair_reaches_feasibility(self):
        p = self.make()
        profit, repaired = p.evaluate(encode([1, 1, 1]))
        loads = p.solution_loads(repaired)
        assert np.all(loads <= p.capacities)
        assert profit == p.values @ p.decode(repaired)

    def test_shape_validation(self):
        with pytest.raises(ValueError):
            MultipleKnapsack(values=[1, 2], weights=[[1, 2, 3]], capacities=[5])

    def test_constraints_sorted_by_capacity(self):
        p = MultipleKnapsack(
            values=[1, 2],
            weights=[[9, 9], [1, 1]],
            capacities=[50, 5],
        )
        assert list(p.capacities) == [5, 50]
        assert list(p.weights[0]) in ([1, 1],)
