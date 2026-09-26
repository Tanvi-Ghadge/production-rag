import os

from dotenv import load_dotenv
from pinecone import Pinecone, SparseValues

from rag.embeddings.models import HybridEmbedding


load_dotenv()


INDEX_NAME = os.getenv(
    "PINECONE_INDEX_NAME",
    "production-rag-hybrid",
)

PINECONE_CLOUD = os.getenv(
    "PINECONE_CLOUD",
    "aws",
)

PINECONE_REGION = os.getenv(
    "PINECONE_REGION",
    "us-east-1",
)

NAMESPACE = os.getenv(
    "PINECONE_NAMESPACE",
    "production-rag",
)

DENSE_DIMENSION = 768

DENSE_FIELD = "dense-embedding"
SPARSE_FIELD = "sparse-embedding"


def get_pinecone_client() -> Pinecone:
    api_key = os.getenv("PINECONE_API_KEY")

    if not api_key:
        raise ValueError(
            "PINECONE_API_KEY is not set."
        )

    return Pinecone(api_key=api_key)


def create_index() -> None:
    pc = get_pinecone_client()

    existing_indexes = pc.list_indexes()

    existing_names = {
        index["name"]
        for index in existing_indexes
    }

    if INDEX_NAME in existing_names:
        print(
            f"Index already exists: {INDEX_NAME}"
        )
        return

    pc.indexes.create(
        name=INDEX_NAME,
        schema={
            "fields": {
                DENSE_FIELD: {
                    "type": "dense_vector",
                    "dimension": DENSE_DIMENSION,
                    "metric": "cosine",
                },
                SPARSE_FIELD: {
                    "type": "sparse_vector",
                },
            }
        },
        deployment={
            "deployment_type": "managed",
            "cloud": PINECONE_CLOUD,
            "region": PINECONE_REGION,
        },
    )

    print(
        f"Created Pinecone index: {INDEX_NAME}"
    )


def get_index():
    pc = get_pinecone_client()

    return pc.Index(INDEX_NAME)


def upsert_chunks(
    chunks: list[dict],
    batch_size: int = 50,
) -> None:
    if not chunks:
        return

    index = get_index()

    for start in range(
        0,
        len(chunks),
        batch_size,
    ):
        batch = chunks[
            start:start + batch_size
        ]

        documents = []

        for chunk in batch:
            embedding: HybridEmbedding = (
                chunk["embedding"]
            )

            document = {
                "_id": chunk["metadata"]["chunk_id"],

                # Dense vector field
                DENSE_FIELD: embedding.dense.values,

                # Sparse vector field
                SPARSE_FIELD: {
                    "indices": embedding.sparse.indices,
                    "values": embedding.sparse.values,
                },

                # Metadata
                **chunk["metadata"],

                # Original chunk text
                "text": chunk["text"],
            }

            documents.append(document)

        index.documents.upsert(
            namespace=NAMESPACE,
            documents=documents,
        )

        print(
            f"Upserted {len(batch)} chunks."
        )