import uvicorn
from fastapi import FastAPI

from little_bits_of_buddha_worldofgeese.data import random_sutta as _random_sutta

app = FastAPI()


@app.get("/")
def random_sutta():
    return _random_sutta()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
