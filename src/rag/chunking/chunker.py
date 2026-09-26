from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from rag.structure import Document


DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 64

TOKEN_ENCODING = "cl100k_base"


def chunk_document(
    document: Document,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict]:
    """
    Structure-aware, token-aware document chunking.

    Stage 1:
        Split the document according to Markdown heading hierarchy.

    Stage 2:
        Recursively split sections that exceed the target token size.

    The recursive splitter uses tiktoken for length measurement,
    so chunk_size and chunk_overlap are measured in tokens rather
    than characters.
    """

    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be greater than 0"
        )

    if chunk_overlap < 0:
        raise ValueError(
            "chunk_overlap cannot be negative"
        )

    if chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap must be smaller than chunk_size"
        )

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
            ("####", "h4"),
        ],
        strip_headers=False,
    )

    sections = markdown_splitter.split_text(
        document.text
    )

    recursive_splitter = (
        RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            encoding_name=TOKEN_ENCODING,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n\n",
                "\n",
                ". ",
                " ",
                "",
            ],
        )
    )

    chunks: list[dict] = []

    for section in sections:
        split_sections = recursive_splitter.split_documents(
            [section]
        )

        for split in split_sections:
            text = split.page_content.strip()

            if not text:
                continue

            chunk_id = (
                f"{document.title}-{len(chunks):04d}"
            )

            metadata = {
                "source": document.source,
                "title": document.title,
                "file_type": document.file_type,
                **split.metadata,
                "chunk_id": chunk_id,
            }

            chunks.append(
                {
                    "text": text,
                    "metadata": metadata,
                }
            )

    return chunks