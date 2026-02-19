# Open Skills Protocol (OSP)

**Intelligent AI Skill Routing Infrastructure**

4-stage routing pipeline with built-in safety, cryptographic integrity, graceful degradation, and sub-millisecond latency. Zero config needed.

## Quick Start

```python
from asp import skill, serve

@skill("greet", description="Say hello")
def greet(name: str) -> str:
    return f"Hello, {name}!"

serve()  # → localhost:8080
```

## Architecture

```
Request → [Intake] → [Route] → [Safety] → [Deliver] → Response
              │          │          │           │
          Validate    BM25+     ML-based    Execute &
          Envelope   Semantic   Classifier   Sign Response
```

### Core Components

| Component | Description |
|-----------|-------------|
| `osp_core/` | Protocol models, JCS canonicalization, crypto (ES256/EdDSA/RS256+) |
| `osp_server/` | Reference server with 4-stage routing pipeline |
| `osp_std/` | Standard library (sandboxed fs, http, system) |
| `osp_cli/` | CLI tools (`osp new skill`, `osp new agent`) |
| `asp/` | Python SDK — `@skill` decorator, dev server, client |

### Key Features

- **BM25 + Semantic Routing** — TF-IDF with compiled regex and LRU cache
- **ML Safety Classifier** — TF-IDF + KL-divergence anomaly detection
- **Graceful Degradation** — D0→D3 FSM with hysteresis and auto-monitoring
- **Cryptographic Plane Isolation** — 9 algorithms (ES/RS/EdDSA/HMAC)
- **Delivery Contracts** — Idempotency, TTL enforcement, append-only proof log
- **Skill Registry** — Trust chain verification, transparency log

## Installation

```bash
pip install osp-sdk

# With all features:
pip install osp-sdk[full]
```

## Server Deployment

```bash
# Set required environment variables
export OSP_ADMIN_KEY="your-secure-admin-key"
export OSP_CORS_ORIGINS="https://yourdomain.com"

# Run with Docker
docker compose up -d
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `OSP_ADMIN_KEY` | — (required) | Admin API key for `/admin/*` endpoints |
| `OSP_CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `OSP_SIGNATURE_ENFORCE` | `false` | Enable strict signature verification |
| `OSP_SANDBOX_ROOT` | CWD | Sandbox root for skill filesystem access |

## Running Tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
