class Slot:
    def __init__(self, day: str, period: int):
        self.day = day
        self.period = period

    def __repr__(self):
        return f"{self.day}-{self.period}"