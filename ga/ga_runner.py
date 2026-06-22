"""
ga_runner.py
"""

from __future__ import annotations

import pygad

from .chromosome import (
    build_gene_space,
    solution_to_chromosome,
    chromosome_to_solution,
)

from ga.fitness import FitnessEvaluator


def run_ga(
    tasks,
    domains,
    parsed_data,
    initial_solution,
    generations=200,
    population_size=50,
):
    """
    Parameters
    ----------
    initial_solution:
        dict[task_id -> Value]

    Returns
    -------
    (
        best_solution,
        best_fitness
    )
    """

    gene_space = build_gene_space(
        tasks,
        domains,
    )

    seed = solution_to_chromosome(
        tasks,
        domains,
        initial_solution,
    )

    population = [seed]

    for _ in range(population_size - 1):
        population.append(seed.copy())

    fitness_obj = FitnessEvaluator(
        tasks=tasks,
        domains=domains,
        parsed_data=parsed_data,
    )

    ga = pygad.GA(
        num_generations=generations,

        sol_per_pop=population_size,

        num_parents_mating=max(
            2,
            population_size // 2,
        ),

        fitness_func=fitness_obj.fitness,

        initial_population=population,

        gene_space=gene_space,

        parent_selection_type="tournament",

        crossover_type="two_points",

        mutation_type="random",

        mutation_percent_genes=5,

        keep_elitism=5,

        suppress_warnings=True,
    )

    ga.run()

    best_chromosome, best_fitness, _ = ga.best_solution()

    best_solution = chromosome_to_solution(
        tasks,
        domains,
        best_chromosome,
    )

    return best_solution, best_fitness