class Listing:
    def __init__(self, data: dict) -> None:
        self.Data = data
    def __str__(self) -> str:
        return self.Data.get("title", self.__class__)