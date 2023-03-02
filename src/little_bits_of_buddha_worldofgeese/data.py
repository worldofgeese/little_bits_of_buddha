import json
import gzip
from pathlib import Path


def get_data():
    # Define the directory where the JSON files are stored

    directory = Path(__file__).parent / "suttas_data"
    file_path = Path(__file__).parent / "merged_data.json.gz"

    # Create a list of values from all the JSON files in the directory using a list comprehension
    # A list comprehension is a way to create a new list from an existing iterable (such as a file path) by applying some expression (such as json.loads()) to each element
    # The syntax is [expression for element in iterable]
    # For each file path in directory.glob("*.json"), which returns an iterable of all the file paths that match "*.json" pattern,
    # We read the text content of the file using the file.read_text() method, which returns a string
    # We parse the string as JSON data using json.loads() function, which returns a dictionary
    # We get all the values from the dictionary using .values() method, which returns a list
    # We join all the elements in the list into a string using "".join() function
    # The condition is value != "", which means that only non-empty values are added to the list
    if directory.exists():
        merged_data = [
            "".join(value)
            for value in [
                json.loads(file.read_text()).values()
                for file in directory.glob("*.json")
            ]
            if value != ""
        ]

        # Write the merged_data to a compressed JSON file
        with gzip.open(file_path, "wb") as file:
            file.write(json.dumps(merged_data).encode())
    elif file_path.exists():
        # Read the merged_data from the compressed JSON file
        with gzip.open(file_path, "rb") as file:
            merged_data = json.loads(file.read().decode())
    else:
        raise FileNotFoundError(
            f"Neither the directory '{directory}' nor the file '{file_path}' were found."
        )

    # Join all the values in merged_data into one string using .join() method of strings
    # The syntax is separator.join(iterable)
    # In this case, we use "" as separator and merged_data as iterable
    merged_data_string = "".join(merged_data)
    return merged_data_string


if __name__ == "__main__":
    get_data()
