#!/usr/bin/env python3

import json
import random


def _random_sutta():
    with open("../data.json") as json_file:
        data = json.load(json_file)

        attributed_quotes = []
        for collection in data["collection"].values():
            for quote in collection.values():
                attributed_quotes.append(quote)
        return random.choice(attributed_quotes)