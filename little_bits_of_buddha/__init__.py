__version__ = "0.1.0"

import json
import random


def random_sutta():
    with open("../data.json") as json_file:
        data = json.load(json_file)

        attributed_quotes = []
        for collection in data["collection"].values():
            for quote in collection.values():
                attributed_quotes.append(quote)
        return random.choice(attributed_quotes)


