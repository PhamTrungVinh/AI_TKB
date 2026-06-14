from constraints.soft_constraints import compute_penalty_breakdown


def print_statistics(assignments, data):
    print("\n===== THỐNG KÊ KẾT QUẢ =====")
    print("Tổng số tiết đã xếp:", len(assignments))

    by_class = {}
    by_teacher = {}

    for a in assignments:
        by_class[a.class_id] = by_class.get(a.class_id, 0) + 1
        by_teacher[a.teacher.name] = by_teacher.get(a.teacher.name, 0) + 1

    print("\nSố tiết theo lớp:")
    for class_id, count in by_class.items():
        print(f"- {class_id}: {count} tiết")

    print("\nSố tiết theo giáo viên:")
    for teacher_name, count in by_teacher.items():
        print(f"- {teacher_name}: {count} tiết")

    print("\nPenalty ràng buộc mềm:")
    breakdown = compute_penalty_breakdown(assignments, data)

    for name, info in breakdown.items():
        if name != "_total":
            print(f"- {name}: raw={info['raw']}, weight={info['weight']}, weighted={info['weighted']}")

    print("Tổng penalty:", breakdown["_total"])