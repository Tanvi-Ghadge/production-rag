from retrieval.rerank import CrossEncoderReranker


def test_cached_cross_encoder_reranks_candidates() -> None:
    reranker = CrossEncoderReranker(model_name="BAAI/bge-reranker-base")
    candidates = [
        ({"chunk_id": "wrong", "text": "The weather forecast is sunny."}, 0.9),
        ({"chunk_id": "right", "text": "Payment aggregators must follow regulatory requirements."}, 0.1),
    ]
    result = reranker.rerank("What are payment aggregator requirements?", candidates, top_k=1)
    assert result
    assert result[0][0]["chunk_id"] == "right"
