"""
backtracking.py
Bộ giải CSP chính cho bài toán xếp thời khoá biểu.

Kết hợp toàn bộ các module CSP:
  AC-3             → thu hẹp domain trước khi tìm kiếm
  Forward Checking → phát hiện sớm thất bại trong khi tìm kiếm
  MRV + Degree     → chọn biến thông minh
  LCV              → thứ tự giá trị tối ưu
  Time limit       → tự động dừng nếu quá thời gian

Cách dùng cơ bản:
    from csp.backtracking import CSPSolver

    solver = CSPSolver(tasks=norm.assignment_tasks, parsed_data=parsed)
    assignments = solver.solve()
    solver.print_stats()
"""

from __future__ import annotations
import sys
import os
import time
import copy

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.assignment import Assignment
from models.session import Session

from ac3 import Value, build_initial_domains, run_ac3
from forward_checking import forward_check, forward_check_with_propagation
from heuristics import select_variable, order_domain_values, compatible


# ────────────────────────────────────────────────────────────────────────────
# Solver
# ────────────────────────────────────────────────────────────────────────────

class CSPSolver:
    """
    Giải bài toán xếp thời khoá biểu bằng CSP Backtracking.

    Parameters
    ----------
    tasks        : list[dict] – assignment_tasks từ Normalizer
    parsed_data  : dict       – output của excel_parser.parse_excel()
    days         : danh sách ngày học       (None → Mon–Fri)
    periods      : danh sách tiết trong ngày (None → 1–10)
    use_ac3      : chạy AC-3 trước backtracking
    use_fc       : dùng Forward Checking trong backtracking
    use_mac      : dùng MAC (Forward Checking mở rộng với lan truyền singleton)
                   Chỉ có hiệu lực khi use_fc=True
    use_mrv      : dùng MRV khi chọn biến
    use_degree   : dùng Degree tiebreak kết hợp MRV
    use_lcv      : dùng LCV khi sắp xếp giá trị
    time_limit   : giới hạn giây (None = không giới hạn)
    """

    def __init__(self,
                 tasks: list[dict],
                 parsed_data: dict,
                 days: list[str] | None = None,
                 periods: list[int] | None = None,
                 use_ac3: bool = True,
                 use_fc: bool = True,
                 use_mac: bool = False,
                 use_mrv: bool = True,
                 use_degree: bool = True,
                 use_lcv: bool = True,
                 time_limit: float | None = 300.0):

        self.tasks       = tasks
        self.parsed_data = parsed_data
        self.days        = days
        self.periods     = periods
        self.use_ac3     = use_ac3
        self.use_fc      = use_fc
        self.use_mac     = use_mac
        self.use_mrv     = use_mrv
        self.use_degree  = use_degree
        self.use_lcv     = use_lcv
        self.time_limit  = time_limit

        # Lookup nhanh theo task_id
        self.task_map: dict[str, dict] = {t["task_id"]: t for t in tasks}

        self.stats: dict = {
            "nodes_explored" : 0,
            "backtracks"     : 0,
            "ac3_pruned"     : 0,
            "solve_time_sec" : 0.0,
            "status"         : "not_started",
        }
        self._start_time: float = 0.0

    # ── Public API ────────────────────────────────────────────────────────────

    def solve(self) -> list[Assignment] | None:
        """
        Chạy bộ giải và trả về:
          list[Assignment]  nếu tìm được lời giải
          None              nếu bất khả thi hoặc hết thời gian
        """
        self._start_time = time.time()
        self.stats["status"] = "running"

        # ── Bước 1: Khởi tạo domain ──────────────────────────────────────────
        domains = build_initial_domains(
            self.tasks, self.parsed_data, self.days, self.periods
        )

        # Kiểm tra domain rỗng ngay từ đầu
        empty_tasks = [tid for tid, d in domains.items() if not d]
        if empty_tasks:
            self.stats["status"] = "infeasible"
            print(f"[CSP] ✗ Domain rỗng từ đầu với: {empty_tasks}")
            return None

        total_values_before = sum(len(d) for d in domains.values())
        print(f"[CSP] Tổng giá trị ban đầu: {total_values_before:,} "
              f"({len(self.tasks)} tasks)")

        # ── Bước 2: AC-3 ─────────────────────────────────────────────────────
        if self.use_ac3:
            print("[CSP] Chạy AC-3...")
            feasible, domains = run_ac3(domains, self.tasks)
            if not feasible:
                self.stats["status"] = "infeasible"
                print("[CSP] ✗ AC-3 phát hiện bất khả thi.")
                self._record_time()
                return None

            total_after = sum(len(d) for d in domains.values())
            pruned = total_values_before - total_after
            self.stats["ac3_pruned"] = pruned
            print(f"[CSP] AC-3 hoàn tất: loại bỏ {pruned:,} giá trị "
                  f"({total_after:,} còn lại)")

        # ── Bước 3: Backtracking ─────────────────────────────────────────────
        print("[CSP] Bắt đầu backtracking...")
        try:
            result = self._backtrack(
                assigned  = {},
                domains   = domains,
                unassigned= list(self.tasks),
            )
        except _TimeoutError:
            self.stats["status"] = "timeout"
            self._record_time()
            print(f"[CSP] ✗ Hết thời gian ({self.time_limit}s).")
            return None

        self._record_time()

        if result is None:
            self.stats["status"] = "infeasible"
            print("[CSP] ✗ Không tìm được lời giải.")
            return None

        self.stats["status"] = "solved"
        assignments = self._build_assignments(result)
        print(f"[CSP] ✔ Tìm được lời giải với {len(assignments)} assignments.")
        return assignments

    def print_stats(self) -> None:
        """In bảng thống kê quá trình tìm kiếm."""
        s = self.stats
        heuristics = []
        if self.use_mrv:    heuristics.append("MRV")
        if self.use_degree: heuristics.append("DEG")
        if self.use_lcv:    heuristics.append("LCV")
        if self.use_ac3:    heuristics.append("AC-3")
        if self.use_mac:    heuristics.append("MAC")
        elif self.use_fc:   heuristics.append("FC")

        print(f"\n{'═'*44}")
        print(f"  {'CSP Solver Statistics':^40}")
        print(f"{'─'*44}")
        print(f"  Trạng thái   : {s['status'].upper()}")
        print(f"  Thời gian    : {s['solve_time_sec']} giây")
        print(f"  Nodes khám   : {s['nodes_explored']:>10,}")
        print(f"  Backtracks   : {s['backtracks']:>10,}")
        if self.use_ac3:
            print(f"  AC-3 cắt tỉa : {s['ac3_pruned']:>10,} giá trị")
        print(f"  Heuristics   : {', '.join(heuristics) or 'None'}")
        print(f"{'═'*44}\n")

    # ── Core backtracking ─────────────────────────────────────────────────────

    def _backtrack(self,
                   assigned:   dict[str, Value],
                   domains:    dict[str, list[Value]],
                   unassigned: list[dict]) -> dict[str, Value] | None:
        """
        Hàm đệ quy backtracking chính.

        Parameters
        ----------
        assigned   : {task_id → Value} các task đã gán
        domains    : domain hiện tại cho mỗi task chưa gán
        unassigned : list các task chưa gán (theo thứ tự sẽ chọn)

        Returns
        -------
        dict đầy đủ {task_id → Value} nếu giải được, None nếu thất bại.
        """
        # Kiểm tra time limit
        if self.time_limit and (time.time() - self._start_time) > self.time_limit:
            raise _TimeoutError()

        # Base case: tất cả đã gán → lời giải
        if not unassigned:
            return assigned

        # ── Chọn biến tiếp theo ───────────────────────────────────────────────
        task      = select_variable(unassigned, domains, self.use_mrv, self.use_degree)
        remaining = [t for t in unassigned if t["task_id"] != task["task_id"]]

        # ── Sắp xếp giá trị ──────────────────────────────────────────────────
        values = order_domain_values(task, domains, remaining, self.use_lcv)

        for value in values:
            self.stats["nodes_explored"] += 1

            # ── Kiểm tra nhất quán + cắt tỉa ─────────────────────────────────
            if self.use_fc:
                fc_fn = (forward_check_with_propagation
                         if self.use_mac else forward_check)
                new_domains = fc_fn(task, value, domains, remaining)
                if new_domains is None:
                    # Domain wipe-out → thất bại sớm, thử giá trị khác
                    continue
            else:
                # Chỉ kiểm tra nhất quán với các task đã gán
                if not self._is_consistent(task, value, assigned):
                    continue
                new_domains = domains

            # ── Đệ quy ───────────────────────────────────────────────────────
            new_assigned = {**assigned, task["task_id"]: value}
            result = self._backtrack(new_assigned, new_domains, remaining)

            if result is not None:
                return result   # Tìm được lời giải → trả về ngay

            self.stats["backtracks"] += 1

        return None   # Tất cả giá trị đều thất bại → backtrack

    def _is_consistent(self,
                       task:     dict,
                       value:    Value,
                       assigned: dict[str, Value]) -> bool:
        """
        Kiểm tra value có nhất quán với tất cả task đã gán không.
        Chỉ dùng khi forward checking bị tắt.
        """
        for other_id, other_value in assigned.items():
            other_task = self.task_map[other_id]
            if not compatible(value, other_value, task, other_task):
                return False
        return True

    # ── Build output ──────────────────────────────────────────────────────────

    def _build_assignments(self, result: dict[str, Value]) -> list[Assignment]:
        """
        Chuyển dict {task_id → Value} thành list[Assignment] hoàn chỉnh.
        """
        assignments: list[Assignment] = []
        for task_id, value in result.items():
            task = self.task_map[task_id]
            assignments.append(Assignment(
                class_id = task["class_id"],
                subject  = self.parsed_data["subjects"][task["subject_id"]],
                teacher  = self.parsed_data["teachers"][value.teacher_id],
                room     = self.parsed_data["rooms"][value.room_id],
                session  = Session(day=value.day, period=value.period),
            ))
        return assignments

    def _record_time(self) -> None:
        self.stats["solve_time_sec"] = round(time.time() - self._start_time, 3)


