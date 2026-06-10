"""The LAB (Leader-Advocate-Believer) optimization engine.

The population is split into groups. Within each group, index 0 is the
Leader, index 1 the Advocate and the rest are Believers. Every iteration
each role moves to a weighted convex combination of the others:

    leader    <- w1 . (global_leader, advocate, mean(believers))
    advocate  <- w2 . (leader, mean(believers))
    believer  <- w3 . (leader, advocate)

where each weight vector is random, normalised to sum to 1 and sorted in
descending order so the first component dominates.

When the best value stops improving (saturation), the working global
leader is perturbed by switching a few unselected items on, which lets the
search escape local optima.
"""

from dataclasses import dataclass, field

import numpy as np

from .problems import SELECTION_THRESHOLD


@dataclass
class Result:
    """Outcome of a LAB run."""

    best_value: float
    best_encoding: np.ndarray
    best_selection: np.ndarray
    history: list = field(default_factory=list)

    @property
    def iterations(self):
        return len(self.history) - 1


def weight_generation(rng, num):
    """Random convex weights sorted in descending order."""
    w = rng.random(num)
    return np.sort(w / w.sum())[::-1]


class LAB:
    """LAB metaheuristic over a knapsack problem instance.

    Parameters
    ----------
    problem : SingleKnapsack or MultipleKnapsack
        Anything exposing ``n_items``, ``init_low``/``init_high``,
        ``evaluate(x) -> (profit, repaired_x)`` and ``decode(x)``.
    groups : int
        Number of LAB groups.
    individuals : int
        Individuals per group (1 leader + 1 advocate + believers).
    seed : int, optional
        Seed for reproducible runs.
    perturb_every : int, optional
        How often (iterations) to check for saturation. Defaults to the
        problem's ``perturb_every``.
    perturb_flips : int, optional
        How many unselected items each perturbation switches on. Defaults
        to the problem's ``perturb_flips``.
    perturb_rounds : int
        Compounding flip rounds applied per perturbation event. The total
        kick is ``perturb_rounds * perturb_flips`` items switched on, which
        the repair operator then prunes back to feasibility.
    """

    def __init__(
        self,
        problem,
        groups=3,
        individuals=5,
        seed=None,
        perturb_every=None,
        perturb_flips=None,
        perturb_rounds=6,
    ):
        if individuals < 3:
            raise ValueError("need at least 3 individuals: leader, advocate, believer")
        self.problem = problem
        self.groups = groups
        self.individuals = individuals
        self.rng = np.random.default_rng(seed)
        self.perturb_every = perturb_every or getattr(problem, "perturb_every", 10)
        self.perturb_flips = perturb_flips or getattr(problem, "perturb_flips", 2)
        self.perturb_rounds = perturb_rounds

    def _init_population(self):
        p = self.problem
        pop = self.rng.uniform(
            p.init_low, p.init_high, (self.groups, self.individuals, p.n_items)
        )
        return np.round(pop, 2)

    def _evaluate_and_sort(self, population):
        """Score every individual, sort each group by fitness descending.

        Returns the sorted population, the best raw encoding (which guides
        the search), its repaired feasible counterpart, and its value.
        """
        writeback = getattr(self.problem, "repair_writeback", False)
        best_value = -np.inf
        best = best_repaired = None
        for g in range(self.groups):
            fitness = np.empty(self.individuals)
            repairs = [None] * self.individuals
            for i in range(self.individuals):
                fitness[i], repairs[i] = self.problem.evaluate(population[g, i])
                if writeback:
                    population[g, i] = repairs[i]
            order = np.argsort(fitness)[::-1]
            population[g] = population[g][order]
            if fitness[order[0]] > best_value:
                best_value = fitness[order[0]]
                best = population[g, 0].copy()
                best_repaired = repairs[order[0]]
        return population, best, best_repaired, best_value

    def _update(self, population, global_leader):
        new = population.copy()
        for g in range(self.groups):
            leader, advocate = population[g, 0], population[g, 1]
            believers_mean = population[g, 2:].mean(axis=0)

            w1 = weight_generation(self.rng, 3)
            new[g, 0] = w1[0] * global_leader + w1[1] * advocate + w1[2] * believers_mean

            w2 = weight_generation(self.rng, 2)
            new[g, 1] = w2[0] * leader + w2[1] * believers_mean

            for j in range(2, self.individuals):
                w3 = weight_generation(self.rng, 2)
                new[g, j] = w3[0] * leader + w3[1] * advocate
        return new

    def _flip_unselected(self, x):
        """Switch up to ``perturb_flips`` unselected items on."""
        x = x.copy()
        flipped, guard = 0, 0
        while flipped < self.perturb_flips and guard < 20 * self.problem.n_items:
            i = self.problem.sample_index(self.rng)
            if x[i] < SELECTION_THRESHOLD:
                x[i] = SELECTION_THRESHOLD + 1.0
                flipped += 1
            guard += 1
        return x

    def _perturb_leader(self, gl):
        """Kick a saturated leader by switching many unselected items on.

        The flips compound over several rounds and the result is accepted
        unconditionally: the kick must be strong enough to pull the whole
        population out of the local optimum it has collapsed into.
        """
        candidate = gl
        for _ in range(self.perturb_rounds):
            candidate = self._flip_unselected(candidate)
        value, repaired = self.problem.evaluate(candidate)
        return candidate, value, repaired

    def solve(self, iterations=250):
        """Run LAB and return the best solution found."""
        population = self._init_population()
        population, gl, gl_repaired, gl_value = self._evaluate_and_sort(population)
        elite, elite_value = gl_repaired.copy(), gl_value
        history = [elite_value]
        recent = [gl_value]

        for it in range(1, iterations + 1):
            population = self._update(population, gl)
            population, gl, gl_repaired, gl_value = self._evaluate_and_sort(population)
            if gl_value > elite_value:
                elite, elite_value = gl_repaired.copy(), gl_value
            recent.append(gl_value)

            if it % self.perturb_every == 0:
                if saturation(recent):
                    gl, gl_value, repaired = self._perturb_leader(gl)
                    if gl_value > elite_value:
                        elite, elite_value = repaired.copy(), gl_value
                recent = []

            history.append(elite_value)

        return Result(
            best_value=elite_value,
            best_encoding=elite,
            best_selection=self.problem.decode(elite),
            history=history,
        )


def saturation(history, tolerance=1e-6):
    """True when the running mean of best values has converged to the last."""
    return abs(sum(history) / len(history) - history[-1]) < tolerance
