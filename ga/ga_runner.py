from __future__ import annotations
 
import pygad
import random
 
from ga.chromosome import (
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
    # FIX: cho phép tinh chỉnh tỉ lệ đột biến khi sinh population ban đầu
    # từ bên ngoài, thay vì hard-code 0.05 (vốn vẫn đủ làm vỡ ràng buộc vì
    # mỗi task có hàng chục/hàng trăm hàng xóm ràng buộc trong domain lớn).
    init_mutation_rate=0.02,
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
        mutated = seed.copy()
        for i in range(len(mutated)):
            # FIX: dùng init_mutation_rate (mặc định 2%, trước là 5%) để
            # giảm số gene bị xáo ngẫu nhiên mỗi cá thể khởi tạo — giảm
            # khả năng phá vỡ ràng buộc liên-task ngay từ population đầu.
            if random.random() < init_mutation_rate:
                mutated[i] = random.choice(gene_space[i])
        population.append(mutated)
 
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
 
        # FIX: giữ mutation_num_genes=1 (đột biến nhẹ mỗi thế hệ) để cá
        # thể con vẫn còn gần seed gốc, tăng khả năng giữ được feasible
        # hoặc chỉ vi phạm rất ít so với cha mẹ.
        mutation_num_genes=1,
 
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