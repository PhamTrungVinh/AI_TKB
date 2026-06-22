"""
Chuyển đổi giữa:
    CSP Solution <-> GA Chromosome
CSP Solution:
{
    task_id: Value(...)
}

GA Chromosome:
[
    domain_index,
    domain_index,
    ...
]
"""

from __future__ import annotations

from typing import Dict, List

from csp.ac3 import Value


def solution_to_chromosome(
    tasks: list[dict],
    domains: dict[str, list[Value]],
    solution: dict[str, Value],
) -> list[int]:
    """
    Convert CSP solution -> chromosome.

    Parameters
    ----------
    tasks
        Danh sách task theo thứ tự cố định.

    domains
        Domain của từng task.

    solution
        {task_id -> Value}

    Returns
    -------
    list[int]
        Chromosome cho GA.
    """

    chromosome: list[int] = []

    for task in tasks:
        task_id = task["task_id"]

        value = solution[task_id]

        try:
            gene = domains[task_id].index(value)
        except ValueError:
            raise ValueError(
                f"Value không tồn tại trong domain của task {task_id}"
            )

        chromosome.append(gene)

    return chromosome


def chromosome_to_solution(
    tasks: list[dict],
    domains: dict[str, list[Value]],
    chromosome: list[int],
) -> dict[str, Value]:
    """
    Convert chromosome -> CSP solution.

    Parameters
    ----------
    tasks
        Danh sách task.

    domains
        Domain từng task.

    chromosome
        List gene.

    Returns
    -------
    dict[str, Value]
    """

    if len(chromosome) != len(tasks):
        raise ValueError(
            f"Chromosome length={len(chromosome)} "
            f"không khớp số task={len(tasks)}"
        )

    solution: dict[str, Value] = {}

    for gene, task in zip(chromosome, tasks):

        task_id = task["task_id"]

        domain = domains[task_id]

        gene = int(round(gene))
        gene = max(0, min(gene, len(domain) - 1))

        solution[task_id] = domain[gene]

    return solution


def build_gene_space(
    tasks: list[dict],
    domains: dict[str, list[Value]],
) -> list[list[int]]:
    """
    Sinh gene_space cho PyGAD.

    Ví dụ:

    [
        [0,1,2],
        [0,1],
        [0,1,2,3]
    ]
    """

    gene_space: list[list[int]] = []

    for task in tasks:

        task_id = task["task_id"]

        domain_size = len(domains[task_id])

        gene_space.append(
            list(range(domain_size))
        )

    return gene_space