from parser.excel_parser import load_excel
from parser.validator import validate
from parser.normalizer import normalize
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
CSP_DIR = os.path.join(PROJECT_ROOT, "csp")

if CSP_DIR not in sys.path:
    sys.path.append(CSP_DIR)
from csp.backtracking import make_solver

from output.export_excel import export_schedule
from output.statistics import print_statistics


def build_assignment_tasks(data):
    tasks = []

    for class_id, subjects in data["class_subjects"].items():
        class_size = data["classes"][class_id]["size"]

        for subject in subjects:
            candidate_teacher_ids = [
                teacher.id
                for teacher in data["teachers"].values()
                if subject.id in [s.id for s in teacher.subjects]
            ]

            candidate_room_ids = [
                room.id
                for room in data["rooms"].values()
                if room.capacity >= class_size
            ]

            for i in range(subject.periods_per_week):
                tasks.append({
                    "task_id": f"{class_id}_{subject.id}_{i + 1}",
                    "class_id": class_id,
                    "subject_id": subject.id,
                    "candidate_teacher_ids": candidate_teacher_ids,
                    "candidate_room_ids": candidate_room_ids,
                })

    return tasks


def main():
    raw_data = load_excel("data/input.xlsx")
    validate(raw_data)

    data = normalize(raw_data)
    tasks = build_assignment_tasks(data)

    print("Số task cần xếp:", len(tasks))

    solver = make_solver(
        tasks=tasks,
        parsed_data=data,
        preset="balanced",
        time_limit=300
    )

    assignments = solver.solve()

    if assignments is None:
        print("Không tìm được thời khóa biểu hợp lệ.")
        solver.print_stats()
        return

    solver.print_stats()
    print_statistics(assignments, data)
    export_schedule(assignments, "output/timetable.xlsx")


if __name__ == "__main__":
    main()