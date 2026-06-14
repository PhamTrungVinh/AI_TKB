class Assignment:
    def __init__(
        self,
        class_id: str,
        subject,
        teacher,
        room,
        session
    ):
        self.class_id = class_id

        self.subject = subject
        self.teacher = teacher
        self.room = room
        self.session = session

    def __repr__(self):
        return (
            f"{self.class_id} | "
            f"{self.subject.id} | "
            f"{self.teacher.id} | "
            f"{self.room.id} | "
            f"{self.session.day}-{self.session.period}"
        )