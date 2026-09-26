from dataclasses import dataclass


@dataclass
class PineconeMatch:
    id: str
    score: float
    metadata: dict