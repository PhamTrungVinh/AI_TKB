import os
import pandas as pd

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
PERIODS = list(range(1, 11))


def _cell_text(a):
    return f"{a.subject.name}\nGV: {a.teacher.name}\nPhòng: {a.room.id}"


def export_schedule(assignments, output_path="output/timetable.xlsx"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    raw_rows = []
    for a in assignments:
        raw_rows.append({
            "Lớp": a.class_id,
            "Mã môn": a.subject.id,
            "Môn": a.subject.name,
            "Mã GV": a.teacher.id,
            "Giáo viên": a.teacher.name,
            "Phòng": a.room.id,
            "Thứ": a.session.day,
            "Tiết": a.session.period,
        })

    raw_df = pd.DataFrame(raw_rows)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        raw_df.to_excel(writer, sheet_name="All_Assignments", index=False)

        for class_id in sorted(raw_df["Lớp"].unique()):
            table = pd.DataFrame(index=PERIODS, columns=DAYS)
            table.index.name = "Tiết"

            class_assignments = [a for a in assignments if a.class_id == class_id]

            for a in class_assignments:
                table.loc[a.session.period, a.session.day] = _cell_text(a)

            table.to_excel(writer, sheet_name=str(class_id))

    print(f"Đã xuất thời khóa biểu: {output_path}")