from fastapi import FastAPI
import uvicorn
from little_bits_of_buddha_worldofgeese.data import get_data

app = FastAPI()


@app.get("/")
async def main():
    """
    This function retrieves the merged data and makes it available to the rest of the program.
    """
    # Call the retrieve_data function to get the merged data
    message = get_data()
    return message


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
