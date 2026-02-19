# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] — 2026-02-19

### Added
- 4-stage routing pipeline (Intake → Route → Safety → Deliver)
- BM25 + semantic scoring with LRU cache and compiled regex
- ML safety classifier with TF-IDF + KL-divergence anomaly detection
- Graceful degradation FSM (D0–D3) with hysteresis and auto-monitoring
- Cryptographic plane isolation — 9 algorithms (ES256/384/512, RS256/384/512, EdDSA, HS256/512)
- JCS canonicalization for deterministic JSON signing
- Delivery contract enforcement with TTL, idempotency, and proof log
- Skill registry with trust chain verification and transparency log
- Standard library: sandboxed filesystem, HTTP client (SSRF-protected), system info
- Python SDK with `@skill` decorator, dev server, and client
- CLI: `osp new skill`, `osp new agent` scaffolding
- OSP Reference Server (FastAPI + Uvicorn)
- Docker deployment support
- Prometheus metrics endpoint
- 291 passing conformance tests
