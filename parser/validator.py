REQUIRED_COLUMNS = {
    "teachers": ["id", "name"],
    "rooms": ["id", "capacity"],
    "subjects": ["id", "name", "periods_per_week"],
    "classes": ["id", "name", "size", "grade"],
    "teacher_subjects": ["teacher_id", "subject_id"],
    "class_subjects": ["class_id", "subject_id"],
    "teacher_unavailable": ["teacher_id", "day", "period"],
}


def validate(raw_data: dict) -> None:
    for sheet_name, columns in REQUIRED_COLUMNS.items():
        if sheet_name not in raw_data:
            raise ValueError(f"Missing sheet: {sheet_name}")

        df = raw_data[sheet_name]

        for col in columns:
            if col not in df.columns:
                raise ValueError(f"Missing column '{col}' in sheet '{sheet_name}'")

    if raw_data["rooms"]["capacity"].isnull().any():
        raise ValueError("Room capacity cannot be empty")

    if raw_data["classes"]["size"].isnull().any():
        raise ValueError("Class size cannot be empty")

    if raw_data["subjects"]["periods_per_week"].isnull().any():
        raise ValueError("Subject periods_per_week cannot be empty")