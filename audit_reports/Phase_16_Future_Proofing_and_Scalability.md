# Phase 16: Future Proofing & Scalability - Analysis Report

## 16. Overview
This phase evaluates the system's readiness for growth.

## 16.1. Horizontal Scaling
*   **Pipeline**: Currently monolithic (runs in one process/container).
    *   **Bottleneck**: Network I/O (ephemeral ports) and CPU (parsing/crypto).
    *   **State**: `ProxyHistoryTracker` uses SQLite (`history.db`).
    *   **Issue**: SQLite locks prevent multi-instance write access.
    *   **Solution**: Migration to PostgreSQL or Redis-based state tracking is needed for horizontal scaling.

## 16.2. Sharding
*   The system *supports* generating sharded outputs (`shard_0.json`), which helps *client* scalability (millions of users fetching configs).
*   It does NOT support sharding the *ingestion* (e.g., worker A does sources 1-100, worker B does 101-200) efficiently without a central queue (Redis).

## Recommendations
1.  **Database**: Abstract `ProxyHistoryTracker` to support a DB backend (SQLAlchemy).
2.  **Queue**: Use Celery or Redis Stream for the `work_queue` if scaling beyond one node.
