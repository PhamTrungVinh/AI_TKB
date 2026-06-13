"""
forward_checking.py
Sau mỗi lần gán giá trị cho một task, loại bỏ ngay các giá trị mâu thuẫn
khỏi domain của các task chưa gán (Forward Checking).

Lợi ích so với backtracking đơn thuần:
  - Phát hiện sớm thất bại (fail-early) trước khi đệ quy sâu hơn
  - Giảm đáng kể số lần backtrack

Cơ chế:
  Sau khi gán value v cho task Xi:
    Với mỗi task Xj chưa gán có ràng buộc với Xi:
      → Xoá khỏi domain(Xj) mọi giá trị w không tương thích với v
      → Nếu domain(Xj) rỗng → trả về None (domain wipe-out)
"""

from __future__ import annotations
import copy
from typing import TYPE_CHECKING

from csp.heuristics import are_constrained, compatible

if TYPE_CHECKING:
    from csp.ac3 import Value


def forward_check(task: dict,
                  value: "Value",
                  domains: dict[str, list["Value"]],
                  unassigned: list[dict]) -> dict[str, list["Value"]] | None:
    """
    Áp dụng forward checking sau khi gán `value` cho `task`.

    Parameters
    ----------
    task       : task vừa được gán
    value      : giá trị vừa gán cho task
    domains    : domain hiện tại của tất cả task chưa gán
    unassigned : list task chưa gán (không bao gồm `task`)

    Returns
    -------
    dict domains đã cắt tỉa nếu không có domain nào rỗng,
    None nếu có domain bị rỗng (thất bại sớm).
    """
    # Chỉ copy những domain cần thay đổi (lazy copy)
    new_domains: dict[str, list["Value"]] = {}
    modified: set[str] = set()

    for other in unassigned:
        if not are_constrained(task, other):
            continue

        other_id = other["task_id"]
        current  = domains[other_id]

        # Lọc: giữ lại các giá trị tương thích với value
        pruned = [w for w in current if compatible(value, w, task, other)]

        if not pruned:
            return None          # Domain wipe-out → thất bại sớm

        if len(pruned) < len(current):
            new_domains[other_id] = pruned
            modified.add(other_id)

    if not modified:
        # Không có gì thay đổi → trả về dict gốc (không copy)
        return domains

    # Trả về dict mới: domains đã sửa ghi đè lên domains gốc
    result = dict(domains)   # shallow copy của dict (chỉ copy tham chiếu)
    result.update(new_domains)
    return result


def forward_check_with_propagation(task: dict,
                                   value: "Value",
                                   domains: dict[str, list["Value"]],
                                   unassigned: list[dict]) -> dict[str, list["Value"]] | None:
    """
    Forward checking mở rộng: sau khi cắt tỉa, nếu domain của Xj bị thu nhỏ
    về đúng 1 giá trị (singleton), lan truyền tiếp sang hàng xóm của Xj
    (tương tự MAC – Maintaining Arc Consistency).

    Phiên bản mạnh hơn forward_check() nhưng tốn kém hơn mỗi bước.
    Dùng khi bài toán nhỏ hoặc trung bình.
    """
    unassigned_map = {t["task_id"]: t for t in unassigned}

    # Bước 1: Forward check cơ bản
    result = forward_check(task, value, domains, unassigned)
    if result is None:
        return None

    result = dict(result)   # đảm bảo có thể sửa

    # Bước 2: Lan truyền singleton (MAC-lite)
    # Queue các task vừa bị thu nhỏ domain về 1 giá trị
    singleton_queue = [
        other_id for other_id in unassigned_map
        if other_id in result and len(result[other_id]) == 1
        and other_id != task["task_id"]
    ]

    visited: set[str] = set()

    while singleton_queue:
        xi_id = singleton_queue.pop()
        if xi_id in visited:
            continue
        visited.add(xi_id)

        xi_task  = unassigned_map.get(xi_id)
        if xi_task is None:
            continue

        singleton_value = result[xi_id][0]

        # Lan truyền sang hàng xóm của xi
        for other in unassigned:
            other_id = other["task_id"]
            if other_id == xi_id or other_id not in result:
                continue
            if not are_constrained(xi_task, other):
                continue

            pruned = [w for w in result[other_id]
                      if compatible(singleton_value, w, xi_task, other)]
            if not pruned:
                return None    # Wipe-out

            if len(pruned) < len(result[other_id]):
                result[other_id] = pruned
                if len(pruned) == 1 and other_id not in visited:
                    singleton_queue.append(other_id)

    return result
