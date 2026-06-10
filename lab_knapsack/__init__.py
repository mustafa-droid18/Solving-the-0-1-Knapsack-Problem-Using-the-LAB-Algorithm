"""LAB (Leader-Advocate-Believer) metaheuristic for 0-1 knapsack problems.

The LAB algorithm is a socio-inspired metaheuristic (Reddy, Kulkarni,
Krishnasamy, Shastri & Gandomi, Soft Computing 2023) in which a population
is organised into groups of one Leader, one Advocate and several Believers.
Each role updates its position from weighted combinations of the others,
driving simultaneous exploration and exploitation.

This package applies LAB to the single 0-1 knapsack problem and the
multidimensional (multiple) 0-1 knapsack problem.
"""

from .core import LAB, Result
from .problems import SingleKnapsack, MultipleKnapsack
from .datasets import F_INSTANCES, load_f_instance, load_weish

__all__ = [
    "LAB",
    "Result",
    "SingleKnapsack",
    "MultipleKnapsack",
    "F_INSTANCES",
    "load_f_instance",
    "load_weish",
]

__version__ = "1.0.0"
