from evals.judge import judge, summarize
from observability.metrics import Metrics


def test_metrics_and_judge() -> None:
    metrics = Metrics()
    metrics.observe("retrieve", 10)
    metrics.observe("retrieve", 20)
    assert metrics.summary()["retrieve"]["p50_ms"] == 15
    result = judge("KYC rule", "KYC rule", "KYC rule source")
    assert result["failure"] == "none"
    assert summarize([result])["questions"] == 1
