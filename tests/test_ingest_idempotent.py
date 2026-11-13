from pathlib import Path
import pytest
from ingest.indexer import LocalIndex


def test_ingest_idempotent_local() -> None:
    """Ensure LocalIndex chunks count is idempotent."""
    index = LocalIndex(Path("data/index"))
    chunks1 = index.load_chunks()
    assert len(chunks1) in (5029, 5256)
    # Re-reading or checking content produces exact same count
    chunks2 = index.load_chunks()
    assert len(chunks1) == len(chunks2)
