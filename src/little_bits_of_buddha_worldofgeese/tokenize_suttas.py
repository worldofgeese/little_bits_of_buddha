from itertools import islice
from typing import Iterable, Iterator, Tuple

import tiktoken

from little_bits_of_buddha_worldofgeese.data import get_data

EMBEDDING_MODEL = "text-embedding-ada-002"
EMBEDDING_CTX_LENGTH = 8191
SUTTAS = get_data()


def batched(iterable: Iterable, n: int) -> Iterator[Tuple[int, ...]]:
    """Batch data into tuples of length n. The last batch may be shorter."""
    # Raise a ValueError if n is less than 1
    if n < 1:
        raise ValueError("n must be at least one")
    # Create an iterator over the input iterable
    it = iter(iterable)
    # Keep iterating and yielding tuples of length n until the iterable is exhausted
    while batch := tuple(islice(it, n)):
        yield batch


def chunked_tokens(chunk_length: int) -> Iterator[Tuple[int, ...]]:
    """_summary_

    Args:
        chunk_length (int): _description_

    Yields:
        Iterator[Tuple[int, ...]]: _description_
    """
    # Obtain the encoding object associated with the specified encoding scheme
    encoding = tiktoken.encoding_for_model(EMBEDDING_MODEL)
    # Convert the input text into a sequence of tokens using the encoding object
    tokens = encoding.encode(SUTTAS)
    # Break down the sequence of tokens into chunks of the specified length
    chunks_iterator = batched(tokens, chunk_length)
    # Yield each of the chunks in the iterator as they are generated
    yield from chunks_iterator


if __name__ == "__main__":
    # Print the first 10 tokens in the first chunk
    print(next(chunked_tokens(EMBEDDING_CTX_LENGTH))[:10])
