from dataclasses import dataclass


@dataclass
class DenseEmbedding:
    values: list[float]


@dataclass
class SparseEmbedding:
    indices: list[int]
    values: list[float]


@dataclass
class HybridEmbedding:
    dense: DenseEmbedding
    sparse: SparseEmbedding