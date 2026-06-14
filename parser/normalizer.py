from models.teacher import Teacher
from models.room import Room
from models.subject import Subject
from models.slot import Slot
from models.class_room import ClassRoom


def normalize(raw_data: dict) -> dict:
    teachers = {}
    rooms = {}
    subjects = {}
    classes = {}
    class_subjects = {}

    for _, row in raw_data["subjects"].iterrows():
        subject = Subject(
            id=str(row["id"]),
            name=str(row["name"]),
            periods_per_week=int(row["periods_per_week"])
        )
        subjects[subject.id] = subject

    for _, row in raw_data["teachers"].iterrows():
        teacher = Teacher(
            id=str(row["id"]),
            name=str(row["name"]),
            subjects=[],
            unavailable_slots=[]
        )
        teachers[teacher.id] = teacher

    for _, row in raw_data["rooms"].iterrows():
        room = Room(
            id=str(row["id"]),
            capacity=int(row["capacity"])
        )
        rooms[room.id] = room

    for _, row in raw_data["classes"].iterrows():
        class_obj = ClassRoom(
            id=str(row["id"]),
            name=str(row["name"]),
            size=int(row["size"]),
            grade=int(row["grade"])
        )

        classes[class_obj.id] = {
            "id": class_obj.id,
            "name": class_obj.name,
            "size": class_obj.size,
            "grade": class_obj.grade,
            "object": class_obj
        }

    for _, row in raw_data["teacher_subjects"].iterrows():
        teacher_id = str(row["teacher_id"])
        subject_id = str(row["subject_id"])

        if teacher_id in teachers and subject_id in subjects:
            teachers[teacher_id].subjects.append(subjects[subject_id])

    for _, row in raw_data["class_subjects"].iterrows():
        class_id = str(row["class_id"])
        subject_id = str(row["subject_id"])

        if class_id not in class_subjects:
            class_subjects[class_id] = []

        if subject_id in subjects:
            class_subjects[class_id].append(subjects[subject_id])

    for _, row in raw_data["teacher_unavailable"].iterrows():
        teacher_id = str(row["teacher_id"])

        if teacher_id in teachers:
            teachers[teacher_id].unavailable_slots.append(
                Slot(
                    day=str(row["day"]),
                    period=int(row["period"])
                )
            )

    return {
        "teachers": teachers,
        "rooms": rooms,
        "subjects": subjects,
        "classes": classes,
        "class_subjects": class_subjects
    }