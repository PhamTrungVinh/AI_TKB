class Subject:
    def __init__(
        self,
        id: str,
        name: str,
        periods_per_week: int
    ):
        self.id = id
        self.name = name
        self.periods_per_week = periods_per_week

    def __repr__(self):
        return f"Subject({self.id}, {self.name})"