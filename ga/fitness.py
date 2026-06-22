from __future__ import annotations
 
from models.assignment import Assignment
from models.session import Session
 
from constraints.soft_constraints import compute_total_penalty
from constraints.hard_constraints import ALL_HARD_CONSTRAINTS
 
from ga.chromosome import chromosome_to_solution
 
 
# FIX: hệ số phạt cho MỖI vi phạm hard constraint riêng lẻ.
# Phải đủ lớn để áp đảo mọi tổ hợp soft penalty thực tế (soft penalty của
# bài toán này tối đa cỡ vài trăm/vài nghìn), nhưng vẫn hữu hạn để giữ
# được gradient giữa các mức độ vi phạm khác nhau.
HARD_VIOLATION_PENALTY = 100_000
 
 
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
 
    # FIX: hàm mới — đếm số lượt vi phạm hard constraint trên TOÀN BỘ
    # timetable, dùng từng hàm trong ALL_HARD_CONSTRAINTS với "existing"
    # là các assignment xét trước nó trong list (đủ để phát hiện mọi cặp
    # xung đột đôi một, vì mỗi cặp vi phạm sẽ được tính khi xét đến phần
    # tử thứ hai trong cặp).
    def _count_hard_violations(self, assignments):
        violations = 0
        for i, a in enumerate(assignments):
            existing = assignments[:i]
            for fn in ALL_HARD_CONSTRAINTS:
                if not fn(a, existing, self.parsed_data):
                    violations += 1
        return violations
 
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
 
        # FIX: thay is_global_feasible (chỉ trả True/False) bằng việc đếm
        # số vi phạm cụ thể, để có gradient liên tục thay vì một mặt
        # phẳng -1_000_000 cho mọi mức độ vi phạm.
        violations = self._count_hard_violations(assignments)
 
        if solution_idx == 0:
            print(
                f"[DEBUG] Gen {ga_instance.generations_completed} | "
                f"feasible={violations == 0} | violations={violations}"
            )
 
        if violations > 0:
            # FIX: phạt theo số lượng vi phạm, không phải hằng số cố định
            return -float(HARD_VIOLATION_PENALTY * violations)
 
        penalty = compute_total_penalty(
            assignments,
            self.parsed_data,
        )
 
        return -float(penalty)