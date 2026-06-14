class ClassRoom:
    def __init__(self, id: str, name: str, size: int, grade: int | None = None):
        self.id = id
        self.name = name
        self.size = size
        self.grade = grade

    def __repr__(self):
        return f"ClassRoom({self.id}, {self.name}, size={self.size})"