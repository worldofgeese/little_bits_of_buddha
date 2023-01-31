import json
import random
from importlib import resources

with resources.open_text("little_bits_of_buddha_worldofgeese", "data.json") as json_file:
    data = json.load(json_file)


def random_sutta(suttas=data):
    # With no arguments called, `suttas` will default to data.
    attributed_quotes = []
    for collection in suttas["collection"].values():
        for quote in collection.values():
            attributed_quotes.append(quote)
    return random.choice(attributed_quotes)
