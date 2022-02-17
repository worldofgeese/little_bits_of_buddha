#!/usr/bin/env python3

import json
import random
from importlib import resources

with resources.open_text("little_bits_of_buddha", "data.json") as json_file:
    data = json.load(json_file)


def random_sutta():
    attributed_quotes = []
    for collection in data["collection"].values():
        for quote in collection.values():
            attributed_quotes.append(quote)
    return random.choice(attributed_quotes)
