__version__ = "0.1.0"

import json
import random


def random_sutta():
    with open("../data.json") as json_file:
        data = json.load(json_file)
        random.choice(data["collection"]["MN"].values())


print(random_sutta())
