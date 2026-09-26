from dataclasses import dataclass, field


@dataclass
class Document:
    title: str
    source: str
    file_type: str
    text: str
    metadata: dict = field(default_factory=dict)