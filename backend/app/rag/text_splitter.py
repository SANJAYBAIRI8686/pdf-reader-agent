# pyright: ignore [reportMissingImports]
from langchain_text_splitters import RecursiveCharacterTextSplitter

def get_text_splitter(
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> RecursiveCharacterTextSplitter:
    """
    Returns a RecursiveCharacterTextSplitter instance configured with the specified
    chunk size and overlap parameters.
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False
    )
