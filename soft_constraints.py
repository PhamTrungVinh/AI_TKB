"""
soft_constraints.py
Ràng buộc mềm (Soft Constraints) — tối ưu hoá, vi phạm tính vào penalty score.

Mỗi hàm trả về penalty (số nguyên >= 0):
    0   = thoả mãn hoàn toàn
    > 0 = mức độ vi phạm (penalty càng cao càng tệ)

Score tổng hợp = Σ(weight × penalty) (càng thấp càng tốt).
"""

from __future__ import annotations
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.assignment import Assignment


# ────────────────────────────────────────────────────────────────────────────
# Cấu hình weight (có thể điều chỉnh từ main.py)
# ────────────────────────────────────────────────────────────────────────────

DEFAULT_WEIGHTS: dict[str, int] = {
    "teacher_idle_gap":           3,   # Giáo viên có tiết trống giữa các buổi dạy
    "avoid_last_period":          2,   # Môn khó xếp vào tiết cuối
    "uneven_distribution":        2,   # Môn học phân bố không đều trong tuần
    "teacher_overload_per_day":   4,   # Giáo viên dạy quá nhiều tiết liên tiếp
    "class_overload_per_day":     3,   # Lớp học quá nhiều tiết trong ngày
    "teacher_consecutive":        1,   # Giáo viên có >= N tiết liên tiếp
    "preferred_morning_subjects": 1,   # Môn khó không được ưu tiên buổi sáng
}

# Môn học "khó" hoặc cần tập trung cao (id) — cấu hình theo trường
HEAVY_SUBJECT_IDS: set[str] = {"MATH", "PHYSICS", "CHEMISTRY", "LITERATURE"}

# Tiết được coi là "cuối buổi" (nên tránh môn khó)
LATE_PERIODS: set[int] = {8, 9, 10}

# Tiết buổi sáng (ưu tiên môn khó)
MORNING_PERIODS: set[int] = {1, 2, 3, 4, 5}

# Ngưỡng số tiết liên tiếp tối đa của giáo viên
MAX_CONSECUTIVE_TEACHER = 3

# Ngưỡng số tiết/ngày tối đa cho một lớp
MAX_PERIODS_CLASS_PER_DAY = 8

# Ngưỡng số tiết/ngày tối đa cho một giáo viên
MAX_PERIODS_TEACHER_PER_DAY = 6


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def _group_by(assignments: list["Assignment"], key_fn) -> dict:
    groups: dict = defaultdict(list)
    for a in assignments:
        groups[key_fn(a)].append(a)
    return groups


def _periods_on_day(assignments: list["Assignment"],
                    entity_id: str,
                    id_fn,
                    day: str) -> list[int]:
    """Lấy danh sách tiết của teacher/class trong một ngày."""
    return sorted([
        a.session.period for a in assignments
        if id_fn(a) == entity_id and a.session.day == day
    ])


def _count_gaps(periods: list[int]) -> int:
    """
    Đếm số tiết trống giữa các tiết dạy.
    Ví dụ: [1, 3, 5] → gaps = (3-1-1) + (5-3-1) = 2
    """
    if len(periods) < 2:
        return 0
    return sum(periods[i + 1] - periods[i] - 1 for i in range(len(periods) - 1))


def _count_consecutive_runs(periods: list[int], max_run: int) -> int:
    """
    Đếm số lần giáo viên dạy >= max_run tiết liên tiếp không nghỉ.
    """
    if not periods:
        return 0
    run, violations = 1, 0
    for i in range(1, len(periods)):
        if periods[i] == periods[i - 1] + 1:
            run += 1
            if run > max_run:
                violations += 1
        else:
            run = 1
    return violations


DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


# ────────────────────────────────────────────────────────────────────────────
# SC-1: Giáo viên không có tiết trống giữa buổi dạy
# ────────────────────────────────────────────────────────────────────────────

def teacher_idle_gap(assignments: list["Assignment"], data: dict) -> int:
    """
    SC-1: Phạt mỗi tiết trống xen giữa hai tiết dạy của giáo viên.
    Ví dụ dạy tiết 1, 4 → 2 tiết trống (tiết 2, 3).
    """
    total_penalty = 0
    by_teacher = _group_by(assignments, lambda a: a.teacher.id)
    for tid, tass in by_teacher.items():
        for day in DAYS:
            periods = _periods_on_day(tass, tid, lambda a: a.teacher.id, day)
            total_penalty += _count_gaps(periods)
    return total_penalty


# ────────────────────────────────────────────────────────────────────────────
# SC-2: Tránh xếp môn khó vào tiết cuối
# ────────────────────────────────────────────────────────────────────────────

def avoid_last_period(assignments: list["Assignment"], data: dict) -> int:
    """
    SC-2: Phạt khi môn khó được xếp vào các tiết cuối buổi.
    """
    return sum(
        1 for a in assignments
        if a.subject.id in HEAVY_SUBJECT_IDS
        and a.session.period in LATE_PERIODS
    )


# ────────────────────────────────────────────────────────────────────────────
# SC-3: Phân bố môn học đều trong tuần
# ────────────────────────────────────────────────────────────────────────────

