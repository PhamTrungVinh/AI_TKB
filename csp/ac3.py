"""
ac3.py
Kiểu Value, khởi tạo domain ban đầu và thuật toán AC-3.

AC-3 (Arc Consistency 3) loại bỏ các giá trị "chắc chắn thất bại"
khỏi domain trước khi bắt đầu backtracking, giúp:
  - Thu hẹp không gian tìm kiếm đáng kể
  - Phát hiện sớm bài toán bất khả thi

Độ phức tạp: O(e × d³)  với e = số cung, d = kích thước domain lớn nhất
"""

from __future__ import annotations
import copy
from typing import NamedTuple
from collections import deque

from csp.heuristics import are_constrained, compatible


# ────────────────────────────────────────────────────────────────────────────
# Kiểu dữ liệu Value
# ────────────────────────────────────────────────────────────────────────────

class Value(NamedTuple):
    """
    Một giá trị đầy đủ cho một task xếp lịch.
    Bất biến (hashable) để dùng làm key hoặc element của set.
    """
    teacher_id: str   # giáo viên được phân công
    room_id: str      # phòng học
    day: str          # ngày trong tuần (vd: "Mon")
    period: int       # tiết học (vd: 3)


# ────────────────────────────────────────────────────────────────────────────
# Khởi tạo domain
# ────────────────────────────────────────────────────────────────────────────

DEFAULT_DAYS    = ["Mon", "Tue", "Wed", "Thu", "Fri"]
DEFAULT_PERIODS = list(range(1, 11))   # tiết 1 → 10


def build_initial_domains(tasks: list[dict],
                           parsed_data: dict,
                           days: list[str] | None = None,
                           periods: list[int] | None = None) -> dict[str, list[Value]]:
    """
    Khởi tạo domain cho từng task.

    Domain của một task = tất cả Value(teacher, room, day, period) thoả:
      - teacher ∈ candidate_teacher_ids của task
      - room    ∈ candidate_room_ids của task
      - (day, period) không nằm trong unavailable_slots của teacher  → HC-4

    Các HC còn lại (xung đột giáo viên/phòng/lớp) được xử lý
    bởi AC-3 và Forward Checking.
    """
    days    = days    or DEFAULT_DAYS
    periods = periods or DEFAULT_PERIODS
    all_slots = [(d, p) for d in days for p in periods]

    # Pre-build unavailable slot set per teacher  (tránh lookup lặp)
    teacher_unavail: dict[str, frozenset[tuple[str, int]]] = {
        tid: frozenset((s.day, s.period) for s in teacher.unavailable_slots)
        for tid, teacher in parsed_data["teachers"].items()
    }

    domains: dict[str, list[Value]] = {}
    for task in tasks:
        domain: list[Value] = []
        for t_id in task["candidate_teacher_ids"]:
            unavail = teacher_unavail.get(t_id, frozenset())
            for r_id in task["candidate_room_ids"]:
                for day, period in all_slots:
                    if (day, period) not in unavail:
                        domain.append(Value(
                            teacher_id=t_id,
                            room_id=r_id,
                            day=day,
                            period=period,
                        ))
        domains[task["task_id"]] = domain

    return domains


# ────────────────────────────────────────────────────────────────────────────
# AC-3 internals
# ────────────────────────────────────────────────────────────────────────────

def _build_neighbor_map(tasks: list[dict]) -> dict[str, list[str]]:
    """
    Xây dựng map: task_id → [task_id của các task có ràng buộc].
    Dùng để tái-thêm cung khi domain thu hẹp.
    """
    neighbors: dict[str, list[str]] = {t["task_id"]: [] for t in tasks}
    for i, ti in enumerate(tasks):
        for j, tj in enumerate(tasks):
            if i != j and are_constrained(ti, tj):
                neighbors[ti["task_id"]].append(tj["task_id"])
    return neighbors


