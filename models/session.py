class Session:
    def __init__(
        self,
        day: str,
        period: int,
        id: str | None = None
    ):
        self.id = id
        self.day = day
        self.period = period

    def __repr__(self):
        return f"Session({self.day}-{self.period})"