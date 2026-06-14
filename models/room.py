class Room:
    def __init__(
        self,
        id: str,
        capacity: int,
        room_type: str = "normal"
    ):
        self.id = id
        self.capacity = capacity
        self.room_type = room_type

    def __repr__(self):
        return f"Room({self.id})"