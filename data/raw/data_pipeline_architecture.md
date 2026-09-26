# Nimbus Data Pipeline — Architecture Reference

**Owner:** Platform Engineering
**Last reviewed:** 2026-02-20
**Status:** Living document — update on any schema or infra change

This document describes the internal architecture of the Nimbus ingestion
and analytics pipeline. It is intended for engineers onboarding onto the
Platform team and for anyone debugging production ingestion issues.

## 1. Overview

The pipeline moves client data from source connectors through
transformation and into the analytics warehouse that powers customer
dashboards. At a high level:

```
Source Connectors -> Kafka (raw topic) -> Stream Processor -> 
Warehouse Proxy -> ClickHouse (analytics store) -> Dashboard API
```

Roughly 40TB of raw event data flows through this pipeline per day across
all client accounts as of Q1 2026, up from 24TB in Q1 2025.

## 2. Source connectors

Connectors are per-integration adapters that normalize inbound client data
into our internal event schema before it reaches Kafka.

| Connector | Source type | Ingestion mode | Owner team |
|---|---|---|---|
| `salesforce-connector` | CRM | Polling, 15 min | Integrations |
| `stripe-connector` | Payments | Webhook | Integrations |
| `s3-batch-connector` | File drop (client S3 buckets) | Scheduled, hourly | Platform |
| `warehouse-sync-connector` | Client's own DW (Snowflake/BigQuery) | Polling, 1 hr | Integrations |

Each connector emits events onto a per-client Kafka topic prefixed
`raw.<client_id>.<source>`. Connectors do **not** write directly to
ClickHouse under any circumstances — this is a hard architectural
boundary, since bypassing Kafka has caused data consistency issues twice
in the past (see incident log, INC-3820 and INC-4471).

## 3. Stream processor

The stream processor is a Flink job that:

1. Deduplicates events using an idempotency key (`event_id` +
   `client_id`), with a 24-hour dedup window held in RocksDB state.
2. Applies per-client transformation rules (defined in
   `transform-rules-service`, not in this repo).
3. Writes transformed events to `processed.<client_id>` Kafka topics.

### 3.1 Known limitation: transformation rule updates require a restart

Transformation rules are currently loaded at job startup and are **not**
hot-reloaded. Updating a client's transformation rule requires a
coordinated Flink job restart, which causes up to 90 seconds of processing
pause for *all* clients sharing that job (jobs are currently shared across
clients within the same region, not isolated per-client). This is tracked
as tech debt under `PLATFORM-2291` and is a known pain point the team
would like prioritized in the next planning cycle, though it has not yet
been scheduled.

## 4. Warehouse proxy

The warehouse proxy sits between the stream processor's output and
ClickHouse, and is responsible for:

- Connection pooling to ClickHouse (see incident INC-4471 for context on
  why pool size configuration matters here)
- Batching writes to reduce insert overhead (target batch size: 5,000
  rows or 2 seconds, whichever comes first)
- Retrying failed writes with exponential backoff (max 5 retries)

Configuration for the proxy lives in `infra/helm/warehouse-proxy/values.yaml`.
As of the INC-4471 postmortem, `max_pool_size` is now explicitly set per
environment rather than relying on the client library default:

```yaml
proxy:
  max_pool_size: 200
  batch_size: 5000
  batch_timeout_ms: 2000
  retry:
    max_attempts: 5
    backoff_ms: 500
```

## 5. ClickHouse analytics store

Data lands in ClickHouse using a per-client sharding strategy for accounts
above a certain event volume threshold (>50M events/month), and a shared
multi-tenant table for smaller accounts. The threshold is currently a
manually maintained list in `sharding-config.yaml` rather than an
automated decision — this is intentional for now, since automating it
without more operational experience felt premature, but is worth
revisiting once we have more shards in production.

### 5.1 Table structure (shared multi-tenant table)

```sql
CREATE TABLE events_shared (
    client_id UInt32,
    event_id UUID,
    event_type LowCardinality(String),
    event_timestamp DateTime64(3),
    payload String,
    ingested_at DateTime64(3) DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_timestamp)
ORDER BY (client_id, event_timestamp);
```

## 6. Dashboard API

The Dashboard API reads from ClickHouse and serves the customer-facing
analytics dashboard. It is a fairly thin read layer today (query
templating + caching), though there is an open discussion about whether it
should absorb more business logic currently living in the frontend — no
decision has been made on this as of the last architecture review.

## 7. Open questions / not yet decided

The following are genuinely unresolved as of this writing, and this
document should be updated once decisions are made:

- Should transformation rules move to hot-reload, and if so, what's the
  isolation story for shared Flink jobs? (Owner: TBD)
- Should the ClickHouse sharding threshold be automated? (Owner: TBD,
  loosely owned by Platform but not formally assigned)
- Long-term home for business logic currently duplicated between the
  Dashboard API and frontend (Owner: TBD, needs a design review)

## 8. Related documents

- Incident postmortems: see `INC-3820`, `INC-4471` in the incident tracker
- On-call runbook: `platform-oncall-runbook.md` (separate document)
- Client onboarding checklist: owned by Integrations team, not Platform