def _revise(domains: dict[str, list[Value]],
            task_i: dict,
            task_j: dict) -> bool:
    """
    Loại bỏ các giá trị trong domain[task_i] không có "support" trong domain[task_j].
    Một giá trị v có support khi tồn tại ít nhất một w trong domain[task_j]
    tương thích với v.

    Trả về True nếu domain[task_i] bị thu hẹp.
    """
    domain_j = domains[task_j["task_id"]]

    # Tách slot của task_j thành set để tra cứu O(1)
    # Nếu v và w khác slot → luôn compatible → v có support ngay lập tức
    slots_j: set[tuple[str, int]] = {(w.day, w.period) for w in domain_j}

    # Với mỗi slot có trong domain_j, tổ hợp (teacher, room) nào tồn tại?
    # Dùng để kiểm tra conflict khi cùng slot
    slot_teacher_j: dict[tuple[str, int], set[str]] = {}
    slot_room_j:    dict[tuple[str, int], set[str]] = {}
    for w in domain_j:
        key = (w.day, w.period)
        slot_teacher_j.setdefault(key, set()).add(w.teacher_id)
        slot_room_j.setdefault(key, set()).add(w.room_id)

    same_class = (task_i["class_id"] == task_j["class_id"])

    revised = False
    new_domain: list[Value] = []

    for v in domains[task_i["task_id"]]:
        slot_v = (v.day, v.period)

        if slot_v not in slots_j:
            # domain_j không có slot này → v có support (khác slot → compatible)
            new_domain.append(v)
            continue

        if same_class:
            # Cùng lớp + cùng slot → xung đột với MỌI w có slot đó → không có support
            # Nhưng nếu domain_j còn slot khác → v vẫn có support qua slot khác
            # Kiểm tra: có slot nào khác trong domain_j không?
            has_other_slot = any(s != slot_v for s in slots_j)
            if has_other_slot:
                new_domain.append(v)
                continue
            # domain_j chỉ có đúng 1 slot và trùng với v → v không có support
            revised = True
            continue

        # Khác lớp: tìm w trong domain_j cùng slot nhưng khác teacher VÀ khác room
        teachers_at_slot = slot_teacher_j.get(slot_v, set())
        rooms_at_slot    = slot_room_j.get(slot_v, set())

        # Support nếu: tồn tại teacher ≠ v.teacher_id HOẶC room ≠ v.room_id tại slot đó
        # (vì nếu teacher khác → compatible; nếu room khác nhưng teacher giống → cần check)
        # Chính xác: cần tìm w tại slot_v với teacher ≠ v.teacher_id AND room ≠ v.room_id
        has_support = any(
            (w.teacher_id != v.teacher_id and w.room_id != v.room_id)
            for w in domain_j
            if w.day == v.day and w.period == v.period
        )
        # Hoặc domain_j có slot khác slot_v
        if not has_support:
            has_support = any(s != slot_v for s in slots_j)

        if has_support:
            new_domain.append(v)
        else:
            revised = True

    domains[task_i["task_id"]] = new_domain
    return revised


# ────────────────────────────────────────────────────────────────────────────
# AC-3 entry point
# ────────────────────────────────────────────────────────────────────────────

def run_ac3(domains: dict[str, list[Value]],
            tasks: list[dict]) -> tuple[bool, dict[str, list[Value]]]:
    """
    Chạy thuật toán AC-3 trên tập domains hiện tại.

    Trả về:
        (True,  pruned_domains) nếu còn khả năng giải
        (False, domains)        nếu có domain rỗng → bất khả thi
    """
    task_map      = {t["task_id"]: t for t in tasks}
    neighbor_map  = _build_neighbor_map(tasks)
    working       = copy.deepcopy(domains)

    # Khởi tạo queue với tất cả cung có ràng buộc
    queue: deque[tuple[str, str]] = deque()
    for ti in tasks:
        for xj_id in neighbor_map[ti["task_id"]]:
            queue.append((ti["task_id"], xj_id))

    while queue:
        xi_id, xj_id = queue.popleft()
        task_i = task_map[xi_id]
        task_j = task_map[xj_id]

        if _revise(working, task_i, task_j):
            if not working[xi_id]:
                # Domain rỗng → không thể giải
                return False, working

            # domain[xi] thu hẹp → các hàng xóm của xi (trừ xj) cần kiểm tra lại
            for xk_id in neighbor_map[xi_id]:
                if xk_id != xj_id:
                    queue.append((xk_id, xi_id))

    return True, working
