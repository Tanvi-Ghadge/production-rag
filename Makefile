ingest:
	python -m ingest.run

eval-retrieval:
	python -m evals.run_retrieval

pgvector-up:
	docker compose -f deploy/docker-compose.pgvector.yml up -d

pgvector-down:
	docker compose -f deploy/docker-compose.pgvector.yml down

pgvector-ingest:
	python -m ingest.pgvector_run

redteam:
	python -m redteam.run

eval-answers:
	python -m evals.run_answers

report-latency:
	python -m observability.report_latency

failure-modes:
	python -m evals.failure_modes

ci-gate:
	python -m evals.ci_gate
