from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    summary: str = Field(
        description="A concise factual summary of the chunk."
    )

    keywords: list[str] = Field(
        description="Important keywords and concepts from the chunk."
    )

    hypothetical_question: str = Field(
        description="A question that this chunk could answer."
    )


class ChunkMetadataResult(ChunkMetadata):
    chunk_id: str = Field(
        description="The ID of the chunk this metadata belongs to."
    )


class MetadataBatchResponse(BaseModel):
    results: list[ChunkMetadataResult]