# ────────────────────────────────────────────────────────────────────────────
# Internal exception
# ────────────────────────────────────────────────────────────────────────────

class _TimeoutError(Exception):
    """Dùng nội bộ để thoát đệ quy khi hết thời gian."""
    pass


# ────────────────────────────────────────────────────────────────────────────
# Preset configurations
# ────────────────────────────────────────────────────────────────────────────

def make_solver(tasks: list[dict],
                parsed_data: dict,
                preset: str = "balanced",
                **kwargs) -> CSPSolver:
    """
    Tạo CSPSolver với cấu hình preset sẵn.

    Presets:
      "fast"      – Tắt LCV và MAC, ưu tiên tốc độ
      "balanced"  – Mặc định: AC3 + FC + MRV + DEG + LCV
      "strong"    – Bật MAC (propagation mạnh hơn), phù hợp bài toán nhỏ
      "minimal"   – Chỉ backtracking thuần, không heuristic
    """
    presets = {
        "fast": dict(use_ac3=True,  use_fc=True,  use_mac=False,
                     use_mrv=True,  use_degree=True, use_lcv=False),
        "balanced": dict(use_ac3=True,  use_fc=True,  use_mac=False,
                         use_mrv=True,  use_degree=True, use_lcv=True),
        "strong": dict(use_ac3=True,  use_fc=True,  use_mac=True,
                       use_mrv=True,  use_degree=True, use_lcv=True),
        "minimal": dict(use_ac3=False, use_fc=False, use_mac=False,
                        use_mrv=False, use_degree=False, use_lcv=False),
    }
    if preset not in presets:
        raise ValueError(f"Preset không hợp lệ: '{preset}'. "
                         f"Chọn một trong: {list(presets)}")
    config = {**presets[preset], **kwargs}
    return CSPSolver(tasks=tasks, parsed_data=parsed_data, **config)
