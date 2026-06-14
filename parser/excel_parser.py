import pandas as pd


def load_excel(path: str) -> dict:
    return {
        "teachers": pd.read_excel(path, sheet_name="Teachers"),
        "rooms": pd.read_excel(path, sheet_name="Rooms"),
        "subjects": pd.read_excel(path, sheet_name="Subjects"),
        "classes": pd.read_excel(path, sheet_name="Classes"),
        "teacher_subjects": pd.read_excel(path, sheet_name="TeacherSubjects"),
        "class_subjects": pd.read_excel(path, sheet_name="ClassSubjects"),
        "teacher_unavailable": pd.read_excel(path, sheet_name="TeacherUnavailable"),
    }