def uneven_distribution(assignments: list["Assignment"], data: dict) -> int:
    """
    SC-3: Phạt khi các tiết của cùng một môn/lớp bị dồn vào ít ngày.
    Lý tưởng: mỗi ngày học tối đa 1 tiết mỗi môn (hoặc phân đều).
    Penalty = số tiết vượt quá 1 tiết/ngày cho mỗi (lớp, môn).
    """
    total_penalty = 0
    # {(class_id, subject_id, day): count}
    counter: dict = defaultdict(int)
    for a in assignments:
        counter[(a.class_id, a.subject.id, a.session.day)] += 1
    for count in counter.values():
        if count > 1:
            total_penalty += (count - 1)
    return total_penalty


# ────────────────────────────────────────────────────────────────────────────
# SC-4: Giáo viên không dạy quá nhiều tiết liên tiếp
# ────────────────────────────────────────────────────────────────────────────

def teacher_consecutive(assignments: list["Assignment"], data: dict) -> int:
    """
    SC-4: Phạt khi giáo viên dạy >= MAX_CONSECUTIVE_TEACHER tiết liên tiếp.
    """
    total_penalty = 0
    by_teacher = _group_by(assignments, lambda a: a.teacher.id)
    for tid, tass in by_teacher.items():
        for day in DAYS:
            periods = _periods_on_day(tass, tid, lambda a: a.teacher.id, day)
            total_penalty += _count_consecutive_runs(periods, MAX_CONSECUTIVE_TEACHER)
    return total_penalty


# ────────────────────────────────────────────────────────────────────────────
# SC-5: Giáo viên không dạy quá nhiều tiết mỗi ngày
# ────────────────────────────────────────────────────────────────────────────

def teacher_overload_per_day(assignments: list["Assignment"], data: dict) -> int:
    """
    SC-5: Phạt khi giáo viên dạy > MAX_PERIODS_TEACHER_PER_DAY tiết trong ngày.
    """
    total_penalty = 0
    by_teacher = _group_by(assignments, lambda a: a.teacher.id)
    for tid, tass in by_teacher.items():
        for day in DAYS:
            count = sum(1 for a in tass if a.session.day == day)
            if count > MAX_PERIODS_TEACHER_PER_DAY:
                total_penalty += (count - MAX_PERIODS_TEACHER_PER_DAY)
    return total_penalty


# ────────────────────────────────────────────────────────────────────────────
# SC-6: Lớp học không học quá nhiều tiết mỗi ngày
# ────────────────────────────────────────────────────────────────────────────

def class_overload_per_day(assignments: list["Assignment"], data: dict) -> int:
    """
    SC-6: Phạt khi lớp học có > MAX_PERIODS_CLASS_PER_DAY tiết trong ngày.
    """
    total_penalty = 0
    by_class = _group_by(assignments, lambda a: a.class_id)
    for cid, cass in by_class.items():
        for day in DAYS:
            count = sum(1 for a in cass if a.session.day == day)
            if count > MAX_PERIODS_CLASS_PER_DAY:
                total_penalty += (count - MAX_PERIODS_CLASS_PER_DAY)
    return total_penalty


# ────────────────────────────────────────────────────────────────────────────
# SC-7: Ưu tiên môn khó vào buổi sáng
# ────────────────────────────────────────────────────────────────────────────

def preferred_morning_subjects(assignments: list["Assignment"], data: dict) -> int:
    """
    SC-7: Phạt khi môn khó KHÔNG được xếp vào buổi sáng.
    Khuyến khích xếp các môn cần tập trung vào tiết đầu ngày.
    """
    return sum(
        1 for a in assignments
        if a.subject.id in HEAVY_SUBJECT_IDS
        and a.session.period not in MORNING_PERIODS
    )


# ────────────────────────────────────────────────────────────────────────────
# Gộp tất cả soft constraints
# ────────────────────────────────────────────────────────────────────────────

ALL_SOFT_CONSTRAINTS: dict[str, callable] = {
    "teacher_idle_gap":           teacher_idle_gap,
    "avoid_last_period":          avoid_last_period,
    "uneven_distribution":        uneven_distribution,
    "teacher_consecutive":        teacher_consecutive,
    "teacher_overload_per_day":   teacher_overload_per_day,
    "class_overload_per_day":     class_overload_per_day,
    "preferred_morning_subjects": preferred_morning_subjects,
}


def compute_total_penalty(assignments: list["Assignment"],
                          data: dict,
                          weights: dict[str, int] | None = None) -> int:
    """
    Tính tổng penalty của một tập assignments.
    Trả về score (càng thấp càng tốt).
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS
    total = 0
    for name, fn in ALL_SOFT_CONSTRAINTS.items():
        w = weights.get(name, 1)
        p = fn(assignments, data)
        total += w * p
    return total


def compute_penalty_breakdown(assignments: list["Assignment"],
                               data: dict,
                               weights: dict[str, int] | None = None) -> dict[str, dict]:
    """
    Trả về breakdown penalty theo từng ràng buộc.
    Hữu ích để debug và phân tích kết quả.

    Trả về:
    {
        "teacher_idle_gap": {"raw": 5, "weight": 3, "weighted": 15},
        ...
        "_total": 42
    }
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS
    breakdown = {}
    total = 0
    for name, fn in ALL_SOFT_CONSTRAINTS.items():
        w = weights.get(name, 1)
        raw = fn(assignments, data)
        weighted = w * raw
        total += weighted
        breakdown[name] = {"raw": raw, "weight": w, "weighted": weighted}
    breakdown["_total"] = total
    return breakdown
