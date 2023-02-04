import json
import pathlib
import random

DATA_PATH = pathlib.Path(__file__).parent / "data.json"
with open(DATA_PATH) as json_file:
    data = json.load(json_file)

def random_sutta(suttas=data):
    # With no arguments called, `suttas` will default to data.
    attributed_quotes = []
    for collection in suttas["collection"].values():
        for quote in collection.values():
            attributed_quotes.append(quote)
    return random.choice(attributed_quotes)
