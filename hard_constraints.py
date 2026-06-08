"""
hard_constraints.py
Ràng buộc cứng (Hard Constraints) — PHẢI thoả mãn 100%.
Mỗi hàm trả về True nếu ràng buộc được thoả mãn, False nếu vi phạm.

Tất cả hàm nhận vào:
    assignment  : Assignment hiện tại đang xét
    existing    : list[Assignment] đã được xếp trước đó
    data        : dict dữ liệu chuẩn hoá (từ Normalizer)
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.assignment import Assignment


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def _same_slot(a1: "Assignment", a2: "Assignment") -> bool:
    """Hai Assignment có cùng (day, period) không?"""
    return (a1.session.day == a2.session.day and
            a1.session.period == a2.session.period)


# ────────────────────────────────────────────────────────────────────────────
# HC-1: Không xung đột giáo viên
# ────────────────────────────────────────────────────────────────────────────

def teacher_no_conflict(assignment: "Assignment",
                        existing: list["Assignment"],
                        data: dict) -> bool:
    """
    HC-1: Một giáo viên không thể dạy hai lớp khác nhau
    cùng một tiết trong cùng một ngày.
    """
    for a in existing:
        if (a.teacher.id == assignment.teacher.id and
                _same_slot(a, assignment)):
            return False
    return True


# ────────────────────────────────────────────────────────────────────────────
# HC-2: Không xung đột phòng học
# ────────────────────────────────────────────────────────────────────────────

def room_no_conflict(assignment: "Assignment",
                     existing: list["Assignment"],
                     data: dict) -> bool:
    """
    HC-2: Một phòng học không thể được dùng bởi hai lớp khác nhau
    cùng một tiết trong cùng một ngày.
    """
    for a in existing:
        if (a.room.id == assignment.room.id and
                _same_slot(a, assignment)):
            return False
    return True


# ────────────────────────────────────────────────────────────────────────────
# HC-3: Không xung đột lớp học
# ────────────────────────────────────────────────────────────────────────────

def class_no_conflict(assignment: "Assignment",
                      existing: list["Assignment"],
                      data: dict) -> bool:
    """
    HC-3: Một lớp không thể học hai môn khác nhau
    cùng một tiết trong cùng một ngày.
    """
    for a in existing:
        if (a.class_id == assignment.class_id and
                _same_slot(a, assignment)):
            return False
    return True


# ────────────────────────────────────────────────────────────────────────────
# HC-4: Giáo viên phải rảnh tại slot được xếp
# ────────────────────────────────────────────────────────────────────────────

def teacher_available(assignment: "Assignment",
                      existing: list["Assignment"],
                      data: dict) -> bool:
    """
    HC-4: Giáo viên không được xếp vào tiết mà họ khai báo bận
    (unavailable_slots).
    """
    for unavail in assignment.teacher.unavailable_slots:
        if (unavail.day == assignment.session.day and
                unavail.period == assignment.session.period):
            return False
    return True


# ────────────────────────────────────────────────────────────────────────────
# HC-5: Sức chứa phòng học đủ cho lớp
# ────────────────────────────────────────────────────────────────────────────

def room_capacity_sufficient(assignment: "Assignment",
                             existing: list["Assignment"],
                             data: dict) -> bool:
    """
    HC-5: Sức chứa của phòng phải >= sĩ số lớp học.
    """
    class_info = data["classes"].get(assignment.class_id)
    if class_info is None:
        return False
    return assignment.room.capacity >= class_info["size"]


# ────────────────────────────────────────────────────────────────────────────
# HC-6: Giáo viên có thể dạy môn được phân công
# ────────────────────────────────────────────────────────────────────────────

def teacher_qualified(assignment: "Assignment",
                      existing: list["Assignment"],
                      data: dict) -> bool:
    """
    HC-6: Giáo viên phải có môn học này trong danh sách các môn họ dạy.
    """
    teacher_subject_ids = {s.id for s in assignment.teacher.subjects}
    return assignment.subject.id in teacher_subject_ids


# ────────────────────────────────────────────────────────────────────────────
# HC-7: Số tiết mỗi môn mỗi lớp không vượt quá quy định
# ────────────────────────────────────────────────────────────────────────────

def subject_periods_not_exceeded(assignment: "Assignment",
                                 existing: list["Assignment"],
                                 data: dict) -> bool:
    """
    HC-7: Số tiết của (lớp, môn) trong tuần không được vượt quá
    periods_per_week quy định.
    """
    count = sum(
        1 for a in existing
        if a.class_id == assignment.class_id
        and a.subject.id == assignment.subject.id
    )
    return count < assignment.subject.periods_per_week


# ────────────────────────────────────────────────────────────────────────────
# HC-8: Mỗi môn không được xếp quá 1 tiết/ngày cho một lớp
# ────────────────────────────────────────────────────────────────────────────

def no_duplicate_subject_per_day(assignment: "Assignment",
                                 existing: list["Assignment"],
                                 data: dict) -> bool:
    """
    HC-8: Một lớp không học cùng một môn hai lần trong cùng một ngày.
    """
    for a in existing:
        if (a.class_id == assignment.class_id and
                a.subject.id == assignment.subject.id and
                a.session.day == assignment.session.day):
            return False
    return True


# ────────────────────────────────────────────────────────────────────────────
# Gộp tất cả hard constraints
# ────────────────────────────────────────────────────────────────────────────

ALL_HARD_CONSTRAINTS = [
    teacher_no_conflict,
    room_no_conflict,
    class_no_conflict,
    teacher_available,
    room_capacity_sufficient,
    teacher_qualified,
    subject_periods_not_exceeded,
    no_duplicate_subject_per_day,
]


def check_all(assignment: "Assignment",
              existing: list["Assignment"],
              data: dict) -> tuple[bool, list[str]]:
    """
    Chạy toàn bộ hard constraints.

    Trả về:
        (True, [])             nếu tất cả thoả mãn
        (False, [tên vi phạm]) nếu có vi phạm
    """
    violated = []
    for fn in ALL_HARD_CONSTRAINTS:
        if not fn(assignment, existing, data):
            violated.append(fn.__name__)
    return (len(violated) == 0, violated)


def is_feasible(assignment: "Assignment",
                existing: list["Assignment"],
                data: dict) -> bool:
    """Trả về True nếu tất cả hard constraints thoả mãn."""
    return all(fn(assignment, existing, data) for fn in ALL_HARD_CONSTRAINTS)
