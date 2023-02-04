from flask import Flask

from little_bits_of_buddha_worldofgeese.data import random_sutta as _random_sutta

app = Flask(__name__)


@app.route("/")
def random_sutta():
    return _random_sutta()


def main():
    app.run(host="0.0.0.0")


if __name__ == "__main__":
    main()
