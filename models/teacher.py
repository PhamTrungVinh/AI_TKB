class Teacher:
    def __init__(
        self,
        id: str,
        name: str,
        subjects=None,
        unavailable_slots=None
    ):
        self.id = id
        self.name = name

        # list[Subject]
        self.subjects = subjects or []

        # list[Slot]
        self.unavailable_slots = unavailable_slots or []

    def __repr__(self):
        return f"Teacher({self.id}, {self.name})"