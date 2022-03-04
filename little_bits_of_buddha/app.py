from flask import Flask

from data import _random_sutta

app = Flask(__name__)


@app.route("/")
def random_sutta():
    return _random_sutta()
