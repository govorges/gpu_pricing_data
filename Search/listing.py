class Listing:
    """
    A listing object. This is just a helper to make a Data dictionary more accessible.
    """
    def __init__(self, data: dict) -> None:
        '''Listings only take a `data` dictionary, this is because vendors' output data is set dynamically as kwargs.'''
        self.Data = data
    def __str__(self) -> str:
        return self.Data.get("title", self.__class__)