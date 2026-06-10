"""Knapsack problem definitions with solution decoding and repair.

Candidate solutions are encoded as continuous vectors: entry x[i] >= 50
means item i is selected, anything below means it is not. The continuous
encoding is what the LAB role-update equations blend; the repair operators
push infeasible entries back below the selection threshold.
"""

import math

import numpy as np

SELECTION_THRESHOLD = 50.0
# Value a repaired (dropped) item is set to: just below the threshold so
# the item is deselected but stays close to the decision boundary.
DROPPED_VALUE = 49.0


class SingleKnapsack:
    """Classic 0-1 knapsack: one capacity constraint.

    Items are sorted internally by ascending value-to-weight ratio so the
    repair operator can drop the least efficient selected items first.
    """

    init_low, init_high = 0.0, 100.0
    # Leader perturbation defaults: (check interval, items flipped per round).
    perturb_every, perturb_flips = 10, 2
    # Keep raw encodings in the population; repair only when scoring.
    # Writing repaired encodings back reduces diversity and hurts results.
    repair_writeback = False

    def __init__(self, weights, values, capacity):
        weights = np.asarray(weights, dtype=float)
        values = np.asarray(values, dtype=float)
        if weights.shape != values.shape:
            raise ValueError(
                f"weights and values must match: {weights.size} != {values.size}"
            )
        order = np.argsort(values / weights)
        self.weights = weights[order]
        self.values = values[order]
        self.capacity = float(capacity)
        self._order = order

    @property
    def n_items(self):
        return self.weights.size

    def decode(self, x):
        """Binary selection vector (in internal sorted item order)."""
        return (np.asarray(x) >= SELECTION_THRESHOLD).astype(float)

    def evaluate(self, x):
        """Return (profit, repaired_encoding) for a candidate vector.

        If the selection is overweight, selected items are dropped in
        ascending ratio order until it fits.
        """
        x = np.asarray(x, dtype=float).copy()
        chosen = self.decode(x)
        total_weight = float(np.dot(self.weights, chosen))
        profit = float(np.dot(self.values, chosen))

        for i in range(self.n_items):
            if total_weight <= self.capacity:
                break
            if chosen[i]:
                chosen[i] = 0.0
                total_weight -= self.weights[i]
                profit -= self.values[i]
                x[i] = DROPPED_VALUE
        return profit, x

    def solution_weight(self, x):
        return float(np.dot(self.weights, self.decode(x)))

    def sample_index(self, rng):
        """Uniform random item index (used by leader perturbation)."""
        return int(rng.integers(self.n_items))

    def to_input_order(self, x):
        """Map a vector from internal (ratio-sorted) order back to input order."""
        out = np.empty_like(np.asarray(x))
        out[self._order] = x
        return out


class MultipleKnapsack:
    """Multidimensional 0-1 knapsack: one weight per item per constraint.

    Constraints are sorted by capacity and items by value-to-weight ratio
    under the tightest constraint, so the exponentially biased repair
    operator preferentially drops low-ratio items.
    """

    init_low, init_high = 50.0, 100.0
    perturb_every, perturb_flips = 5, 3
    # The stochastic repair operator doubles as a mutation source here, so
    # repaired encodings replace the originals in the population.
    repair_writeback = True

    def __init__(
        self, values, weights, capacities, optimum=None, lambda_param=0.19, seed=None
    ):
        values = np.asarray(values, dtype=float)
        weights = np.atleast_2d(np.asarray(weights, dtype=float))
        capacities = np.asarray(capacities, dtype=float)
        if weights.shape != (capacities.size, values.size):
            raise ValueError(
                f"weights must be (n_constraints, n_items) = "
                f"({capacities.size}, {values.size}), got {weights.shape}"
            )

        constraint_order = np.argsort(capacities)
        capacities = capacities[constraint_order]
        weights = weights[constraint_order]

        with np.errstate(divide="ignore"):
            ratio = np.where(weights[0] > 0, values / weights[0], np.inf)
        item_order = np.argsort(ratio)
        self.values = values[item_order]
        self.weights = weights[:, item_order]
        self._order = item_order
        self.capacities = capacities
        self.optimum = optimum
        self.lambda_param = lambda_param
        self._rng = np.random.default_rng(seed)

    @property
    def n_items(self):
        return self.values.size

    @property
    def n_constraints(self):
        return self.capacities.size

    def decode(self, x):
        return (np.asarray(x) >= SELECTION_THRESHOLD).astype(float)

    def _violated(self, chosen):
        loads = self.weights @ chosen
        return bool(np.any(loads > self.capacities))

    def _biased_index(self):
        """Exponentially distributed index, biased toward low-ratio items."""
        draw = int(-1 / self.lambda_param * math.log(1 - self._rng.random()))
        return min(draw, self.n_items - 1)

    def sample_index(self, rng):
        """Biased item index (used by leader perturbation)."""
        return self._biased_index()

    def evaluate(self, x):
        """Return (profit, repaired_encoding) for a candidate vector.

        While any constraint is violated, drop a randomly chosen selected
        item, biased toward the low value-to-weight end of the ordering.
        """
        x = np.asarray(x, dtype=float).copy()
        chosen = self.decode(x)

        while self._violated(chosen):
            i = self._biased_index()
            while not chosen[i]:
                i = self._biased_index()
            chosen[i] = 0.0
            x[i] = DROPPED_VALUE

        profit = float(np.dot(self.values, chosen))
        return profit, x

    def solution_loads(self, x):
        return self.weights @ self.decode(x)

    def to_input_order(self, x):
        """Map a vector from internal (ratio-sorted) order back to input order."""
        out = np.empty_like(np.asarray(x))
        out[self._order] = x
        return out
