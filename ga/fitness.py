"""
fitness.py
"""

from __future__ import annotations

from models.assignment import Assignment
from models.session import Session

from constraints.soft_constraints import compute_total_penalty

from constraints.hard_constraints import is_global_feasible


from ga.chromosome import chromosome_to_solution


class FitnessEvaluator:

    def __init__(
        self,
        tasks,
        domains,
        parsed_data,
    ):
        self.tasks = tasks
        self.domains = domains
        self.parsed_data = parsed_data

        self.task_map = {
            t["task_id"]: t
            for t in tasks
        }

    def _build_assignments(
        self,
        solution,
    ):
        """
        solution:
            {task_id -> Value}

        ->
            list[Assignment]
        """

        assignments = []

        for task_id, value in solution.items():

            task = self.task_map[task_id]

            assignments.append(
                Assignment(
                    class_id=task["class_id"],
                    subject=self.parsed_data["subjects"][task["subject_id"]],
                    teacher=self.parsed_data["teachers"][value.teacher_id],
                    room=self.parsed_data["rooms"][value.room_id],
                    session=Session(
                        day=value.day,
                        period=value.period,
                    ),
                )
            )

        return assignments

    def fitness(
        self,
        ga_instance,
        chromosome,
        solution_idx,
    ):

        solution = chromosome_to_solution(
            self.tasks,
            self.domains,
            chromosome,
        )

        assignments = self._build_assignments(
            solution
        )

        if not is_global_feasible(
            assignments,
            self.parsed_data,
        ):
            return -1_000_000

        penalty = compute_total_penalty(
            assignments,
            self.parsed_data,
        )

        return -float(penalty)