"""
heuristics.py
Chiến lược chọn biến và sắp xếp giá trị cho backtracking CSP.

Cũng chứa các utility dùng chung (are_constrained, compatible)
được import bởi ac3.py và forward_checking.py.

Heuristics được dùng:
  MRV   – Minimum Remaining Values   : ưu tiên biến có domain nhỏ nhất
  DEG   – Degree tiebreak            : tie-break bằng số ràng buộc
  LCV   – Least Constraining Value   : thử giá trị "ít huỷ diệt" nhất trước
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csp.ac3 import Value


# ────────────────────────────────────────────────────────────────────────────
# Utilities dùng chung (AC-3, Forward Checking, Backtracking)
# ────────────────────────────────────────────────────────────────────────────

def are_constrained(task_i: dict, task_j: dict) -> bool:
    """
    Hai task có ràng buộc với nhau không?
    Có ràng buộc khi chúng chia sẻ: cùng lớp, giáo viên chung, hoặc phòng chung.
    """
    if task_i["task_id"] == task_j["task_id"]:
        return False
    if task_i["class_id"] == task_j["class_id"]:
        return True  # cùng lớp → không thể học cùng tiết (HC-3)
    if set(task_i["candidate_teacher_ids"]) & set(task_j["candidate_teacher_ids"]):
        return True  # giáo viên chung → có thể xung đột (HC-1)
    if set(task_i["candidate_room_ids"]) & set(task_j["candidate_room_ids"]):
        return True  # phòng chung → có thể xung đột (HC-2)
    return False


def compatible(v: "Value", w: "Value", task_i: dict, task_j: dict) -> bool:
    """
    Hai giá trị v (cho task_i) và w (cho task_j) có tương thích không?

    Tương thích = không vi phạm hard constraint nào:
      HC-1: giáo viên không dạy 2 lớp cùng tiết
      HC-2: phòng không bị dùng 2 lớp cùng tiết
      HC-3: lớp không học 2 môn cùng tiết
    """
    # Khác slot → luôn OK, không cần xét thêm
    if v.day != w.day or v.period != w.period:
        return True

    # Cùng slot → kiểm tra từng loại xung đột
    if task_i["class_id"] == task_j["class_id"]:
        return False   # HC-3
    if v.teacher_id == w.teacher_id:
        return False   # HC-1
    if v.room_id == w.room_id:
        return False   # HC-2
    return True


# ────────────────────────────────────────────────────────────────────────────
# Variable selection
# ────────────────────────────────────────────────────────────────────────────

def _mrv_key(task: dict, domains: dict[str, list]) -> int:
    """Số giá trị còn lại trong domain của task."""
    return len(domains[task["task_id"]])


def _degree_key(task: dict, unassigned: list[dict]) -> int:
    """
    Số task chưa gán có ràng buộc với task này.
    Dùng làm tiebreaker cho MRV (degree cao → ưu tiên chọn trước).
    """
    return sum(
        1 for t in unassigned
        if t["task_id"] != task["task_id"] and are_constrained(task, t)
    )


def select_variable(unassigned: list[dict],
                    domains: dict[str, list],
                    use_mrv: bool = True,
                    use_degree: bool = True) -> dict:
    """
    Chọn task tiếp theo để gán giá trị.

    Chiến lược:
      - MRV   : chọn task có domain nhỏ nhất (phát hiện sớm bất khả thi)
      - DEG   : dùng làm tiebreaker khi MRV bằng nhau (âm → muốn MAX)
      - Fallback: lấy phần tử đầu tiên nếu không dùng heuristic
    """
    if not use_mrv:
        return unassigned[0]

    if use_degree:
        return min(
            unassigned,
            key=lambda t: (_mrv_key(t, domains), -_degree_key(t, unassigned))
        )
    return min(unassigned, key=lambda t: _mrv_key(t, domains))


# ────────────────────────────────────────────────────────────────────────────
# Value ordering (LCV)
# ────────────────────────────────────────────────────────────────────────────

# Ngưỡng domain: nếu domain lớn hơn, bỏ qua LCV để tránh chậm
_LCV_DOMAIN_THRESHOLD = 80


def _lcv_score(value: "Value",
               task: dict,
               domains: dict[str, list],
               unassigned: list[dict]) -> int:
    """
    Đếm tổng số giá trị bị loại khỏi các domain hàng xóm nếu chọn value.
    Score thấp hơn → ít "huỷ diệt" → ưu tiên chọn.
    """
    eliminated = 0
    for other in unassigned:
        if other["task_id"] == task["task_id"]:
            continue
        if not are_constrained(task, other):
            continue
        for w in domains[other["task_id"]]:
            if not compatible(value, w, task, other):
                eliminated += 1
    return eliminated


def order_domain_values(task: dict,
                        domains: dict[str, list],
                        unassigned: list[dict],
                        use_lcv: bool = True) -> list:
    """
    Sắp xếp giá trị trong domain theo LCV (ít loại bỏ nhất → thử trước).

    LCV bị bỏ qua khi domain quá lớn (> _LCV_DOMAIN_THRESHOLD) để tránh
    chi phí O(|domain| × |neighbors| × |neighbor_domain|) không cần thiết.
    """
    values = list(domains[task["task_id"]])
    if not use_lcv or len(values) <= 1 or len(values) > _LCV_DOMAIN_THRESHOLD:
        return values
    return sorted(values, key=lambda v: _lcv_score(v, task, domains, unassigned))
