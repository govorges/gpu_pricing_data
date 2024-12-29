from os import path
import json

QUERY_DIR = path.dirname(path.realpath(__file__))

class Query:
    def __init__(self, Content: str, Include: list[str, dict], IncludeSettings: dict, Exclude: list[str, dict], ExcludeSettings: dict, ValueRange: list[float, float] | None) -> None:
        self.Content = Content
        
        # Include & Exclude are lists of phrases/strings required to be present or missing from a listing's title/desc/etc.
        # You can optionally pass a dictionary as an object in the list ( ex. include = ["phrase1", "phrase2", {...}] )
        #       to add some additional functionality to this filter.
        #               options include:
        # {
        #   "case_sensitive": bool, (default False)
        #   "operator": "and"/"or"/"xor", (default "or")
        # }
        self.Include = Include
        self.Include_Settings = {
            "require_content": IncludeSettings.get("require_content", True),
            "case_sensitive": IncludeSettings.get("case_sensitive", False),
            "operator": IncludeSettings.get("operator", "and")
        }

        if self.Include_Settings.get("require_content", True): self.Include.append(self.Content)
        if not self.Include_Settings.get("case_sensitive", False): self.Include = [x.lower() for x in self.Include]

        self.Exclude = Exclude
        self.Exclude_Settings = {
            "case_sensitive": ExcludeSettings.get("case_sensitive", False),
            "operator": ExcludeSettings.get("operator", "or")
        }

        if not self.Exclude_Settings.get("case_sensitive", False): self.Exclude = [x.lower() for x in self.Exclude]

        # ValueRange sets a strict value range (or None) for the query's results. 
        #   If a listing's price isnt between MinimumValue and MaximumValue, it's dropped.
        self.MinimumValue = ValueRange[0]
        self.MaximumValue = ValueRange[1]

    def IsValidListing(self, CheckStrings: list[str], Price: int):
        '''
        Given a list of strings (belonging to one (1) listing) and a price value, this function checks the
        validity of the arguments when run against the query's filters (Query.Include/Query.Exclude/Query.ValueRange/etc)
        '''
        max_value = Price + 1 if self.MaximumValue is None else self.MaximumValue
        if not (Price > self.MinimumValue):
            return f"Price: {Price} less than MinimumValue of {self.MinimumValue}"
        if Price > max_value:
            return f"Price: {Price} greater than MaximumValue of {self.MaximumValue}"
        total_check_string = " ".join([string for string in CheckStrings])
        return self.is_string_valid(total_check_string)
    
    def is_string_valid(self, check_string: str) -> bool | list[str]:
        include_check_string = (check_string.lower(), check_string)[self.Include_Settings['case_sensitive']]
        phrases_found = []
        for phrase in self.Include:
            if phrase in include_check_string:
                phrases_found.append(phrase)
            # Checking for the query's content in the check string regardless of space placement if the phrase happens to be the query's content.
            elif phrase.lower() == self.Content.lower() and phrase.replace(" ", "") in include_check_string.replace(" ", ""):
                phrases_found.append(phrase) 

        match self.Include_Settings.get("operator", "and").lower():
            case "and":
                include_result = len(phrases_found) == len(self.Include)
            case "or":
                include_result = len(phrases_found) > 0
            case "xor":
                include_result = len(phrases_found) == 1
            case _:
                raise ValueError(f"Query: `{self.Content}`'s Include operator was explicitly set but not to a valid value. Received: {self.Include_Settings['operator'].lower()}")
        if include_result is False:
            if len(self.Include) != 0:
                return "phrases_not_found : " + str([x for x in self.Include if x not in include_check_string])
        

        exclude_check_string = (check_string.lower(), check_string)[self.Exclude_Settings['case_sensitive']]
        phrases_found = []
        for phrase in self.Exclude:
            if phrase in exclude_check_string:
                phrases_found.append(phrase)

        match self.Exclude_Settings.get("operator", "or").lower():
            case "and": # Problems with self.Exclude length being longer than actual set exclude list of the query item.
                exclude_result = len(phrases_found) == len(self.Exclude)
            case "or":
                exclude_result = len(phrases_found) > 0
            case "xor":
                exclude_result = len(phrases_found) == 1
            case _:
                raise ValueError(f"Query: `{self.Content}`'s Exclude operator was explicitly set but not to a valid value. Received: {self.Exclude_Settings['operator'].lower()}")
        if exclude_result is True:
            return "phrases_found : " + str(phrases_found)
        
        return True
    
    def __str__(self) -> str:
        return self.Content



class QueryList:
    def __init__(self, list_name: str):
        list_name = f"{list_name}.json" if list_name.rsplit('.', 1)[1] != "json" else list_name
        query_file_path = path.join(QUERY_DIR, "lists", list_name)
        with open(query_file_path, "r") as query_list_file:
            data = json.loads(query_list_file.read())

            settings = data.get("settings", None)
            queries = data.get("queries", None)

            assert isinstance(queries, list), \
                f"{query_file_path} was not a properly configured JSON file. (Must be a list, received: {data.__class__.__name__})"

        self.Queries: list[Query] = []
        for item in queries:
            # Adding our query list's global "filtered_phrases" to each query's Exclude list.
            exclude = item.get("Exclude", [])
            for phrase in settings.get("filtered_phrases"):
                exclude.append(phrase)

            query = Query(
                Content = item['Content'],

                Include = item.get("Include", []),
                IncludeSettings = item.get("IncludeSettings", {}),

                ExcludeSettings = item.get("ExcludeSettings", {}),
                Exclude = exclude,

                ValueRange = [item.get("MinimumValue", 0), item.get("MaximumValue", None)]
            )
            self.Queries.append(query)
        
        self.Pos = 0
    
    @property
    def Query(self) -> Query:
        return self.Queries[self.Pos]

    @property
    def Next(self):
        self.Pos += 1
        if self.Pos >= len(self.Queries):
            return None
        return self.Query

    @property
    def Previous(self):
        self.Pos -= 1
        if self.Pos <= 0:
            self.Pos = 0
        return self.Query
    
    def Reset(self):
        self.Pos = 0

