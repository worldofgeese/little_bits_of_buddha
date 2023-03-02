from little_bits_of_buddha_worldofgeese.tokenize_suttas import chunked_tokens
from typing import Iterator, Tuple


def test_tokenize():
    # Define input parameters for the function
    chunk_length = 10

    # Call the function with the input parameters
    token_chunks = chunked_tokens(chunk_length)

    # Validate that the function returns an iterator
    assert isinstance(
        token_chunks, Iterator
    ), f"Function does not return an iterator: {type(token_chunks)}"

    # Validate that the iterator yields tuples of integers
    for chunk in token_chunks:
        assert isinstance(chunk, Tuple), f"Chunk is not a tuple: {type(chunk)}"
        assert all(
            isinstance(token, int) for token in chunk
        ), "Chunk contains non-integer tokens"
