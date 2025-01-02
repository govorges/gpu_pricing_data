

class Vendor:
    def __init__(self, identifier: str, metadata: dict, url: dict, selectors: dict, strip_phrases: list, preload: str = None):
        self.identifier = identifier
        self.metadata = metadata
        self.url = url
        self.selectors = selectors
        self.strip_phrases = strip_phrases
        self.preload = preload

        assert "listings" in self.selectors.keys(), \
            f"Required selector, `listings` not defined in {identifier} configuration."
        
        listings_selector_value = self.selectors['listings']
        assert isinstance(listings_selector_value, str), \
            f"`listings` selector definition in {identifier} configuration should be {str.__class__}, not {listings_selector_value.__class__}"
        
    def __str__(self):
        return f"<Vendor" + " ".join([f"{x}={self.__dict__[x]}" for x in self.__dict__]) + ">"